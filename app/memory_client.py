"""Cliente de memória do FocoCerto (docs/CONTRATOS.md, seções 5 e 11).

Duas implementações do Protocol ``ClienteMemoria``:

- ``ClienteHMEM(base_url)``: fala com o serviço H-MEM em TypeScript
  (``services/hmem/``, porta 7070), que roda o engine de referência da Meterless.
- ``MemoriaLocal()``: tudo em processo, sem rede, para o sample mode e os testes.
  É uma tradução fiel para Python das partes do engine que o serviço usa
  (``services/hmem/src/engine/``: embedder determinístico, enriquecimento,
  detecção de supersedes, detecção e auto-resolução de conflito, ranking
  híbrido) e da camada ``services/hmem/src/servico.ts`` (escopo por região,
  supersedes -> supersededBy, política de notas do coordenador, cadeia de
  substituídas no recall). Mesmos limiares e fórmulas; os ids têm o mesmo
  formato (``<regiao>:mem-<n>``).

Semântica (resumo; detalhes em services/hmem/README.md):
- ``gravar(..., supersedes=id)``: a memória nova substitui ``id``; a antiga recebe
  ``substituida_por`` e passa a levar a penalidade −0.20 do ranking. Nada é apagado.
- Sem ``supersedes``, o engine ainda pode detectar a substituição (similaridade
  > 0.85 + linguagem de correção) ou um conflito (pares opostos, como
  "alagada"/"liberada"). Conflito acima do gate de 0.70 é resolvido pelo engine;
  abaixo dele vai para a fila, exceto entre duas notas do coordenador com a
  política ``coordenador_mais_recente`` (padrão), em que a nota nova vence.
- ``recall`` devolve ``(ativas, substituidas)``: as ativas em ordem de relevância e
  as substituídas encontradas no ranking ou na cadeia das ativas.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Protocol, runtime_checkable

import httpx

from app.core.models import Memoria

Politica = Literal["fila", "coordenador_mais_recente"]


@runtime_checkable
class ClienteMemoria(Protocol):
    def gravar(self, regiao: str, texto: str, tipo: str, fonte: str,
               confianca: float = 1.0, supersedes: str | None = None) -> Memoria: ...

    def recall(self, regiao: str, consulta: str, k: int = 5) -> tuple[list[Memoria], list[Memoria]]: ...

    def listar(self, regiao: str) -> list[Memoria]: ...


class ErroMemoria(ValueError):
    """Requisição inválida (status 400) ou memória inexistente (status 404)."""

    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status


# ---------------------------------------------------------------------------
# Cliente HTTP
# ---------------------------------------------------------------------------

class ClienteHMEM:
    """Cliente do serviço H-MEM (services/hmem). ``base_url`` ex.: http://127.0.0.1:7070"""

    def __init__(self, base_url: str = "http://127.0.0.1:7070", timeout: float = 10.0,
                 client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self._http = client or httpx.Client(base_url=self.base_url, timeout=timeout)
        self.ultimos_conflitos: list[dict] = []  # conflitos detectados no último gravar()
        self.ultimo_trace: dict = {}             # trace do último recall() (scores, estratégia)
        self._substituida_por: dict[str, str | None] = {}  # visto no último listar()/recall()

    def _checar(self, r: httpx.Response) -> httpx.Response:
        if r.status_code in (400, 404, 413):
            try:
                msg = r.json().get("erro", r.text)
            except ValueError:
                msg = r.text
            raise ErroMemoria(r.status_code, msg)
        r.raise_for_status()
        return r

    def saude(self) -> bool:
        try:
            return bool(self._http.get("/health").json().get("ok"))
        except (httpx.HTTPError, ValueError):
            return False

    def gravar(self, regiao: str, texto: str, tipo: str, fonte: str,
               confianca: float = 1.0, supersedes: str | None = None) -> Memoria:
        corpo = {"regiao": regiao, "texto": texto, "tipo": tipo, "fonte": fonte,
                 "confianca": confianca, "supersedes": supersedes}
        dados = self._checar(self._http.post("/memorias", json=corpo)).json()
        self.ultimos_conflitos = dados.get("conflitos", [])
        return Memoria.model_validate(dados)

    def recall(self, regiao: str, consulta: str, k: int = 5) -> tuple[list[Memoria], list[Memoria]]:
        dados = self._checar(self._http.post("/recall", json={"regiao": regiao, "consulta": consulta, "k": k})).json()
        self.ultimo_trace = dados.get("trace", {})
        return ([Memoria.model_validate(m) for m in dados["memorias"]],
                [Memoria.model_validate(m) for m in dados["substituidas"]])

    def listar(self, regiao: str) -> list[Memoria]:
        dados = self._checar(self._http.get("/memorias", params={"regiao": regiao})).json()
        self._substituida_por.update({m["id"]: m.get("substituida_por") for m in dados if "id" in m})
        return [Memoria.model_validate(m) for m in dados]

    def substituida_por(self, memoria_id: str) -> str | None:
        """Id da memória que substituiu ``memoria_id`` (None se ativa), pelo campo ``substituida_por`` que o
        serviço devolve no último ``listar()`` (o tipo ``Memoria`` do contrato não tem esse campo).
        Mesma assinatura de ``MemoriaLocal.substituida_por``."""
        return self._substituida_por.get(memoria_id)

    def ledger(self, regiao: str) -> list[dict]:
        """Ledger de auditoria do engine (extra ao contrato)."""
        return self._checar(self._http.get("/ledger", params={"regiao": regiao})).json()

    def close(self) -> None:
        self._http.close()


# ---------------------------------------------------------------------------
# Port do engine (services/hmem/src/engine) para Python
# ---------------------------------------------------------------------------

_DIM = 64
_DAY_MS = 24 * 60 * 60 * 1000
_RECENCY_DAYS = 14
_THRESHOLD = 0.35
_ENTITY_CAP = 10
_RELATED_CAP = 5
_GATE = 0.7
_LAYER_WEIGHT = {"long_term": 1.0, "working": 0.8, "short_term": 0.6}
_ORIGEM = {"nota": "manual", "derivada": "plan_completion"}
_REGIAO_RE = re.compile(r"^[a-z0-9_-]{1,64}$", re.I)

_TECH_TERMS = ["react", "python", "typescript", "javascript", "rust", "sqlite", "postgres", "indexeddb",
               "node", "docker", "graphql", "redis", "webrtc", "tauri", "electron", "llm", "embedding"]
_DOMAIN_KEYWORDS = {
    "tech": ["code", "bug", "api", "database", "deploy", "framework", "library", "server", *_TECH_TERMS],
    "work": ["meeting", "deadline", "client", "project", "sprint", "review", "report"],
    "personal": ["family", "hobby", "prefer", "like", "dislike", "morning", "evening"],
}
_A = re.I | re.A  # \b ASCII, como no JavaScript
_CORRECTION = re.compile(r"\b(actually|instead|no longer|not anymore|changed to|correction)\b", _A)
_CORRECTION_PT = re.compile(r"\b(na verdade|em vez de|ao inves de|nao esta mais|nao mais|deixou de|corrigindo"
                            r"|correcao|retificando|retificacao)\b", _A)
_OPPOSING = [
    (r"\balways\b", r"\bnever\b"),
    (r"\benable[ds]?\b", r"\bdisable[ds]?\b"),
    (r"\bprefer[s]?\b", r"\bavoid[s]?|dislike[s]?\b"),
    (r"\bon\b", r"\boff\b"),
    (r"\byes\b", r"\bno\b"),
    (r"\bsempre\b", r"\bnunca\b"),
    (r"\b(habilitad|ativad)[oa]s?\b", r"\b(desabilitad|desativad)[oa]s?\b"),
    (r"\b(liberad[oa]s?|abert[oa]s?|desbloquead[oa]s?|desimpedid[oa]s?|transitave(l|is))\b",
     r"\b(alagad[oa]s?|bloquead[oa]s?|interditad[oa]s?|fechad[oa]s?|obstruid[oa]s?|intransitave(l|is))\b"),
    (r"\bdisponive(l|is)\b", r"\bindisponive(l|is)\b"),
]
_OPPOSING_RE = [(re.compile(p, _A), re.compile(q, _A)) for p, q in _OPPOSING]
_NUM_RE = re.compile(r"\d+(\.\d+)?", re.A)
_ENT_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b", re.A)


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _fold(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not ("̀" <= c <= "ͯ"))


def _tokenize(texto: str) -> list[str]:
    t = re.sub(r"[^a-z0-9\s]", " ", _fold(texto).lower())
    return [x for x in re.split(r"\s+", t) if len(x) > 1]


def _fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for c in s:
        h ^= ord(c)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def _embed(texto: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in _tokenize(texto):
        h = _fnv1a(tok)
        sign = 1 if (h >> 8) % 2 == 0 else -1
        vec[h % _DIM] += sign * (1 + ((h >> 16) % 8) / 8)
    s = 0.0
    for v in vec:  # soma na mesma ordem do reduce() do JS (sum() do Python compensa erro)
        s += v * v
    norm = math.sqrt(s)
    return vec if norm == 0 else [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    d = 0.0
    for x, y in zip(a, b):
        d += x * y
    return d


def _jaccard(a, b) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return inter / (len(sa) + len(sb) - inter)


def _numeros(texto: str) -> list[str]:
    return [m.group(0) for m in _NUM_RE.finditer(texto)]


def _classify_domain(content: str, tags: list[str], tipo: str) -> str:
    for t in tags:
        if t.startswith("project:"):
            return t[len("project:"):]
        if t.startswith("tech:"):
            return "tech"
    tokens = set(_tokenize(content))
    best, best_score = "general", 0
    for domain, kws in _DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in tokens)
        if domain == "personal" and tipo in ("personal", "preference"):
            score += 1
        if score > best_score:
            best, best_score = domain, score
    return best if best_score > 0 else "general"


def _extract_entities(content: str) -> list[str]:
    ents: dict[str, None] = {}
    for t in _tokenize(content):
        if t in _TECH_TERMS:
            ents[t] = None
    for m in _ENT_RE.finditer(_fold(content)):
        norm = m.group(1).lower()
        if norm not in ("the", "this", "that", "with"):
            ents[norm] = None
    return list(ents)[:_ENTITY_CAP]


class _Registro:
    __slots__ = ("id", "content", "type", "layer", "timestamp", "last_accessed", "access_count", "tags",
                 "embedding", "confidence", "source", "origin", "domain", "entities", "related_to",
                 "supersedes", "superseded_by")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class _Conflito:
    __slots__ = ("id", "a", "b", "reason", "confidence", "resolved", "resolution")

    def __init__(self, id, a, b, reason, confidence):
        self.id, self.a, self.b, self.reason, self.confidence = id, a, b, reason, confidence
        self.resolved, self.resolution = False, None


class _EngineRegiao:
    """Uma instância por região, como no serviço (HMEM por região)."""

    def __init__(self, clock: Callable[[], int]):
        self.clock = clock
        self.records: dict[str, _Registro] = {}
        self.seq = 0
        self.conflict_seq = 0
        self.conflicts: list[_Conflito] = []
        self.ledger: list[dict] = []

    def log(self, mid: str, action: str, actor: str, **details) -> None:
        self.ledger.append({"memoryId": mid, "action": action, "actor": actor, "timestamp": self.clock(), **details})

    # MemoryStoreService.add + discoverRelationships
    def add(self, content: str, tags: list[str], confidence: float, source: str, origin: str,
            supersedes: str | None, actor: str) -> _Registro:
        if not source or not source.strip():
            raise ErroMemoria(400, "fonte é obrigatória (o H-MEM rejeita registros sem source)")
        now = self.clock()
        self.seq += 1
        rec = _Registro(id=f"mem-{self.seq}", content=content, type="factual", layer="working", timestamp=now,
                        last_accessed=now, access_count=0, tags=list(tags), embedding=_embed(content),
                        confidence=_clamp01(confidence), source=source, origin=origin,
                        domain=_classify_domain(content, tags, "factual"), entities=_extract_entities(content),
                        related_to=[], supersedes=supersedes, superseded_by=None)
        for other in self.records.values():
            if len(rec.related_to) >= _RELATED_CAP:
                break
            shared = [e for e in other.entities if e in rec.entities]
            sim = _cosine(rec.embedding, other.embedding)
            if not rec.supersedes and sim > 0.85 and (_CORRECTION.search(rec.content)
                                                      or _CORRECTION_PT.search(_fold(rec.content))):
                rec.supersedes = other.id
                continue
            if shared and other.domain == rec.domain:
                rec.related_to.append(other.id)
                if len(other.related_to) < _RELATED_CAP and rec.id not in other.related_to:
                    other.related_to.append(rec.id)
        self.records[rec.id] = rec
        self.log(rec.id, "create", actor)
        return rec

    # ConflictDetectionService.check
    def check(self, a: _Registro, b: _Registro) -> _Conflito | None:
        if a.supersedes == b.id or b.supersedes == a.id or a.superseded_by == b.id or b.superseded_by == a.id:
            return None
        sim = _cosine(a.embedding, b.embedding)
        reason, confidence = "", 0.0
        ca, cb = _fold(a.content), _fold(b.content)
        for p, q in _OPPOSING_RE:
            if (p.search(ca) and q.search(cb)) or (q.search(ca) and p.search(cb)):
                if sim > 0.5:
                    reason = "opposing phrase pair on similar content"
                    confidence = 0.5 + 0.3 * sim
        if not reason and sim > 0.8:
            na, nb = _numeros(a.content), _numeros(b.content)
            if na and nb and ",".join(na) != ",".join(nb):
                reason = "high-similarity conflicting numeric values"
                confidence = 0.55 + 0.25 * sim
        if not reason:
            return None
        if any(e in b.entities for e in a.entities):
            confidence += 0.1
        if a.domain == b.domain:
            confidence += 0.05
        if b.id in a.related_to:
            confidence -= 0.1
        self.conflict_seq += 1
        return _Conflito(f"conflict-{self.conflict_seq}", a.id, b.id, reason, _clamp01(confidence))

    def scan_for(self, mid: str, actor: str) -> list[_Conflito]:
        alvo = self.records[mid]
        found = []
        for other in list(self.records.values()):
            if other.id == mid:
                continue
            c = self.check(other, alvo)
            if c:
                found.append(c)
                self.conflicts.append(c)
                self.log(c.a, "conflict_detected", actor, details={"with": c.b, "reason": c.reason})
        return found

    def auto_resolve(self, c: _Conflito, actor: str) -> str:
        a, b = self.records[c.a], self.records[c.b]
        now = max(1, self.clock())

        def score_of(m: _Registro) -> float:
            return (0.3 * (m.last_accessed / now) + 0.2 * min(1, m.access_count / 10) + 0.25 * m.confidence
                    + 0.1 * min(1, len(m.content) / 200) + 0.15 * (1 if m.origin == "user_correction" else 0.5))

        sa, sb = score_of(a), score_of(b)
        margin = abs(sa - sb) / max(sa, sb)
        decision = _clamp01(c.confidence * 0.6 + margin * 0.8)
        if decision < _GATE:
            return "queued"
        winner, loser = (a, b) if sa >= sb else (b, a)
        return self._resolver(c, winner, loser, actor, {"decisionConfidence": round(decision, 3)})

    def resolve_by_supervisor(self, c: _Conflito, winner_id: str, actor: str) -> str:
        winner = self.records[winner_id]
        loser = self.records[c.b if winner_id == c.a else c.a]
        return self._resolver(c, winner, loser, actor, {"mode": "supervisor", "policy": "coordenador_mais_recente"})

    def _resolver(self, c, winner, loser, actor, details) -> str:
        loser.superseded_by = winner.id
        c.resolved = True
        c.resolution = "keep_a" if winner.id == c.a else "keep_b"
        self.log(loser.id, "conflict_resolved", actor, details={"conflictId": c.id, "winner": winner.id, **details})
        return "resolved"

    # MemoryRetrievalService.score/query (sem filtro de chatId)
    def query(self, consulta: str, top_n: int, threshold: float = _THRESHOLD) -> list[tuple[_Registro, float]]:
        q_emb = _embed(consulta)
        q_tok = _tokenize(consulta)[:8]
        q_ent = _extract_entities(consulta)
        q_dom = _classify_domain(consulta, [], "general")
        now = self.clock()
        scored = []
        for m in self.records.values():
            semantic = _clamp01(_cosine(q_emb, m.embedding))
            keyword = _jaccard(q_tok, _tokenize(m.content))
            tag = _jaccard(q_tok, [t.lower() for t in m.tags])
            domain = 1 if m.domain == q_dom else 0
            entity = _jaccard(q_ent, m.entities)
            layer = _LAYER_WEIGHT[m.layer]
            recency = math.exp(-((now - m.last_accessed) / _DAY_MS) / _RECENCY_DAYS)
            superseded = 1 if m.superseded_by else 0
            raw = (0.35 * semantic + 0.2 * keyword + 0.1 * tag + 0.1 * domain
                   + 0.15 * entity + 0.05 * layer + 0.05 * recency - 0.2 * superseded)
            s = _clamp01(raw) * m.confidence
            if s >= threshold:
                scored.append((m, s))
        scored.sort(key=lambda t: (-t[1], t[0].id))
        top = scored[:top_n]
        for m, _ in top:
            m.last_accessed = now
            m.access_count += 1
        return top


def _seq(rid: str) -> int:
    try:
        return int(rid.rsplit("-", 1)[-1])
    except ValueError:
        return 0


_CAMPOS_PERSISTIDOS = [c for c in _Registro.__slots__ if c != "embedding"]  # embedding é recalculado


class MemoriaLocal:
    """H-MEM em processo, com a mesma semântica do serviço.

    ``caminho=None``: só em memória. Com um caminho, carrega o JSON na
    inicialização (se existir) e grava o estado inteiro (todas as regiões,
    registros, ledger e conflitos) a cada ``gravar`` e ``recall`` (o recall
    atualiza lastAccessed/accessCount, como no engine). A escrita é atômica
    (arquivo temporário + rename).
    """

    def __init__(self, caminho: str | Path | None = None, clock: Callable[[], int] | None = None,
                 politica: Politica = "coordenador_mais_recente"):
        self.caminho = Path(caminho) if caminho is not None else None
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.politica = politica
        self._engines: dict[str, _EngineRegiao] = {}
        self.ultimos_conflitos: list[dict] = []
        self.ultimo_trace: dict = {}
        if self.caminho is not None and self.caminho.exists():
            self._carregar()

    def _carregar(self) -> None:
        dados = json.loads(self.caminho.read_text(encoding="utf-8"))
        for regiao, e in dados.get("regioes", {}).items():
            eng = self._engine(regiao)
            eng.seq, eng.conflict_seq, eng.ledger = e["seq"], e["conflict_seq"], e["ledger"]
            for r in e["records"]:
                eng.records[r["id"]] = _Registro(**r, embedding=_embed(r["content"]))
            for c in e["conflicts"]:
                cf = _Conflito(c["id"], c["a"], c["b"], c["reason"], c["confidence"])
                cf.resolved, cf.resolution = c["resolved"], c["resolution"]
                eng.conflicts.append(cf)

    def _salvar(self) -> None:
        if self.caminho is None:
            return
        dados = {"versao": 1, "regioes": {
            regiao: {
                "seq": eng.seq, "conflict_seq": eng.conflict_seq, "ledger": eng.ledger,
                "records": [{c: getattr(r, c) for c in _CAMPOS_PERSISTIDOS} for r in eng.records.values()],
                "conflicts": [{c: getattr(cf, c) for c in _Conflito.__slots__} for cf in eng.conflicts],
            } for regiao, eng in self._engines.items()}}
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.caminho.with_name(self.caminho.name + ".tmp")
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.caminho)

    def _engine(self, regiao: str) -> _EngineRegiao:
        if not isinstance(regiao, str) or not _REGIAO_RE.match(regiao):
            raise ErroMemoria(400, "regiao inválida (use letras, números, _ ou -)")
        if regiao not in self._engines:
            self._engines[regiao] = _EngineRegiao(self.clock)
        return self._engines[regiao]

    def _memoria(self, regiao: str, r: _Registro) -> Memoria:
        tipo = next((t[5:] for t in r.tags if t.startswith("tipo:")), "nota")
        return Memoria(id=f"{regiao}:{r.id}", regiao=regiao, texto=r.content, tipo=tipo, fonte=r.source,
                       confianca=r.confidence, supersedes=f"{regiao}:{r.supersedes}" if r.supersedes else None,
                       criada_em=datetime.fromtimestamp(r.timestamp / 1000, tz=timezone.utc))

    def substituida_por(self, memoria_id: str) -> str | None:
        """Id da memória que substituiu ``memoria_id`` (None se ativa)."""
        regiao, _, rid = memoria_id.partition(":")
        r = self._engine(regiao).records.get(rid)
        return f"{regiao}:{r.superseded_by}" if r and r.superseded_by else None

    def gravar(self, regiao: str, texto: str, tipo: str, fonte: str,
               confianca: float = 1.0, supersedes: str | None = None) -> Memoria:
        eng = self._engine(regiao)
        if not isinstance(texto, str) or not texto.strip():
            raise ErroMemoria(400, "texto é obrigatório")
        if tipo not in ("derivada", "nota"):
            raise ErroMemoria(400, "tipo deve ser 'derivada' ou 'nota'")
        if not isinstance(fonte, str) or not fonte.strip():
            raise ErroMemoria(400, "fonte é obrigatória (o H-MEM rejeita registros sem source)")
        if not isinstance(confianca, (int, float)) or not 0 <= confianca <= 1:
            raise ErroMemoria(400, "confianca deve ser um número entre 0 e 1")
        alvo = None
        if supersedes is not None:
            if not supersedes.startswith(f"{regiao}:"):
                raise ErroMemoria(400, f"supersedes {supersedes} não pertence à região {regiao}")
            alvo = supersedes[len(regiao) + 1:]
            if alvo not in eng.records:
                raise ErroMemoria(404, f"memória {supersedes} não existe")
        actor = f"fococerto-hmem:{regiao}"
        rec = eng.add(texto, [f"tipo:{tipo}", f"regiao:{regiao}"], float(confianca), fonte, _ORIGEM[tipo], alvo, actor)
        if rec.supersedes and rec.supersedes != rec.id and rec.supersedes in eng.records:
            eng.records[rec.supersedes].superseded_by = rec.id
            eng.log(rec.supersedes, "update", actor)

        conflitos = []
        for c in eng.scan_for(rec.id, actor):
            resultado = eng.auto_resolve(c, actor)
            outro = eng.records[c.b if c.a == rec.id else c.a]
            if (resultado == "queued" and self.politica == "coordenador_mais_recente" and tipo == "nota"
                    and "tipo:nota" in outro.tags and not outro.superseded_by):
                resultado = eng.resolve_by_supervisor(c, rec.id, f"supervisor:{fonte}")
                if not rec.supersedes:
                    rec.supersedes = outro.id
                    eng.log(rec.id, "update", actor)
            vencedor = (c.a if c.resolution == "keep_a" else c.b) if resultado == "resolved" else None
            conflitos.append({"com": f"{regiao}:{outro.id}", "motivo": c.reason,
                              "confianca": round(c.confidence, 4), "resultado": resultado,
                              "vencedor": f"{regiao}:{vencedor}" if vencedor else None})
        self.ultimos_conflitos = conflitos
        self._salvar()
        return self._memoria(regiao, rec)

    def recall(self, regiao: str, consulta: str, k: int = 5) -> tuple[list[Memoria], list[Memoria]]:
        eng = self._engine(regiao)
        if not isinstance(consulta, str) or not consulta.strip():
            raise ErroMemoria(400, "consulta é obrigatória")
        if not isinstance(k, int) or not 1 <= k <= 100:
            raise ErroMemoria(400, "k deve ser inteiro entre 1 e 100")
        top = eng.query(consulta, k)
        self.ultimo_trace = {"scores": {f"{regiao}:{m.id}": round(s, 4) for m, s in top}}
        ativas, subst, vistos = [], [], set()
        for m, _ in top:
            vistos.add(m.id)
            (subst if m.superseded_by else ativas).append(m)
        todas = sorted(eng.records.values(), key=lambda r: _seq(r.id))
        fronteira = [m.id for m, _ in top]
        while fronteira:
            prox = []
            for r in todas:
                if r.superseded_by and r.superseded_by in fronteira and r.id not in vistos:
                    vistos.add(r.id)
                    subst.append(r)
                    prox.append(r.id)
            fronteira = prox
        self._salvar()
        return [self._memoria(regiao, m) for m in ativas], [self._memoria(regiao, m) for m in subst]

    def listar(self, regiao: str) -> list[Memoria]:
        eng = self._engine(regiao)
        return [self._memoria(regiao, r) for r in sorted(eng.records.values(), key=lambda r: _seq(r.id))]

    def ledger(self, regiao: str) -> list[dict]:
        return list(self._engine(regiao).ledger)
