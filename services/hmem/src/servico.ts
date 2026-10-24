// Camada de serviço do FocoCerto sobre o engine H-MEM vendorizado (src/engine/).
// Não altera a semântica do engine: só adiciona escopo por região, o formato
// `Memoria` do contrato (docs/CONTRATOS.md, seções 2 e 5) e a ligação
// supersedes -> supersededBy descrita no README.
//
// Escopo por região: uma instância HMEM por região, cada uma com o próprio
// diretório de persistência (state.json + ledger.jsonl do engine). Memórias de
// regiões diferentes nunca se misturam, nem no ranking nem na detecção de conflito.
//
// Nenhuma chamada a modelo: o HMEM é construído sem `minerFn`, então o engine
// fica no caminho determinístico (sem gerador injetado).

import fs from "node:fs";
import path from "node:path";
import { HMEM } from "./engine/index.ts";
import type { MemoryRecord, LedgerEntry, ConflictRecord, ProvenanceOrigin } from "./engine/index.ts";

export type TipoMemoria = "derivada" | "nota";

export interface Memoria {
  id: string;
  regiao: string;
  texto: string;
  tipo: TipoMemoria;
  fonte: string;
  confianca: number;
  supersedes: string | null;
  criada_em: string;
  // Campos extras (não estão no contrato; o pydantic ignora):
  substituida_por: string | null;
}

export interface EntradaMemoria {
  regiao: string;
  texto: string;
  tipo: TipoMemoria;
  fonte: string;
  confianca?: number;
  supersedes?: string | null;
}

export interface ConflitoResumo {
  com: string;
  motivo: string;
  confianca: number;
  resultado: "resolved" | "queued";
  vencedor: string | null;
}

// "fila": só o engine de referência (conflito abaixo do gate fica na fila).
// "coordenador_mais_recente": além disso, uma nota nova do coordenador resolve,
// como supervisor, o conflito que o engine enfileirou contra uma nota anterior.
export type Politica = "fila" | "coordenador_mais_recente";

export function politicaDoAmbiente(): Politica {
  const v = (process.env.HMEM_POLITICA_NOTAS ?? "coordenador_mais_recente").trim();
  if (v !== "fila" && v !== "coordenador_mais_recente") {
    throw new Error(`HMEM_POLITICA_NOTAS inválida: ${v} (use fila ou coordenador_mais_recente)`);
  }
  return v;
}

export class ErroRequisicao extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const REGIAO_RE = /^[a-z0-9_-]{1,64}$/i;
const ORIGEM: Record<TipoMemoria, ProvenanceOrigin> = { nota: "manual", derivada: "plan_completion" };

export function validarRegiao(regiao: unknown): string {
  if (typeof regiao !== "string" || !REGIAO_RE.test(regiao)) {
    throw new ErroRequisicao(400, "regiao inválida (use letras, números, _ ou -)");
  }
  return regiao;
}

export function idPublico(regiao: string, idEngine: string): string {
  return `${regiao}:${idEngine}`;
}

function idEngine(regiao: string, idPub: string): string {
  const prefixo = `${regiao}:`;
  if (!idPub.startsWith(prefixo)) {
    throw new ErroRequisicao(400, `supersedes ${idPub} não pertence à região ${regiao}`);
  }
  return idPub.slice(prefixo.length);
}

function seqDe(id: string): number {
  const n = Number(id.split("-").pop());
  return Number.isFinite(n) ? n : 0;
}

export class ServicoHMEM {
  private engines = new Map<string, HMEM>();

  constructor(
    private dataDir: string | undefined,
    private clock: () => number = Date.now,
    private politica: Politica = "coordenador_mais_recente"
  ) {}

  engine(regiao: string): HMEM {
    validarRegiao(regiao);
    let e = this.engines.get(regiao);
    if (!e) {
      e = new HMEM({
        clock: this.clock,
        actor: `fococerto-hmem:${regiao}`,
        persistDir: this.dataDir ? path.join(this.dataDir, regiao) : undefined,
        // minerFn omitido de propósito: nenhum modelo é chamado.
      });
      this.engines.set(regiao, e);
    }
    return e;
  }

