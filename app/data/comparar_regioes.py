"""Compara regiões candidatas dia a dia com o arquivo FIRMS de 7 dias (confirma a seção 4.1).

Uso: python -m app.data.comparar_regioes [--firms data/raw/firms_7d.csv] [--saida data/cache/REGIAO_7DIAS.md]
Por dia UTC: detecções, ocorrências (células de 0,1°) e ocorrências com localidade (cities1000) a < 15 km.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import RAIZ
from app.data.fontes import ler_firms, ler_geonames
from app.data.ocorrencias import agrupar, localidades_no_raio

REGIOES = {
    "Tocantins/Jalapão": (-13.0, -8.0, -49.5, -45.5),
    "Pantanal": (-22.5, -15.5, -59.5, -54.5),
    "Sudeste do Pará": (-10.0, -4.0, -53.5, -48.0),
    "Península Ibérica": (36.0, 44.0, -10.0, 4.0),
}
RAIO_KM = 15.0


def contar(firms: Path, cities: Path) -> dict[str, list[dict]]:
    out = {}
    for nome, bbox in REGIOES.items():
        focos = ler_firms(firms, bbox)
        locs = ler_geonames(cities, bbox, margem=0.2)
        linhas = []
        for dia in sorted({f["dia"] for f in focos}):
            grupos = agrupar(focos, dia)
            expostas = sum(1 for g in grupos if localidades_no_raio(g["lat"], g["lon"], locs, RAIO_KM))
            linhas.append({"dia": dia, "deteccoes": sum(g["n_focos"] for g in grupos),
                           "ocorrencias": len(grupos), "expostas": expostas})
        out[nome] = linhas
    return out


def markdown(res: dict[str, list[dict]], firms: Path) -> str:
    dias = sorted({l["dia"] for ls in res.values() for l in ls})
    ult = dias[-1] if dias else ""
    md = ["# Escolha da região com o arquivo FIRMS de 7 dias", "",
          f"Fonte: `SUOMI_VIIRS_C2_Global_7d.csv` (NASA FIRMS, VIIRS Suomi-NPP), baixado em 24/10/2026; "
          f"dias UTC {dias[0]} a {ult}. **{ult} está incompleto** (o arquivo termina no meio do dia).",
          "Ocorrência = célula de 0,1° com foco no dia. Exposta = alguma localidade do GeoNames `cities1000` "
          f"(1.000+ hab.) a < {RAIO_KM:.0f} km do centroide dos focos da célula.",
          "Gerado por `python -m app.data.comparar_regioes` (dados reais, nada simulado).", ""]
    for nome, linhas in res.items():
        md += [f"## {nome} {list(REGIOES[nome])}", "",
               "| Dia (UTC) | Detecções | Ocorrências | Ocorrências com localidade < 15 km |", "|---|---|---|---|"]
        for l in linhas:
            md.append(f"| {l['dia']} | {l['deteccoes']} | {l['ocorrencias']} | {l['expostas']} |")
        comp = [l for l in linhas if l["dia"] != ult]
        if comp:
            md.append(f"| **média dias completos** | {sum(l['deteccoes'] for l in comp) / len(comp):.0f} | "
                      f"{sum(l['ocorrencias'] for l in comp) / len(comp):.0f} | "
                      f"{sum(l['expostas'] for l in comp) / len(comp):.0f} |")
        md.append("")
    md += ["## Resumo (média por dia completo)", "",
           "| Região | Detecções | Ocorrências | Expostas | Dias com ≥ 20 ocorrências expostas |", "|---|---|---|---|---|"]
    for nome, linhas in res.items():
        comp = [l for l in linhas if l["dia"] != ult] or [{"deteccoes": 0, "ocorrencias": 0, "expostas": 0}]
        n = len(comp)
        md.append(f"| {nome} | {sum(l['deteccoes'] for l in comp) / n:.0f} | {sum(l['ocorrencias'] for l in comp) / n:.0f} | "
                  f"{sum(l['expostas'] for l in comp) / n:.0f} | {sum(1 for l in comp if l['expostas'] >= 20)} de {n} |")
    md.append("")
    medias = {}
    for nome, linhas in res.items():
        comp = [l for l in linhas if l["dia"] != ult] or [{"ocorrencias": 0, "expostas": 0, "dia": ""}]
        medias[nome] = (sum(l["ocorrencias"] for l in comp) / len(comp), sum(l["expostas"] for l in comp) / len(comp))
    mais_oc = max(medias, key=lambda k: medias[k][0])
    mais_exp = max(medias, key=lambda k: medias[k][1])
    md += ["## Conclusão (calculada)", "",
           f"- Mais ocorrências por dia (escassez): **{mais_oc}** ({medias[mais_oc][0]:.0f}).",
           f"- Mais ocorrências expostas por dia: **{mais_exp}** ({medias[mais_exp][1]:.0f}).",
           "- A contagem varia muito de um dia para outro; para a demo, prefira um dia de pico "
           "(veja a coluna de ocorrências da região principal).", ""]
    return "\n".join(md)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--firms", type=Path, default=RAIZ / "data/raw/firms_7d.csv")
    p.add_argument("--cities", type=Path, default=RAIZ / "data/raw/cities1000.zip")
    p.add_argument("--saida", type=Path, default=RAIZ / "data/cache/REGIAO_7DIAS.md")
    a = p.parse_args(argv)
    texto = markdown(contar(a.firms, a.cities), a.firms)
    a.saida.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
