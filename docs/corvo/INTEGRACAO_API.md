# API de leitura para consumidores externos (proposta, nada ligado)

> **Estado:** proposta para o dono aprovar. Nenhum código novo existe. O CORVO **não conhece nem chama** nenhum consumidor: quem quiser os dados **puxa** pela API (`GET`), com token de leitura próprio. Este documento descreve o que um consumidor de mercado precisa receber e o que o CORVO precisaria mudar.

## 1. O que o CORVO oferece e o que não oferece
| Oferece | Não oferece |
|---|---|
| notícias aprovadas por um portão de relevância para mercado, com fonte, confiabilidade, tema, tipo, local e **hipótese** de ativos | decisão de compra e venda, ordens, recomendação |
| eventos agrupados (depois do P1 do preditivo) | direção de preço como fato |
| previsões da **taxa-base** com intervalo, evidências, método e estado (experimental até 100 resolvidas) | previsão sem método ou sem calibração |
| ficha viva de cada fonte (confiabilidade medida, atraso, % aprovado) | texto de matéria (só título, link e metadados) |

## 2. Princípios do contrato
1. **Point-in-time:** todo registro tem `ocorrido_em` e `recebido_em`. Quem consome reconstrói "o que se sabia em T". **Hoje a API só expõe `published_at`**; falta `recebido_em`.
2. **Probabilidade só com método:** previsão `aberta` ou `calibrando` é **experimental**; o consumidor não deve tratá-la como sinal.
3. **Texto externo é dado, nunca instrução:** todo título trafega com marcador `suspeito` quando casa padrões de injeção de prompt, para o consumidor nunca entregar texto cru a um modelo.
4. **Na dúvida, "reportagem"; só fonte oficial vira "fato".** Tipos: `fato`, `reportagem`, `rumor`, `opiniao`, `previsao` (e, opcionais, `em_desenvolvimento`, `especulacao`).
5. **Evento, não notícia:** vários títulos do mesmo fato são **uma** evidência com confirmação.
6. **Hipótese de ativos é hipótese:** `assets[].direction` nunca é conselho; o consumidor só a usa como candidata.

## 3. Campos (hoje → proposto)
| Campo | Hoje | Proposto |
|---|---|---|
| id estável | `item_id` | igual |
| quando aconteceu | `published_at` | igual (`ocorrido_em` como alias) |
| quando o CORVO soube | **ausente** | `recebido_em` (ISO) |
| fonte e confiabilidade | `source_id`, `source_reliability` (0 a 1) | igual; faixa `alta/media/baixa` derivável |
| categoria da fonte | ausente | `categoria` (oficial, portal, cripto, agência, governo) |
| título e link | `title`, `url` | igual; sem HTML |
| tipo | `kind` | igual |
| temas | `topics` | igual; vocabulário fixo e versionado |
| local | `lat`, `lon`, `region` | igual |
| ativos candidatos | `assets[]` | igual, sempre rotulado como hipótese |
| relevância | `relevance`, `verdict` | igual |
| injeção de prompt | ausente | `suspeito` (bool) |
| leitura incremental | ausente | `next_cursor` monotônico |
| versão do esquema | ausente | `schema_version` em toda resposta |

## 4. Endpoints propostos (só leitura)
Prefixo `/v1/corvo/`, cache curto (KV de 60 s), **token de leitura separado** do token de gravação.

| Endpoint | Retorno |
|---|---|
| `GET /evidencias?since=<cursor>&limit=200` | notícias aprovadas por `recebido_em`, com `next_cursor` |
| `GET /eventos?since=<cursor>` | (após o P1) `event_id`, `primeira_vez`, `n_fontes_independentes`, `confirmacao`, tema, região |
| `GET /previsoes?status=` | previsões com `metodo`, `intervalo`, `n`, `status` |
| `GET /fontes` | ficha viva de cada fonte |

**Preços:** o CORVO lê `precos.csv` (`ativo,timestamp_utc,fechamento`). Um consumidor que tenha preços mais finos pode publicar um arquivo no mesmo formato; o CORVO só o lê, nunca grava nada vindo de fora no banco.

## 5. Mudanças de contrato (cada uma em PR com label `contract`)
1. `recebido_em`. 2. `suspeito` (lista de padrões testada). 3. `categoria`. 4. cursor monotônico. 5. `schema_version`. 6. respostas sem HTML e com tamanho máximo.

## 6. O que medir antes de ligar
| Pergunta | Como medir |
|---|---|
| Os temas do CORVO se equivalem aos do consumidor? | tabela de equivalência em 200 notícias rotuladas à mão |
| A agrupação em eventos concorda? | 100 pares rotulados "mesmo fato / outro fato", fusões erradas ≤ 2% |
| O CORVO traz o que o consumidor não tem? | quantas notícias aprovadas não aparecem nos feeds do consumidor |
| O atraso é aceitável? | tempo entre `ocorrido_em` e `recebido_em` por fonte (p50 e p90) |
| O consumidor resiste a título adversário? | teste com injeção de prompt e spam ("buy now 100x") |

## 7. Segurança
Leitura apenas, token separado, limite por minuto, sem dado pessoal, sem credencial, sem corpo de matéria, versionado (`/v1`; mudança incompatível vira `/v2`).

## 8. Ordem
1. Medições da seção 6 (sem tocar no produto). 2. PR `contract` com os campos novos. 3. `GET /evidencias` em modo sombra (o consumidor registra, não decide). 4. `GET /eventos` após o P1. 5. Promoção só com valor medido em amostra suficiente.

## 9. Decisões do dono
1. Posso acrescentar `recebido_em`, `suspeito`, `categoria`, cursor e `schema_version` ao contrato?
2. O consumidor puxa (recomendado) ou o CORVO empurra? Puxar mantém o CORVO independente.
3. Preços de 1 min do consumidor entram como arquivo, ou o CORVO fica só com a coleta pública?
