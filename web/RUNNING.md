# Frontend FocoCerto

React + Vite, Leaflet e lucide-react. O aplicativo consulta a API FastAPI existente, sem carregar mocks. Os textos e os nomes das regiões, períodos, bases, recursos e ocorrências vêm dos endpoints descritos em `README.md`. A interface começa com um exemplo retornado pela API; exemplos são somente leitura e não podem ser aprovados como planos ativos.

## Iniciar com Docker

Na raiz do repositório, com Docker Desktop em execução:

```powershell
docker compose -f web/compose.yaml up -d --build
```

Abra **http://localhost:8000**. Frontend e API são servidos juntos. A publicação da porta fica restrita ao computador local. Os planos, notas e logs ficam em volumes Docker; nenhum arquivo de backend é alterado. O modo inicial dos formulários é `sample: true`, usando os dados reais em cache e agentes determinísticos, sem chaves ou serviços externos.

```powershell
docker compose -f web/compose.yaml logs --tail 50
docker compose -f web/compose.yaml stop
```

Para atualizar após editar o código, repita `up -d --build`. Não use `down -v` se quiser preservar planos e notas.

## Desenvolvimento

```powershell
cd web/app
npm ci
npm run dev
```

O Vite abre em http://localhost:5173 e encaminha `/api` para http://127.0.0.1:8000 (a API do Docker pode continuar em execução).

```powershell
npm run build
npm test
```

O build vai para `web/dist`, conforme o contrato da API. Traduções ficam em `web/app/src/i18n.js`. Os textos narrativos do backend são preservados no idioma do plano; o seletor de idioma controla o próximo plano e os rótulos da interface.

## Conferir os fluxos

1. Visão geral: selecione um exemplo, abra as escalações e expanda uma designação para conferir evidências e componentes da prioridade. Clique em um foco no mapa para ver detalhes.
2. Recursos do dia: comece em branco (nenhuma equipe é inferida) ou escolha explicitamente um cenário. Edite recursos, reserva, notas e o selo de simulação. Clique no mapa para declarar uma base.
3. Gere o plano e acompanhe o job. O plano do mesmo período será substituído. Após a conclusão, o plano ativo permite aprovação com identificação do coordenador. Aprovar não despacha equipes nem resolve escalações.
4. Salve um cenário para reabri-lo. Substituir um cenário salvo exige confirmação; cenários do repositório são protegidos pela API.
5. Registre notas para a próxima execução. Em Raciocínio e memória, consulte pareceres, confiança, memórias e histórico. Nos exemplos, o trace mostra as chamadas e recibos do modelo.

O mapa usa Esri World Street Map e precisa de internet para os tiles. Os dados da demonstração são históricos; o último período de cache pode estar incompleto. A população é a soma das localidades no raio, não uma contagem de pessoas diretamente em risco. ETAs são estimativas, não rotas de navegação.

Limitação do backend atual: `POST /api/aprovar` registra a decisão, mas não atualiza `meta.aprovacao_humana` no arquivo do plano. A interface confirma a aprovação após uma resposta bem-sucedida e mantém esse estado durante a sessão, vinculado à data de geração do plano. Após recarregar a página, prevalece o estado retornado pela API.
