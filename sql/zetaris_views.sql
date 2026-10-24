-- FocoCerto: views do Zetaris (especificação, seção 5). Equivalente SQL de app/data/ocorrencias.py.
--
-- Executado por scripts/setup_zetaris.py, um comando por requisição (o script divide em ";" no fim da linha
-- e tira o ponto e vírgula). Antes destas views, o script registra:
--   fococerto_pg.focos            Postgres (CREATE DATASOURCE … jdbc:postgresql://host.docker.internal:…)
--   fococerto_arq.regioes         file store CSV: regiao, lat_min, lat_max, lon_min, lon_max, raio_km, passo_clima
--   fococerto_arq.localidades     file store CSV: regiao, geonameid, nome, lat, lon, pop, pais
--   fococerto_arq.bases           file store CSV: regiao, id, nome, lat, lon, fonte
--   fococerto.clima               view sobre as tabelas REST do Open-Meteo (uma por região, com CACHE TABLE):
--                                 regiao, lat, lon (ponto da grade), dia, vpd_kpa_max, vento_kmh_max, …
--
-- Validação: o mesmo texto (com CREATE SCHEMASTORE VIEW trocado por CREATE OR REPLACE VIEW) roda num Spark 4.0
-- local em sql/validar_views_spark.py, que compara o resultado com o Python. NÃO foi testado num Zetaris real.
-- Sem CTEs (WITH): só subconsultas, por segurança com o parser de views do Zetaris.

-- 1. ocorrencias: focos agrupados em células de 0,1° por dia UTC, com períodos seguidos e focos do dia anterior.
--    periodos_seguidos usa "ilhas" de dias consecutivos: dia − row_number() é constante dentro de cada sequência.
CREATE SCHEMASTORE VIEW ocorrencias WITH CONTAINER fococerto AS
SELECT i.regiao, i.id, i.dia, i.lat, i.lon, i.n_focos, i.frp_soma, i.frp_max, i.primeiro, i.ultimo,
       CAST(ROW_NUMBER() OVER (PARTITION BY i.regiao, i.id, i.ilha ORDER BY i.dia) AS INT) AS periodos_seguidos,
       CAST(CASE WHEN i.dia_ant = date_sub(i.dia, 1) THEN i.n_ant ELSE 0 END AS INT) AS n_focos_ontem
FROM (
    SELECT g.*,
           date_sub(g.dia, CAST(ROW_NUMBER() OVER (PARTITION BY g.regiao, g.id ORDER BY g.dia) AS INT)) AS ilha,
           LAG(g.n_focos) OVER (PARTITION BY g.regiao, g.id ORDER BY g.dia) AS n_ant,
           LAG(g.dia) OVER (PARTITION BY g.regiao, g.id ORDER BY g.dia) AS dia_ant
    FROM (
        SELECT f.regiao,
               concat('cel_', CAST(f.ci AS STRING), '_', CAST(f.cj AS STRING)) AS id,
               f.dia,
               ROUND(AVG(f.lat), 5) AS lat,
               ROUND(AVG(f.lon), 5) AS lon,
               CAST(COUNT(*) AS INT) AS n_focos,
               ROUND(SUM(f.frp), 2) AS frp_soma,
               ROUND(MAX(f.frp), 2) AS frp_max,
               MIN(f.data_hora_utc) AS primeiro,
               MAX(f.data_hora_utc) AS ultimo
        FROM (
            SELECT r.regiao,
                   CAST(p.lat AS DOUBLE) AS lat,
                   CAST(p.lon AS DOUBLE) AS lon,
                   COALESCE(CAST(p.frp AS DOUBLE), 0.0) AS frp,
                   CAST(p.data_hora_utc AS TIMESTAMP) AS data_hora_utc,
                   CAST(p.dia AS DATE) AS dia,
                   CAST(FLOOR(ROUND(CAST(p.lat AS DOUBLE) / 0.1, 9)) AS BIGINT) AS ci,
                   CAST(FLOOR(ROUND(CAST(p.lon AS DOUBLE) / 0.1, 9)) AS BIGINT) AS cj
            FROM fococerto_pg.focos p
            JOIN fococerto_arq.regioes r
              ON CAST(p.lat AS DOUBLE) BETWEEN r.lat_min AND r.lat_max
             AND CAST(p.lon AS DOUBLE) BETWEEN r.lon_min AND r.lon_max
        ) f
        GROUP BY f.regiao, f.ci, f.cj, f.dia
    ) g
) i;

-- 2. ocorrencias_localidades: localidades do cities1000 dentro do raio de exposição da região (haversine).
--    O pré-filtro por caixa (0,2° de lat., 0,3° de lon.) supõe raio_km ≤ 20 e |lat| ≤ 45.
CREATE SCHEMASTORE VIEW ocorrencias_localidades WITH CONTAINER fococerto AS
SELECT x.regiao, x.id, x.dia, x.nome, x.pop, ROUND(x.dist, 1) AS dist_km
FROM (
    SELECT o.regiao, o.id, o.dia, l.nome, CAST(l.pop AS BIGINT) AS pop, r.raio_km,
           2 * 6371.0088 * ASIN(LEAST(1.0, SQRT(
               POWER(SIN(RADIANS(CAST(l.lat AS DOUBLE) - o.lat) / 2), 2)
             + COS(RADIANS(o.lat)) * COS(RADIANS(CAST(l.lat AS DOUBLE)))
             * POWER(SIN(RADIANS(CAST(l.lon AS DOUBLE) - o.lon) / 2), 2)))) AS dist
    FROM fococerto.ocorrencias o
    JOIN fococerto_arq.regioes r ON r.regiao = o.regiao
    JOIN fococerto_arq.localidades l
      ON CAST(l.lat AS DOUBLE) BETWEEN o.lat - 0.2 AND o.lat + 0.2
     AND CAST(l.lon AS DOUBLE) BETWEEN o.lon - 0.3 AND o.lon + 0.3
) x
WHERE x.dist <= x.raio_km;

-- 3. ocorrencias_contexto: população no raio, tempo do ponto da grade (arredondando ao passo da grade) e TI/UC.
--    TI/UC ainda não ingeridos: dist_ti_uc_km = NULL (a exposição usa só a população).
CREATE SCHEMASTORE VIEW ocorrencias_contexto WITH CONTAINER fococerto AS
SELECT o.regiao, o.id, o.dia, o.lat, o.lon, o.n_focos, o.frp_soma, o.frp_max, o.primeiro, o.ultimo,
       o.periodos_seguidos, o.n_focos_ontem,
       CAST(COALESCE(lp.pop_raio, 0) AS BIGINT) AS pop_raio,
       CAST(COALESCE(lp.n_localidades_raio, 0) AS INT) AS n_localidades_raio,
       CAST(NULL AS DOUBLE) AS dist_ti_uc_km,
       CAST(c.vpd_kpa_max AS DOUBLE) AS vpd_kpa,
       CAST(c.vento_kmh_max AS DOUBLE) AS vento_kmh
FROM fococerto.ocorrencias o
JOIN fococerto_arq.regioes r ON r.regiao = o.regiao
LEFT JOIN (
    SELECT regiao, id, dia, SUM(pop) AS pop_raio, COUNT(*) AS n_localidades_raio
    FROM fococerto.ocorrencias_localidades
    GROUP BY regiao, id, dia
) lp ON lp.regiao = o.regiao AND lp.id = o.id AND lp.dia = o.dia
LEFT JOIN fococerto.clima c
  ON c.regiao = o.regiao AND c.dia = o.dia
 AND c.lat = ROUND(ROUND(o.lat / r.passo_clima) * r.passo_clima, 4)
 AND c.lon = ROUND(ROUND(o.lon / r.passo_clima) * r.passo_clima, 4);

-- 4. ocorrencias_prioridade: fórmula da seção 5 (pesos 0,35 / 0,25 / 0,20 / 0,10 / 0,10).
--    Constantes iguais às de app/data/ocorrencias.py: POP_REF 100000, PESO_TI_UC 0,3, HDW_REF 400, PERSIST_REF 4.
CREATE SCHEMASTORE VIEW ocorrencias_prioridade WITH CONTAINER fococerto AS
SELECT k.*,
       ROUND(0.35 * k.c_exposicao + 0.25 * k.c_intensidade + 0.20 * k.c_tempo
           + 0.10 * k.c_persistencia + 0.10 * k.c_crescimento, 4) AS prioridade
FROM (
    SELECT c.regiao, c.id, c.dia, c.lat, c.lon, c.n_focos, c.frp_soma, c.frp_max, c.primeiro, c.ultimo,
           c.periodos_seguidos, c.n_focos_ontem, c.pop_raio, c.n_localidades_raio, c.dist_ti_uc_km,
           c.vpd_kpa, c.vento_kmh,
           CASE WHEN c.dist_ti_uc_km IS NULL
                THEN ROUND(LEAST(1.0, GREATEST(0.0, LOG10(1 + c.pop_raio) / LOG10(1 + 100000))), 4)
                ELSE ROUND(LEAST(1.0, GREATEST(0.0,
                       LEAST(1.0, GREATEST(0.0, LOG10(1 + c.pop_raio) / LOG10(1 + 100000)))
                     + 0.3 * LEAST(1.0, GREATEST(0.0, 1 - c.dist_ti_uc_km / r.raio_km)))), 4)
           END AS c_exposicao,
           CASE WHEN c.frp_soma_max_regiao > 0
                THEN ROUND(LEAST(1.0, GREATEST(0.0, LN(1 + GREATEST(0.0, c.frp_soma)) / LN(1 + c.frp_soma_max_regiao))), 4)
                ELSE 0.0 END AS c_intensidade,
           CASE WHEN c.vpd_kpa IS NULL OR c.vento_kmh IS NULL THEN 0.0
                ELSE ROUND(LEAST(1.0, GREATEST(0.0, (c.vpd_kpa * 10.0) * (c.vento_kmh / 3.6) / 400.0)), 4)
           END AS c_tempo,
           ROUND(LEAST(1.0, GREATEST(0.0, (c.periodos_seguidos - 1) / 3.0)), 4) AS c_persistencia,
           CASE WHEN GREATEST(c.n_focos, c.n_focos_ontem) = 0 THEN 0.0
                ELSE ROUND(LEAST(1.0, GREATEST(0.0,
                       (c.n_focos - c.n_focos_ontem) / CAST(GREATEST(c.n_focos, c.n_focos_ontem) AS DOUBLE))), 4)
           END AS c_crescimento
    FROM (
        SELECT x.*, MAX(x.frp_soma) OVER (PARTITION BY x.regiao, x.dia) AS frp_soma_max_regiao
        FROM fococerto.ocorrencias_contexto x
    ) c
    JOIN fococerto_arq.regioes r ON r.regiao = c.regiao
) k;