  paraMemoria(regiao: string, r: MemoryRecord): Memoria {
    const tipoTag = r.tags.find((t) => t.startsWith("tipo:"));
    return {
      id: idPublico(regiao, r.id),
      regiao,
      texto: r.content,
      tipo: (tipoTag?.slice(5) as TipoMemoria) ?? "nota",
      fonte: r.source,
      confianca: r.confidence,
      supersedes: r.supersedes ? idPublico(regiao, r.supersedes) : null,
      criada_em: new Date(r.timestamp).toISOString(),
      substituida_por: r.supersededBy ? idPublico(regiao, r.supersededBy) : null,
    };
  }

  gravar(entrada: EntradaMemoria): { memoria: Memoria; conflitos: ConflitoResumo[] } {
    const regiao = validarRegiao(entrada.regiao);
    if (typeof entrada.texto !== "string" || entrada.texto.trim() === "") {
      throw new ErroRequisicao(400, "texto é obrigatório");
    }
    if (entrada.tipo !== "derivada" && entrada.tipo !== "nota") {
      throw new ErroRequisicao(400, "tipo deve ser 'derivada' ou 'nota'");
    }
    if (typeof entrada.fonte !== "string" || entrada.fonte.trim() === "") {
      // O engine também rejeita (registro sem source), mas aqui damos 400 claro.
      throw new ErroRequisicao(400, "fonte é obrigatória (o H-MEM rejeita registros sem source)");
    }
    const confianca = entrada.confianca ?? 1.0;
    if (typeof confianca !== "number" || !Number.isFinite(confianca) || confianca < 0 || confianca > 1) {
      throw new ErroRequisicao(400, "confianca deve ser um número entre 0 e 1");
    }
    const hmem = this.engine(regiao);
    let alvo: string | undefined;
    if (entrada.supersedes != null) {
      if (typeof entrada.supersedes !== "string") throw new ErroRequisicao(400, "supersedes deve ser string");
      alvo = idEngine(regiao, entrada.supersedes);
      if (!hmem.store.get(alvo)) throw new ErroRequisicao(404, `memória ${entrada.supersedes} não existe`);
    }

    const rec = hmem.add({
      content: entrada.texto,
      type: "factual",
      layer: "working",
      tags: [`tipo:${entrada.tipo}`, `regiao:${regiao}`],
      confidence: confianca,
      source: entrada.fonte,
      provenance: { origin: ORIGEM[entrada.tipo], learnedAt: this.clock(), label: entrada.fonte },
      supersedes: alvo,
    });

    // supersedes (explícito ou detectado pelo engine) -> o registro substituído
    // recebe supersededBy, que é o que aciona a penalidade −0.20 do ranking.
    // É um update do engine, então fica no ledger com estado anterior e novo.
    if (rec.supersedes && rec.supersedes !== rec.id && hmem.store.get(rec.supersedes)) {
      hmem.store.update(rec.supersedes, { supersededBy: rec.id });
    }

    // Detecção e auto-resolução de conflito, com o gate de 0.70 do engine.
    // Se o engine põe o conflito na fila e a política "coordenador_mais_recente"
    // está ativa, a nota nova do coordenador decide como supervisor (veja README).
    const conflitos: ConflitoResumo[] = [];
    for (const c of hmem.conflicts.scanFor(rec.id)) {
      let resultado = hmem.conflicts.autoResolve(c);
      const outroRec = hmem.store.get(c.memoryA === rec.id ? c.memoryB : c.memoryA)!;
      if (
        resultado === "queued" &&
        this.politica === "coordenador_mais_recente" &&
        entrada.tipo === "nota" &&
        outroRec.tags.includes("tipo:nota") &&
        !outroRec.supersededBy
      ) {
        resultado = hmem.conflicts.resolveBySupervisor(c, rec.id, `supervisor:${entrada.fonte}`, {
          policy: "coordenador_mais_recente",
        });
        if (!hmem.store.get(rec.id)!.supersedes) hmem.store.update(rec.id, { supersedes: outroRec.id });
      }
      const outro = c.memoryA === rec.id ? c.memoryB : c.memoryA;
      const vencedor =
        resultado === "resolved" ? (c.resolution === "keep_a" ? c.memoryA : c.memoryB) : null;
      conflitos.push({
        com: idPublico(regiao, outro),
        motivo: c.reason,
        confianca: Number(c.confidence.toFixed(4)),
        resultado,
        vencedor: vencedor ? idPublico(regiao, vencedor) : null,
      });
    }
    return { memoria: this.paraMemoria(regiao, hmem.store.get(rec.id)!), conflitos };
  }

