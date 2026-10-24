from app.core.models import Base, Designacao, Plano
from app.tools.alocador import alocador_simples
from app.tools.citacoes import checar_citacoes
from app.tools.memorias import interpretar_memorias
from app.tools.regras import checar_regras
from tests.fakes import MemoriaFake, oc, rec, regiao_teste

CFG = regiao_teste()
BN = Base(id="bn", nome="Base Norte", lat=-10.0, lon=-47.0)
BS = Base(id="bs", nome="Base Sul", lat=-10.8, lon=-47.0)
VILA = [{"nome": "Vila Alegre", "pop": 500, "dist_km": 4.0}]


def _regras(v):
    return sorted(x.regra for x in v)


# ------------------------------------------------------------------ alocador_simples
def test_alocador_maior_prioridade_recebe_o_mais_proximo():
    occs = [oc("a", -10.1, -47.0, 0.9), oc("b", -10.7, -47.0, 0.5)]
    p = alocador_simples(occs, [rec("t1", "bn"), rec("t2", "bs")], [BN, BS], CFG, reserva=0)
    assert [(d.recurso_id, d.ocorrencia_id) for d in p.designacoes] == [("t1", "a"), ("t2", "b")]
    assert p.nao_atendidas == [] and p.reserva == []


def test_alocador_respeita_reserva_eta_e_disponibilidade():
    occs = [oc("a", -10.1, -47.0, 0.9), oc("b", -10.7, -47.0, 0.8), oc("longe", -12.9, -49.4, 0.95)]
    recs = [rec("t1", "bn"), rec("t2", "bs"), rec("t3", "bs", disponivel=False)]
    p = alocador_simples(occs, recs, [BN, BS], CFG, reserva=1)
    assert len(p.designacoes) == 1 and p.designacoes[0].ocorrencia_id == "a"
    assert "longe" in p.nao_atendidas and "b" in p.nao_atendidas
    assert p.reserva == ["t2"]
    assert all(d.eta_h <= CFG.eta_max_h for d in p.designacoes)


def test_plano_do_alocador_passa_no_checar_citacoes():
    occs = [oc("a", -10.1, -47.0, 0.9, pop=500, localidades=VILA)]
    recs = [rec("t1", "bn")]
    p = alocador_simples(occs, recs, [BN, BS], CFG, reserva=0)
    assert checar_citacoes(p, occs, [BN, BS], recursos=recs, regiao_cfg=CFG) == []
    assert checar_regras(p, occs, recs, [BN, BS], CFG, []) == []


# ------------------------------------------------------------------ checar_regras
def _plano(*pares, eta=0.4):
    return Plano(periodo="p", regiao="teste", designacoes=[
        Designacao(recurso_id=r, ocorrencia_id=o, ordem=i + 1, eta_h=eta, justificativa="x")
        for i, (r, o) in enumerate(pares)])


def test_regras_capacidade_duplicado_eta_indisponivel():
    occs = [oc("a", -10.1, -47.0, 0.9), oc("b", -10.2, -47.0, 0.8), oc("longe", -12.9, -49.4, 0.5)]
    recs = [rec("t1", "bn"), rec("t2", "bn", disponivel=False)]
    v = checar_regras(_plano(("t1", "a"), ("t1", "a"), ("t1", "b"), ("t2", "longe")), occs, recs, [BN], CFG, [])
    r = _regras(v)
    assert "recurso_duplicado" in r and "capacidade_excedida" in r
    assert "eta_acima_limite" in r and "recurso_indisponivel" in r
    assert all(x.rigida for x in v)


def test_regra_exposta_sem_recurso_enquanto_sem_exposicao_recebe():
    occs = [oc("vida", -10.1, -47.0, 0.5, pop=300), oc("mato", -10.2, -47.0, 0.9)]
    v = checar_regras(_plano(("t1", "mato")), occs, [rec("t1", "bn")], [BN], CFG, [])
    assert [x.regra for x in v] == ["exposta_sem_recurso"] and v[0].ocorrencia_id == "vida"


def test_regra_exposicao_sem_recurso_viavel_e_exposta_nao_atendida():
    occs = [oc("v1", -10.1, -47.0, 0.9, pop=100), oc("v2", -10.2, -47.0, 0.8, pop=100),
            oc("longe", -12.9, -49.4, 0.7, pop=50)]
    v = checar_regras(_plano(("t1", "v1")), occs, [rec("t1", "bn")], [BN], CFG, [])
    por = {x.ocorrencia_id: x for x in v}
    assert por["longe"].regra == "exposicao_sem_recurso_viavel" and por["longe"].rigida
    assert por["v2"].regra == "exposta_nao_atendida" and not por["v2"].rigida


