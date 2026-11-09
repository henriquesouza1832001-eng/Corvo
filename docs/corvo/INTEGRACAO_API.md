# API de leitura do CORVO para consumidores externos (`/api/v1`)

> **Estado (2026-11-08):** implementada e testada no Worker (`apps/worker/src/routes/corvo-v1.ts`, 191 testes). O CORVO **não conhece nem chama** nenhum consumidor: quem quiser os dados **puxa** com uma chave. O repositório não nomeia nenhum consumidor.

## 1. O que o CORVO entrega e o que não entrega
| Entrega | Não entrega |
|---|---|
| notícias aprovadas por um portão de relevância para mercado, com fonte, confiabilidade, tema, tipo, local e **hipótese** de ativos | decisão de compra e venda, ordens, recomendação |
| `received_at` (quando o CORVO soube), para reconstruir "o que se sabia em T" | direção de preço como fato |
| marca `suspicious` (padrão de injeção de prompt ou golpe no título) | texto de matéria (só título, link e metadados) |
| previsões da taxa-base com intervalo, evidências, método e estado | previsão sem método, ou apresentada como certeza |

## 2. Endpoints (todos `GET`, `Authorization: Bearer cvk_...`)
| Rota | Retorno |
|---|---|
| `/api/v1` | versão do esquema e lista de rotas (sem chave) |
| `/api/v1/evidencias?since=<cursor>&limit=<1..200>` | `{schema_version, generated_at, count, items[], next_cursor}`; sem cursor começa 24 h atrás; ordem de chegada; o cursor nunca anda para trás |
| `/api/v1/previsoes` | até 50 previsões com `probability`, `interval_low/high`, `evidences`, `sources`, `method`, `horizon`, `status` |
| `/api/v1/uso` | uso do dia, limite e plano da própria chave |

Cada item de `evidencias`: `id, title, url, source_id, source_reliability, published_at, received_at, kind, topics[], region, lat, lon, relevance, verdict, asset_hypotheses[], suspicious`.
- `received_at` é o horário de ingestão no CORVO, sempre **igual ou posterior** a quando o coletor viu a notícia: nunca vaza o futuro.
- `asset_hypotheses` é **hipótese de impacto**, nunca direção nem conselho.
- `suspicious=true`: não entregue o título cru a um modelo de linguagem. Texto externo é dado, nunca instrução.
- `kind`: `fato | reportagem | rumor | opiniao | previsao`. Na dúvida, reportagem; só fonte oficial vira fato.

Erros: `401 invalid_key`, `429 quota_exceeded` (com `Retry-After` até a meia-noite UTC e `X-RateLimit-*`), `400 invalid_cursor`.

## 3. Chaves, planos e limites
O operador cria a chave (`ADMIN_TOKEN`), que aparece **uma vez**; o banco guarda só o SHA-256. Rotas do operador: `POST /api/corvo/admin/keys` (`{name, plan, daily_limit?, delay_s?}`), `GET /api/corvo/admin/keys` (nunca devolve a chave) e `POST /api/corvo/admin/keys/:id/revoke`.

| Plano | Para quem | Limite diário | Atraso |
|---|---|---|---|
| `interno` | consumidor de casa, sem custo | 20.000 | nenhum |
| `gratis` | público | 500 | 15 min |
| `pago` | clientes com taxa | 10.000 | nenhum |

Os valores são padrões e podem ser trocados por chave. **Cada chamada válida custa 1 linha de escrita** (o contador de uso) no orçamento do banco; chamada recusada por limite não escreve nada.

## 4. Antes de cobrar de alguém (o que ainda falta, sem enfeite)
1. **Termos das fontes.** O catálogo de feeds foi montado para **uso não comercial** (título, link e resumo curto, com atribuição). Redistribuir títulos de portais (por exemplo Bloomberg, FT, CNBC) numa API **paga** pode violar os termos deles. Antes de cobrar: marcar cada fonte como liberada ou não para uso comercial (as oficiais e de domínio público são as mais seguras) e fazer o plano pago devolver só o que for liberado, ou só **sinais derivados** (contagens, relevância, tema, região, eventos, previsões). Isso precisa de revisão jurídica; este documento não é parecer.
2. **Confiabilidade preditiva.** Hoje há **0 previsões** publicadas e a calibração está "não avaliada": a regra do projeto é só chamar de confiável com **100 ou mais previsões resolvidas e ECE ≤ 0,05**. Até lá, vender "previsão" seria vender uma promessa. O que já tem valor mensurável é a **evidência filtrada, datada e localizada**.
3. **Cobrança.** O Worker controla chave, plano e limite, mas **não cobra**. Pagamento, fatura e cancelamento precisam de um provedor de pagamento e de contrato.
4. **Regulação.** Entregar sinais financeiros pode cair em regras de consultoria ou recomendação (por exemplo a CVM no Brasil). A resposta carrega o aviso de que não é recomendação, mas isso não substitui o parecer de quem entende.
5. **Escala.** O contador de uso escreve no banco a cada chamada. Para muitos consumidores com sondagem frequente, será preciso cache ou limite por minuto antes de crescer.

## 5. Como um consumidor usa
```
curl -H "Authorization: Bearer cvk_..." "https://corvo-api.henriquesouza.workers.dev/api/v1/evidencias?limit=100"
# guarde next_cursor e envie em ?since= na chamada seguinte (a cada 1 a 5 minutos)
```

## 6. Medir antes de depender
| Pergunta | Como medir |
|---|---|
| Os temas do CORVO se equivalem aos do consumidor? | tabela de equivalência em 200 notícias rotuladas à mão |
| O agrupamento em eventos concorda? | 100 pares rotulados "mesmo fato / outro fato"; fusões erradas ≤ 2% |
| O CORVO traz o que o consumidor não tem? | quantas notícias aprovadas não aparecem nos feeds dele |
| O atraso é aceitável? | `received_at − published_at` por fonte (p50 e p90) |
| O consumidor resiste a título adversário? | teste com injeção de prompt e spam |