  recall(regiaoIn: string, consulta: string, k = 5) {
    const regiao = validarRegiao(regiaoIn);
    if (typeof consulta !== "string" || consulta.trim() === "") throw new ErroRequisicao(400, "consulta é obrigatória");
    if (!Number.isInteger(k) || k < 1 || k > 100) throw new ErroRequisicao(400, "k deve ser inteiro entre 1 e 100");
    const hmem = this.engine(regiao);
    const res = hmem.query(consulta, { topN: k });
    hmem.store.persist(); // query atualiza lastAccessed/accessCount (touch)

    const ativas: MemoryRecord[] = [];
    const substituidas: MemoryRecord[] = [];
    const vistos = new Set<string>();
    for (const { memory } of res.memories) {
      vistos.add(memory.id);
      (memory.supersededBy ? substituidas : ativas).push(memory);
    }
    // Cadeia: o que cada memória recuperada substituiu (supersededBy aponta para ela).
    const todas = hmem.store.all().sort((a, b) => seqDe(a.id) - seqDe(b.id));
    let fronteira = res.memories.map((m) => m.memory.id);
    while (fronteira.length) {
      const prox: string[] = [];
      for (const r of todas) {
        if (r.supersededBy && fronteira.includes(r.supersededBy) && !vistos.has(r.id)) {
          vistos.add(r.id);
          substituidas.push(r);
          prox.push(r.id);
        }
      }
      fronteira = prox;
    }
    return {
      memorias: ativas.map((m) => this.paraMemoria(regiao, m)),
      substituidas: substituidas.map((m) => this.paraMemoria(regiao, m)),
      trace: {
        retrievalReason: res.trace.retrievalReason,
        strategy: res.trace.strategy,
        scores: Object.fromEntries(Object.entries(res.trace.scores).map(([id, s]) => [idPublico(regiao, id), s])),
      },
    };
  }

  listar(regiaoIn: string): Memoria[] {
    const regiao = validarRegiao(regiaoIn);
    return this.engine(regiao)
      .store.all()
      .sort((a, b) => seqDe(a.id) - seqDe(b.id))
      .map((r) => this.paraMemoria(regiao, r));
  }

  ledger(regiaoIn: string): LedgerEntry[] {
    const regiao = validarRegiao(regiaoIn);
    return this.engine(regiao).ledger.all().map((e) => ({ ...e, memoryId: idPublico(regiao, e.memoryId) }));
  }

  conflitos(regiaoIn: string): ConflictRecord[] {
    const regiao = validarRegiao(regiaoIn);
    return this.engine(regiao)
      .conflicts.queue()
      .map((c) => ({ ...c, memoryA: idPublico(regiao, c.memoryA), memoryB: idPublico(regiao, c.memoryB) }));
  }
}

export function dirDados(): string | undefined {
  const v = process.env.HMEM_DATA_DIR;
  if (v === ":memory:") return undefined;
  const dir = v && v.trim() ? v : path.join(path.dirname(new URL(import.meta.url).pathname), "..", "data");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}
