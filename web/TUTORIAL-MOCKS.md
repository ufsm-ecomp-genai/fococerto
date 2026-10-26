# Tutorial: front-end com os dados mock (sem a API)

Para começar a tela **sem rodar nada do back-end**: sem Python, sem Zetaris, sem Nightshift, sem chaves.
Os arquivos em `web/mocks/` são **respostas reais da API** (formato idêntico). Quando a tela estiver pronta,
trocar para a API de verdade é mudar **uma linha** (passo 7).

> Regra das submissões: **na versão final e no vídeo, a tela busca os dados pela API**. Mock é só para desenvolver.

## 1. Pegar o projeto
```bash
git clone https://github.com/ufsm-ecomp-genai/fococerto.git
cd fococerto
```
Precisa só de **Node 20+** (`node -v`).

## 2. Criar o app (React + Vite + TypeScript)
A pasta `web/` já tem documentos, então o app vai em `web/app/`:
```bash
cd web
npm create vite@latest app -- --template react-ts
cd app
npm install
npm install leaflet react-leaflet
npm install -D @types/leaflet
```

## 3. Copiar os mocks para dentro do app
Tudo que está em `public/` é servido pelo Vite como arquivo estático:
```bash
mkdir -p public/mocks
cp ../mocks/*.json public/mocks/
```
Depois disso, `http://localhost:5173/mocks/plano_tocantins-escasso-real.json` já abre no navegador.

## 4. Uma camada de dados com a "chave" mock/API
Crie `src/api.ts`. **Toda** chamada da tela passa por aqui; nenhum componente lê arquivo direto.
```ts
// src/api.ts
export const USAR_MOCKS = true;                 // passo 7: trocar para false
const API = "http://localhost:8000";

// endpoint da API -> arquivo mock equivalente
const MOCKS: Record<string, string> = {
  "/api/regioes": "regioes.json",
  "/api/periodos?regiao=tocantins": "periodos_tocantins.json",
  "/api/bases?regiao=tocantins": "bases_tocantins.json",
  "/api/cenarios": "cenarios.json",
  "/api/cenarios/tocantins-escasso": "cenario_tocantins-escasso.json",
  "/api/exemplos": "exemplos.json",
  "/api/exemplos/tocantins-escasso-real": "plano_tocantins-escasso-real.json",
  "/api/exemplos/tocantins-escasso-en": "plano_tocantins-escasso-en.json",
  "/api/exemplos/tocantins-folgado": "plano_tocantins-folgado.json",
  "/api/exemplos/tocantins-escasso-com-nota": "plano_tocantins-escasso-com-nota.json",
  "/api/exemplos/tocantins-parana-analista": "plano_tocantins-parana-analista.json",
};

export async function get<T>(caminho: string): Promise<T> {
  const url = USAR_MOCKS ? `/mocks/${MOCKS[caminho]}` : API + caminho;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} em ${caminho}`);
  return r.json();
}

// POST /api/run: no mock devolve a resposta gravada (job já "aceito");
// o job concluído está em job_concluido.json
export async function gerarPlano(corpo: unknown): Promise<{ job_id: string; status: string }> {
  if (USAR_MOCKS) return (await fetch("/mocks/run_resposta_202.json")).json();
  const r = await fetch(`${API}/api/run`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo),
  });
  return r.json();
}
```

## 5. Os dados de um plano (o que a tela mostra)
Exemplo: `plano_tocantins-escasso-real.json` (a execução real: Zetaris + Nemotron).

| Campo | O que é |
|---|---|
| `meta` | região, período, `idioma`, `modo` (llm/offline), `simulado`, `aprovacao_humana` |
| `status` | `aprova` ou `escala` |
| `escalacoes[]` | **o mais importante**: `{ocorrencia_id, motivo, sugestao}`, o que precisa da decisão humana |
| `plano.designacoes[]` | `{recurso_id, ocorrencia_id, ordem, eta_h, justificativa, evidencias[]}`, a ordem de recursos |
| `plano.reserva[]`, `plano.nao_atendidas[]` | ids de recursos parados e de ocorrências sem equipe |
| `ocorrencias[]` | `{id, lat, lon, n_focos, prioridade (0–1), pop_raio, status, localidades[{nome,pop,dist_km}], componentes{...}}` |
| `bases[]` | `{id, nome, lat, lon, confianca (declarada/oficial/osm/estimada), fonte}` |
| `recursos[]` | `{id, base_id, tipo (terrestre/aereo), disponivel}` |
| `pareceres[]` | do Analista: conclusão + `confianca` (ver `plano_tocantins-parana-analista.json`) |
| `memorias_usadas[]` | notas e lições que mudaram o plano (ver `plano_tocantins-escasso-com-nota.json`) |
| `historico[]` | cada rodada: proposta, violações e veredito do Crítico ("como chegamos aqui") |

Mais detalhes de cada endpoint em `web/README.md`.

## 6. Primeiro componente: mapa + escalações
Troque o `src/App.tsx` por:
```tsx
import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { get } from "./api";

