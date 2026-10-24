"""Testes da memória (H-MEM): MemoriaLocal sempre; ClienteHMEM quando o serviço sobe.

O fixture ``servico_hmem`` sobe services/hmem (npx tsx) numa porta livre, com dados
num diretório temporário, e derruba no fim. Se o Node ou o node_modules de
services/hmem não existirem, os testes HTTP são pulados (com o motivo).
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from app.core.models import Memoria
from app.memory_client import ClienteHMEM, ClienteMemoria, ErroMemoria, MemoriaLocal

RAIZ = Path(__file__).resolve().parents[1]
HMEM_DIR = RAIZ / "services" / "hmem"
TSX = HMEM_DIR / "node_modules" / ".bin" / "tsx"

NOTA_1 = "Estrada para Mateiros alagada"
NOTA_2 = "Estrada para Mateiros liberada"
DERIVADA = "Célula cel_-102_-470 despriorizada no período 1 cresceu 3x no período 2"


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Servico:
    def __init__(self, dados: Path, politica: str = "coordenador_mais_recente"):
        self.dados, self.politica = dados, politica
        self.proc: subprocess.Popen | None = None
        self.url = ""

    def subir(self) -> None:
        porta = _porta_livre()
        self.url = f"http://127.0.0.1:{porta}"
        env = {"PATH": os.environ.get("PATH", ""), "HMEM_PORT": str(porta), "HMEM_HOST": "127.0.0.1",
               "HMEM_DATA_DIR": str(self.dados), "HMEM_POLITICA_NOTAS": self.politica}
        self.proc = subprocess.Popen([str(TSX), "src/server.ts"], cwd=HMEM_DIR, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        limite = time.time() + 20
        while time.time() < limite:
            if self.proc.poll() is not None:
                saida = self.proc.stdout.read().decode() if self.proc.stdout else ""
                raise RuntimeError(f"serviço H-MEM saiu com {self.proc.returncode}: {saida}")
            try:
                if httpx.get(f"{self.url}/health", timeout=0.5).json().get("ok"):
                    return
            except httpx.HTTPError:
                time.sleep(0.1)
        self.derrubar()
        raise RuntimeError("serviço H-MEM não respondeu /health em 20 s")

    def derrubar(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


@pytest.fixture
def servico_hmem(tmp_path):
    if shutil.which("node") is None or not TSX.exists():
        pytest.skip("Node ou services/hmem/node_modules ausente (rode `npm ci` em services/hmem)")
    s = _Servico(tmp_path / "hmem-dados")
    s.subir()
    yield s
    s.derrubar()


@pytest.fixture(params=["local", "http"])
def memoria(request) -> ClienteMemoria:
    if request.param == "local":
        return MemoriaLocal()
    s = request.getfixturevalue("servico_hmem")
    return ClienteHMEM(s.url)


def _ids(ms: list[Memoria]) -> list[str]:
    return [m.id for m in ms]


def test_implementa_protocol(memoria):
    assert isinstance(memoria, ClienteMemoria)


def test_tres_periodos(memoria):
    r = "jalapao"
    # Período 1: o coordenador avisa que a estrada está alagada.
    n1 = memoria.gravar(r, NOTA_1, tipo="nota", fonte="coordenador:teste")
    assert isinstance(n1, Memoria) and n1.id == f"{r}:mem-1" and n1.supersedes is None

    # Fim do período 1 -> 2: memória derivada dos dados (a célula despriorizada cresceu).
    d = memoria.gravar(r, DERIVADA, tipo="derivada", fonte="monitor:periodo-2", confianca=0.9)
    assert d.tipo == "derivada" and d.confianca == pytest.approx(0.9)

    # Período 2: nota contraditória. O engine detecta o conflito (alagada x liberada);
    # a nota nova do coordenador vence e passa a substituir a antiga.
    n2 = memoria.gravar(r, NOTA_2, tipo="nota", fonte="coordenador:teste")
    assert n2.supersedes == n1.id
    assert memoria.ultimos_conflitos and memoria.ultimos_conflitos[0]["com"] == n1.id
    assert memoria.ultimos_conflitos[0]["resultado"] == "resolved"
    assert memoria.ultimos_conflitos[0]["vencedor"] == n2.id

    # Período 3: o recall mostra a nota ativa e a substituída.
    ativas, substituidas = memoria.recall(r, "estrada para Mateiros", k=5)
    assert n2.id in _ids(ativas)
    assert n1.id not in _ids(ativas)
    assert _ids(substituidas) == [n1.id]
    assert substituidas[0].texto == NOTA_1

    # ... e a memória derivada é lembrada.
    ativas, _ = memoria.recall(r, "célula cel_-102_-470 despriorizada cresceu", k=3)
    assert ativas and ativas[0].id == d.id

    # Nada foi apagado: a auditoria lista as três.
    assert _ids(memoria.listar(r)) == [n1.id, d.id, n2.id]


def test_supersedes_explicito_e_validacao(memoria):
    r = "jalapao"
    a = memoria.gravar(r, "Base de Ponte Alta sem combustível", tipo="nota", fonte="coordenador:teste")
    b = memoria.gravar(r, "Combustível reposto na base de Ponte Alta", tipo="nota", fonte="coordenador:teste",
                       supersedes=a.id)
    assert b.supersedes == a.id
    ativas, substituidas = memoria.recall(r, "combustível base Ponte Alta", k=5)
    assert _ids(ativas) == [b.id] and _ids(substituidas) == [a.id]

    with pytest.raises(ErroMemoria) as e:
        memoria.gravar(r, "x qualquer", tipo="nota", fonte="c", supersedes=f"{r}:mem-999")
    assert e.value.status == 404
    with pytest.raises(ErroMemoria) as e:
        memoria.gravar("outra", "x qualquer", tipo="nota", fonte="c", supersedes=a.id)
    assert e.value.status == 400
    with pytest.raises(ErroMemoria):
        memoria.gravar(r, "sem fonte", tipo="nota", fonte="")


def test_escopo_por_regiao(memoria):
    memoria.gravar("jalapao", NOTA_1, tipo="nota", fonte="coordenador:teste")
    m = memoria.gravar("chapada", NOTA_2, tipo="nota", fonte="coordenador:teste")
    # A nota de outra região não entra em conflito nem é substituída.
    assert m.supersedes is None and memoria.ultimos_conflitos == []
    assert memoria.recall("chapada", "estrada para Mateiros")[1] == []
    assert [x.texto for x in memoria.listar("jalapao")] == [NOTA_1]
    assert [x.texto for x in memoria.listar("chapada")] == [NOTA_2]


def test_politica_fila_segue_so_o_engine():
    """Sem a política do coordenador, o conflito fica na fila (gate de 0.70 do engine)."""
    mem = MemoriaLocal(politica="fila")
    n1 = mem.gravar("jalapao", NOTA_1, tipo="nota", fonte="coordenador:teste")
    n2 = mem.gravar("jalapao", NOTA_2, tipo="nota", fonte="coordenador:teste")
    assert n2.supersedes is None
    assert mem.ultimos_conflitos[0]["resultado"] == "queued"
    ativas, substituidas = mem.recall("jalapao", "estrada para Mateiros")
    assert set(_ids(ativas)) == {n1.id, n2.id} and substituidas == []


def test_memoria_local_persiste_em_arquivo(tmp_path):
    caminho = tmp_path / "estado" / "memoria_jalapao.json"
    m1 = MemoriaLocal(caminho)
    n1 = m1.gravar("jalapao", NOTA_1, tipo="nota", fonte="coordenador:teste")
    d = m1.gravar("jalapao", DERIVADA, tipo="derivada", fonte="monitor:periodo-2")
    assert caminho.exists()

    # Outro processo (nova instância) continua de onde parou.
    m2 = MemoriaLocal(caminho)
    assert _ids(m2.listar("jalapao")) == [n1.id, d.id]
    n2 = m2.gravar("jalapao", NOTA_2, tipo="nota", fonte="coordenador:teste")
    assert n2.id == "jalapao:mem-3" and n2.supersedes == n1.id

    m3 = MemoriaLocal(caminho)
    ativas, substituidas = m3.recall("jalapao", "estrada para Mateiros")
    assert n2.id in _ids(ativas) and _ids(substituidas) == [n1.id]
    assert [e["action"] for e in m3.ledger("jalapao")].count("conflict_resolved") == 1

    # Sem caminho, nada vai para o disco.
    MemoriaLocal().gravar("jalapao", NOTA_1, tipo="nota", fonte="c")
    assert sorted(p.name for p in caminho.parent.iterdir()) == ["memoria_jalapao.json"]


def test_local_e_servico_concordam(servico_hmem):
    """A MemoriaLocal reproduz o serviço: mesmos ids, supersedes e substituídas."""
    local, http = MemoriaLocal(), ClienteHMEM(servico_hmem.url)
    passos = [("jalapao", NOTA_1, "nota"), ("jalapao", DERIVADA, "derivada"), ("jalapao", NOTA_2, "nota"),
              ("jalapao", "Ponte do rio Novo interditada", "nota"), ("jalapao", "Ponte do rio Novo liberada", "nota")]
    for regiao, texto, tipo in passos:
        a = local.gravar(regiao, texto, tipo=tipo, fonte="coordenador:teste")
        b = http.gravar(regiao, texto, tipo=tipo, fonte="coordenador:teste")
        assert (a.id, a.supersedes) == (b.id, b.supersedes)
        assert local.ultimos_conflitos == http.ultimos_conflitos
    for consulta in ["estrada para Mateiros", "ponte rio Novo", "célula despriorizada cresceu"]:
        la, ls = local.recall("jalapao", consulta)
        ha, hs = http.recall("jalapao", consulta)
        assert (_ids(la), _ids(ls)) == (_ids(ha), _ids(hs))
    assert [(m.id, m.supersedes) for m in local.listar("jalapao")] == \
           [(m.id, m.supersedes) for m in http.listar("jalapao")]


def test_servico_persiste_entre_reinicios(servico_hmem):
    c = ClienteHMEM(servico_hmem.url)
    n1 = c.gravar("jalapao", NOTA_1, tipo="nota", fonte="coordenador:teste")
    servico_hmem.derrubar()
    servico_hmem.subir()
    c = ClienteHMEM(servico_hmem.url)
    n2 = c.gravar("jalapao", NOTA_2, tipo="nota", fonte="coordenador:teste")
    assert n2.id == "jalapao:mem-2" and n2.supersedes == n1.id
    acoes = [e["action"] for e in c.ledger("jalapao")]
    assert acoes[:2] == ["create", "create"] and "conflict_resolved" in acoes