def test_regra_reserva_vinda_da_memoria_e_restricao_de_memoria():
    mem = MemoriaFake()
    m1 = mem.gravar("teste", "Coordenador: manter uma aeronave de reserva", "nota", "cli")
    m2 = mem.gravar("teste", "Estrada da Base Norte alagada", "nota", "cli", confianca=0.9)
    occs = [oc("a", -10.1, -47.0, 0.9)]
    recs = [rec("t1", "bn"), rec("av1", "bs", tipo="aereo")]
    v = checar_regras(_plano(("t1", "a"), ("av1", "a")), occs, recs, [BN, BS], CFG, [m1, m2])
    por = {x.regra: x for x in v}
    assert por["reserva_nao_mantida"].evidencia["pedida"] == 1
    assert por["restricao_memoria"].recurso_id == "t1" and not por["restricao_memoria"].rigida
    assert por["restricao_memoria"].evidencia["memoria_id"] == m2.id


def test_memoria_liberacao_posterior_anula_bloqueio():
    mem = MemoriaFake()
    a = mem.gravar("teste", "estrada para a Base Norte alagada", "nota", "cli")
    b = mem.gravar("teste", "estrada da Base Norte liberada", "nota", "cli", supersedes=a.id)
    assert "bn" in interpretar_memorias([a], [BN], []).bases_bloqueadas
    assert interpretar_memorias([a, b], [BN], []).bases_bloqueadas == {}
    # "intransitável" bloqueia (não confundir com "transitável")
    c = mem.gravar("teste", "acesso à Base Norte intransitável", "nota", "cli")
    assert "bn" in interpretar_memorias([c], [BN], []).bases_bloqueadas


# ------------------------------------------------------------------ checar_citacoes
def test_citacao_errada_no_texto_e_nas_evidencias():
    occs = [oc("a", -10.1, -47.0, 0.9, pop=500, localidades=VILA),
            oc("b", -10.6, -47.0, 0.5, localidades=[{"nome": "Ponte Alta", "pop": 200, "dist_km": 3.0}])]
    recs = [rec("t1", "bn")]
    d = Designacao(recurso_id="t1", ocorrencia_id="a", ordem=1, eta_h=0.39,
                   justificativa="Vila Alegre a 25 km, 900 habitantes, perto de Ponte Alta; chega em ETA 3 h.",
                   evidencias=["pop:900", "dist:Vila Alegre:25"])
    v = checar_citacoes(Plano(periodo="p", regiao="teste", designacoes=[d]), occs, [BN], recursos=recs,
                        regiao_cfg=CFG)
    campos = sorted(x.evidencia["campo"] for x in v)
    assert all(x.regra == "citacao_incorreta" for x in v)
    assert campos == ["dist", "dist_texto", "eta_texto", "localidade", "pop", "pop_texto"]


def test_nome_da_base_de_saida_nao_e_localidade_citada():
    # regressão: base com nome de cidade ("Ponte Alta (simulada)") que também é localidade de outra ocorrência
    base = Base(id="pa", nome="Ponte Alta (simulada)", lat=-10.6, lon=-47.0, simulada=True)
    occs = [oc("a", -10.1, -47.0, 0.9, pop=500, localidades=VILA),
            oc("b", -10.6, -47.0, 0.5, localidades=[{"nome": "Ponte Alta", "pop": 200, "dist_km": 3.0}])]
    recs = [rec("t1", "pa")]
    p = alocador_simples(occs[:1], recs, [base], CFG, reserva=0)
    assert "Ponte Alta (simulada)" in p.designacoes[0].justificativa
    assert checar_citacoes(p, occs, [base], recursos=recs, regiao_cfg=CFG) == []


def test_id_do_recurso_nao_e_localidade_citada():
    # regressão: id "ponte-alta-t1" contém o nome de uma localidade de outra ocorrência
    occs = [oc("a", -10.1, -47.0, 0.9, pop=500, localidades=VILA),
            oc("b", -10.6, -47.0, 0.5, localidades=[{"nome": "Ponte Alta", "pop": 200, "dist_km": 3.0}])]
    recs = [rec("ponte-alta-t1", "bn")]
    p = alocador_simples(occs[:1], recs, [BN], CFG, reserva=0)
    assert checar_citacoes(p, occs, [BN], recursos=recs, regiao_cfg=CFG) == []


def test_citacao_eta_h_do_campo_errado():
    occs = [oc("a", -10.1, -47.0, 0.9)]
    d = Designacao(recurso_id="t1", ocorrencia_id="a", ordem=1, eta_h=4.0, justificativa="ok")
    v = checar_citacoes(Plano(periodo="p", regiao="teste", designacoes=[d]), occs, [BN],
                        recursos=[rec("t1", "bn")], regiao_cfg=CFG)
    assert [x.evidencia["campo"] for x in v] == ["eta_h"]
