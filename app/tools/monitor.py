"""monitor: compara com o período anterior e preenche o status (docs/CONTRATOS.md, seção 6)."""
from __future__ import annotations

from app.core.models import Ocorrencia

LIMIAR_CRESCE = 1.25   # +25% em focos ou FRP somado
LIMIAR_DIMINUI = 0.75  # -25%


def _razao(atual: float, anterior: float) -> float:
    if anterior <= 0:
        return float("inf") if atual > 0 else 1.0
    return atual / anterior


def monitor(atuais: list[Ocorrencia], anteriores: list[Ocorrencia]) -> list[Ocorrencia]:
    """Devolve cópias com ``status`` preenchido. Sem par no período anterior: ``nova``, exceto se a própria
    ocorrência diz que já existia (``periodos_seguidos > 1``): aí o par só não veio na lista de anteriores
    (ex.: corte de top N), não dá para comparar, e o status fica ``None`` (sem comparação) em vez de ``nova``.

    Crescendo/diminuindo usa o maior sinal entre nº de focos e FRP somado (subir em qualquer um conta como
    crescer; para diminuir, os dois precisam cair). ``periodos_seguidos`` nunca fica menor que anterior+1.
    """
    ant = {o.id: o for o in anteriores}
    saida = []
    for o in atuais:
        p = ant.get(o.id)
        if p is None:
            status, seguidos = ("nova" if o.periodos_seguidos <= 1 else None), o.periodos_seguidos
        else:
            rf, rp = _razao(o.n_focos, p.n_focos), _razao(o.frp_soma, p.frp_soma)
            if max(rf, rp) >= LIMIAR_CRESCE:
                status = "crescendo"
            elif max(rf, rp) <= LIMIAR_DIMINUI:
                status = "diminuindo"
            else:
                status = "estavel"
            seguidos = max(o.periodos_seguidos, p.periodos_seguidos + 1)
        saida.append(o.model_copy(update={"status": status, "periodos_seguidos": seguidos}))
    return saida