type Plano = any; // depois tipar com base na tabela do passo 5

export default function App() {
  const [p, setP] = useState<Plano | null>(null);
  useEffect(() => { get<Plano>("/api/exemplos/tocantins-escasso-real").then(setP); }, []);
  if (!p) return <p>Carregando…</p>;

  const occ = Object.fromEntries(p.ocorrencias.map((o: any) => [o.id, o]));
  const base = Object.fromEntries(p.bases.map((b: any) => [b.id, b]));
  const rec = Object.fromEntries(p.recursos.map((r: any) => [r.id, r]));
  const escaladas = new Set(p.escalacoes.map((e: any) => e.ocorrencia_id));
  // cor por faixa relativa do dia (igual ao mapa do back-end: tercis da prioridade)
  const prios = p.ocorrencias.map((o: any) => o.prioridade).sort((a: number, b: number) => a - b);
  const t1 = prios[Math.floor(prios.length / 3)], t2 = prios[Math.floor((2 * prios.length) / 3)];
  const cor = (v: number) => (v >= t2 ? "#c62828" : v >= t1 ? "#ef6c00" : "#f9a825");

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <aside style={{ width: 360, overflow: "auto", padding: 12 }}>
        <h2>Escalações ({p.escalacoes.length})</h2>
        {p.escalacoes.map((e: any) => (
          <p key={e.ocorrencia_id}><b>{e.ocorrencia_id}</b>: {e.motivo}</p>
        ))}
        <h2>Ordem de recursos</h2>
        {p.plano.designacoes.map((d: any) => (
          <p key={d.recurso_id}>{d.ordem}. {d.recurso_id} → {d.ocorrencia_id} ({d.eta_h} h)</p>
        ))}
      </aside>
      <MapContainer center={[-10.5, -47.8]} zoom={7} style={{ flex: 1 }}>
        {/* Fundo Esri: o OpenStreetMap bloqueia e o CARTO pede chave */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, USGS, &copy; OpenStreetMap contributors"
        />
        {p.ocorrencias.map((o: any) => (
          <CircleMarker key={o.id} center={[o.lat, o.lon]} radius={6 + Math.sqrt(o.n_focos) * 2}
            pathOptions={{ color: escaladas.has(o.id) ? "#000" : "#333", dashArray: escaladas.has(o.id) ? "4 4" : undefined,
                           fillColor: cor(o.prioridade), fillOpacity: 0.85 }}>
            <Popup>{o.id} · prioridade {o.prioridade.toFixed(2)} · {o.pop_raio} hab.</Popup>
          </CircleMarker>
        ))}
        {p.plano.designacoes.map((d: any) => {
          const b = base[rec[d.recurso_id]?.base_id], o = occ[d.ocorrencia_id];
          if (!b || !o) return null;
          return <Polyline key={d.recurso_id} positions={[[b.lat, b.lon], [o.lat, o.lon]]}
            pathOptions={{ color: "#1565c0", dashArray: rec[d.recurso_id].tipo === "aereo" ? "2 6" : undefined }} />;
        })}
      </MapContainer>
    </div>
  );
}
```
Rodar:
```bash
npm run dev      # abre em http://localhost:5173
```

## 7. Trocar para a API de verdade
Quando a tela estiver boa:
1. Alguém roda a API (em sample mode não precisa de nenhum serviço):
   ```bash
   cd fococerto && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   SAMPLE_MODE=true .venv/bin/uvicorn app.api:app --port 8000
   ```
2. No `src/api.ts`: `USAR_MOCKS = false`. Pronto, a tela passa a usar a API.

## Limites do mock
- **`POST /api/run` não roda nada**: devolve sempre `run_resposta_202.json`, e `job_concluido.json` é o resultado fixo. Para testar a tela de "processando", simule um atraso (`setTimeout`).
- **Salvar cenário, aprovar e registrar nota** não têm efeito no mock: implemente a chamada, mas só dá para testar com a API.
- Os dados são de **um dia do Tocantins** (23/10/2026). Para testar outro dia ou outro cenário, é preciso a API.

## Dicas de tela
- **Escalações sempre em destaque**, no topo. São o que o coordenador precisa decidir.
- Mostrar a **procedência das bases** (`confianca`) e o aviso de **recursos simulados** quando `meta.simulado` for true.
- Nada de número fixo na tela: tudo vem do JSON.
- Idioma: `meta.idioma` diz em que idioma o conteúdo veio (`plano_tocantins-escasso-en.json` é o exemplo em inglês).
