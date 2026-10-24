// Servidor HTTP do H-MEM do FocoCerto (docs/CONTRATOS.md, seção 5).
//
//   GET  /health                         -> {ok: true}
//   POST /memorias  {regiao, texto, tipo, fonte, confianca?, supersedes?} -> Memoria (+ conflitos)
//   POST /recall    {regiao, consulta, k?} -> {memorias, substituidas, trace}
//   GET  /memorias?regiao=..             -> [Memoria]
//   GET  /ledger?regiao=..               -> [LedgerEntry]   (auditoria; extra ao contrato)
//   GET  /conflitos?regiao=..            -> conflitos na fila (extra ao contrato)
//
// Variáveis: HMEM_PORT (padrão 7070), HMEM_HOST (padrão 127.0.0.1),
// HMEM_DATA_DIR (padrão services/hmem/data; ":memory:" desliga a persistência),
// HMEM_POLITICA_NOTAS (coordenador_mais_recente | fila; padrão coordenador_mais_recente).

import http from "node:http";
import { ErroRequisicao, ServicoHMEM, dirDados, politicaDoAmbiente } from "./servico.ts";

const LIMITE_CORPO = 1_000_000;

function lerJson(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let tamanho = 0;
    const partes: Buffer[] = [];
    req.on("data", (c: Buffer) => {
      tamanho += c.length;
      if (tamanho > LIMITE_CORPO) {
        reject(new ErroRequisicao(413, "corpo grande demais"));
        req.destroy();
        return;
      }
      partes.push(c);
    });
    req.on("end", () => {
      const txt = Buffer.concat(partes).toString("utf-8");
      if (!txt.trim()) return resolve({});
      try {
        resolve(JSON.parse(txt));
      } catch {
        reject(new ErroRequisicao(400, "JSON inválido"));
      }
    });
    req.on("error", reject);
  });
}

function responder(res: http.ServerResponse, status: number, corpo: unknown): void {
  const txt = JSON.stringify(corpo);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "content-length": Buffer.byteLength(txt) });
  res.end(txt);
}

export function criarServidor(servico: ServicoHMEM): http.Server {
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? "/", "http://localhost");
      const rota = `${req.method} ${url.pathname}`;
      switch (rota) {
        case "GET /health":
          return responder(res, 200, { ok: true });
        case "POST /memorias": {
          const b = await lerJson(req);
          const { memoria, conflitos } = servico.gravar(b);
          return responder(res, 200, { ...memoria, conflitos });
        }
        case "POST /recall": {
          const b = await lerJson(req);
          return responder(res, 200, servico.recall(b.regiao, b.consulta, b.k ?? 5));
        }
        case "GET /memorias":
          return responder(res, 200, servico.listar(url.searchParams.get("regiao") ?? ""));
        case "GET /ledger":
          return responder(res, 200, servico.ledger(url.searchParams.get("regiao") ?? ""));
        case "GET /conflitos":
          return responder(res, 200, servico.conflitos(url.searchParams.get("regiao") ?? ""));
        default:
          return responder(res, 404, { erro: `rota não encontrada: ${rota}` });
      }
    } catch (err) {
      if (err instanceof ErroRequisicao) return responder(res, err.status, { erro: err.message });
      console.error(err);
      return responder(res, 500, { erro: (err as Error).message });
    }
  });
}

const executadoDireto = process.argv[1] && new URL(import.meta.url).pathname === process.argv[1];
if (executadoDireto) {
  const porta = Number(process.env.HMEM_PORT ?? 7070);
  const host = process.env.HMEM_HOST ?? "127.0.0.1";
  const dados = dirDados();
  const politica = politicaDoAmbiente();
  const servidor = criarServidor(new ServicoHMEM(dados, Date.now, politica));
  servidor.listen(porta, host, () => {
    console.log(`fococerto-hmem ouvindo em http://${host}:${porta} (dados: ${dados ?? "somente memória"}; política de notas: ${politica})`);
  });
  const parar = () => servidor.close(() => process.exit(0));
  process.on("SIGTERM", parar);
  process.on("SIGINT", parar);
}
