-- FocoCerto: schema do Postgres (especificação, seção 5).
-- Idempotente: pode rodar várias vezes. Aplicar com:
--   .venv/bin/python scripts/ingest_firms.py --aplicar-schema   (ou psql -f sql/postgres.sql)
-- O Zetaris lê estas tabelas (só leitura). O app escreve em decisoes e notas direto aqui.

-- Detecções VIIRS do NASA FIRMS (um registro por detecção).
-- id = sha1(lat|lon|data|hora|satelite)[:16]: o mesmo foco baixado de novo cai no mesmo id (ingestão idempotente).
CREATE TABLE IF NOT EXISTS focos (
    id             TEXT PRIMARY KEY,
    lat            DOUBLE PRECISION NOT NULL,
    lon            DOUBLE PRECISION NOT NULL,
    data_hora_utc  TIMESTAMP NOT NULL,
    satelite       TEXT NOT NULL,
    confianca      TEXT,              -- VIIRS: low | nominal | high
    frp            DOUBLE PRECISION,  -- Fire Radiative Power (MW)
    dia_noite      CHAR(1),           -- D | N
    dia            DATE NOT NULL      -- data UTC da aquisição (= período operacional)
);
CREATE INDEX IF NOT EXISTS focos_dia_idx ON focos (dia);
CREATE INDEX IF NOT EXISTS focos_latlon_idx ON focos (lat, lon);

-- Recursos informados pelo coordenador para um período (na demo: cenários marcados como simulados).
CREATE TABLE IF NOT EXISTS recursos_periodo (
    periodo     TEXT NOT NULL,
    id          TEXT NOT NULL,
    base_id     TEXT NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('terrestre', 'aereo')),
    capacidade  INTEGER NOT NULL DEFAULT 1,
    disponivel  BOOLEAN NOT NULL DEFAULT TRUE,
    simulado    BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (periodo, id)
);

-- Decisões aprovadas (uma linha por designação, recurso em reserva ou ocorrência não atendida).
CREATE TABLE IF NOT EXISTS decisoes (
    seq            BIGSERIAL PRIMARY KEY,
    regiao         TEXT NOT NULL,
    periodo        TEXT NOT NULL,
    ocorrencia_id  TEXT,               -- nulo para acao = 'reserva'
    recurso_id     TEXT,               -- nulo para acao = 'nao_atendida'
    acao           TEXT NOT NULL CHECK (acao IN ('designar', 'reserva', 'nao_atendida')),
    ordem          INTEGER,
    eta_h          DOUBLE PRECISION,
    aprovado_por   TEXT NOT NULL,
    motivo         TEXT,
    evidencias     TEXT,               -- JSON (lista de strings)
    rodada         INTEGER,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS decisoes_periodo_idx ON decisoes (regiao, periodo);

-- Notas do coordenador (também vão para o H-MEM).
CREATE TABLE IF NOT EXISTS notas (
    seq        BIGSERIAL PRIMARY KEY,
    regiao     TEXT NOT NULL,
    periodo    TEXT NOT NULL,
    texto      TEXT NOT NULL,
    autor      TEXT NOT NULL,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);
