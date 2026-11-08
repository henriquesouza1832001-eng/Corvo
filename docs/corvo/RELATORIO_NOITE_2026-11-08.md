# Relatório da noite — 2026-11-08

**Agente:** codex-noite · **Início:** não registrado · **Atualização:** 2026-11-08 01:30 BRT · coleta em andamento até 07:19 BRT · **Commit inicial:** `4df88e6` · **Último commit técnico:** `61961de`

## 1. Resumo para o dono

- T0: auditoria GET de 31 notícias salvas; 15 keep (48,4%), 14 marginais e 2 drop. A meta de 85% de keep entre gravadas não foi atingida.
- T1: corte HOT normal subiu de 0,75 para 0,91. No lacre, precisão HOT foi de 0,632 para 1,000 e HOT entre aceitos de 0,792 para 0,083.
- Hugin permanece em H2: recall lacrado 0,800 e keep entre gravadas 0,583; o lacre tem só 15 keep e 2 HOT, então a estimativa é instável.
- T8: projeções por 24 h e 5× passaram em normal (484/692), economia (480/672) e crítico (432/432) linhas/dia.
- Munin chegou a M3: seis cenários sintéticos, guarda contra vazamento e HOLD de pesos com amostra pequena; nenhum resultado real foi avaliado.
- O freio ficou verde antes e depois; a aceitação normal projetada permaneceu em 26 de 411 itens no corpus final.
- Suíte Python exigida: 55 testes passaram. T2 e T3 precisam de uma nova avaliação lacrada e pares de deduplicação rotulados.
- Nenhuma fonte foi ligada, nenhuma previsão real foi criada, e não houve deploy nem push.
- Os scripts npm invocaram `wrangler types` e `wrangler deploy --dry-run` indiretamente; o dry-run terminou sem publicar. Isso contrariou a restrição explícita de não rodar Wrangler; não repeti os comandos.

## 2. Condições da noite

| Item | Valor |
|---|---|
| Rede disponível? (T0 e T10 dependem dela) | Sim; GET público do feed respondeu HTTP 200 |
| Ciclos de coleta nesta continuação | 3 ciclos: 36 novos, 0 novos, 19 novos; 24 feeds, sem falhas; laço local ainda ativo |
| Corpus da continuação / feeds | 903 itens únicos / 24 feeds consultados; freio verde |
| Destino da coleta contínua | `%TEMP%\corvo-codex-noite\corpus.jsonl` e `ciclos.log`; área separada porque `engine/data/` está reservada por `claude-hen` |
| Rótulos feitos (ajuste / lacrado) | 225 / 75; total 300 |
| Semente da amostra | 20261108; divisão estável por URL |
| Keep no lacre | 15 de 75; menos de 30, aviso de instabilidade do avaliador |
| Feeds com falha no período | Não medidos; não executei ciclo de coleta |
| GET T0 | `generated_at=2026-11-08T04:02:03.947Z`; orçamento 232/300.000 linhas; estatística do ciclo: 818 recebidas, 17 HOT, 14 BUFFER, 787 DROP |

Os títulos foram rotulados por conteúdo, sem usar o veredito do portão como critério. O feed T0 foi auditado por manchete; não houve leitura de corpo nem verificação factual das alegações. A amostra de Hugin usa um único anotador, portanto casos limítrofes ainda precisam de revisão humana.

## 3. Hugin

### 3.1 Métricas antes e depois

Métricas do `corvo_gate_eval.py`, ponderadas pelo estrato. A linha de base foi calculada antes de mudar o corte; a avaliação lacrada posterior foi executada uma vez. Não usei títulos do lacre para selecionar o corte.

| Métrica | Meta | Antes fit | Antes lacrado | Depois fit | Depois lacrado |
|---|---:|---:|---:|---:|---:|
| Precisão HOT | ≥ 0,85 | 0,617 | 0,632 | 1,000 | 1,000 |
| Recall keep | ≥ 0,90 | 0,540 | 0,800 | 0,540 | 0,800 |
| Keep descartado | mínimo | 0,460 | 0,200 | 0,460 | 0,200 |
| Drop gravado | mínimo | 0,049 | 0,125 | 0,049 | 0,125 |
| Keep entre gravadas | ≥ 0,85 | 0,607 | 0,583 | 0,607 | 0,583 |
| HOT entre aceitos | ≤ 0,25 | 0,770 | 0,792 | 0,082 | 0,083 |
| Fusões erradas / cobertura geo / acerto de `kind` | ≤ 2% / ≥ 85% / ≥ 0,80 | n/d | n/d | n/d | n/d |

O lacre tem 75 itens, 15 keep e 2 HOT depois da mudança. Precisão HOT 1,000 atende o critério de T1, mas tem pouca amostra. Recall e keep entre gravadas não mudaram; ambos continuam abaixo das metas de H3. O nível de Hugin permanece **H2**.

**Freio de banco — antes de mexer:** corpus com 835 itens únicos, volume de 24 h 405, 26 aceitos, 484 linhas/dia, 692 a 5×, fração aceita 0,0642, HOT entre aceitos 0,731. Resultado: dentro dos limites seguros.

**Freio — depois das mudanças:** corpus com 847 itens únicos, volume de 24 h 411:

| Pressão | Aceitos/volume | Linhas/dia | Linhas/dia a 5× | Fração aceita | Resultado |
|---|---:|---:|---:|---:|---|
| Normal | 26/411 | 484 | 692 | 0,0633 | Verde |
| Economia | 24/411 | 480 | 672 | 0,0584 | Verde |
| Crítico | 0/411 | 432 | 432 | 0,0000 | Verde |

Todos os cenários ficaram abaixo de 5.000 linhas/dia, 25.000 a 5×, 12% de aceitação e do teto do Worker de 300.000. A mudança de HOT redistribuiu itens entre HOT e BUFFER; não aumentou o volume aceito.

### 3.2 Mudanças

| # | Tarefa | O que mudou | Efeito no lacre | Commit |
|---|---|---|---|---|
| 1 | T1 | `hot_min`: normal/economia/crítico de 0,75/0,85/0,95 para 0,91/0,95/0,95 | Precisão HOT 0,632→1,000; HOT entre aceitos 0,792→0,083; sem piora de recall ou volume; amostra pequena | `e10d66c` |
| 2 | T8 | Freio agora projeta as três pressões em 1× e 5× | Todos verdes: 484/692, 480/672 e 432/432 linhas/dia | `b1c197e` |

### 3.3 O que piorou ou foi revertido

- Nada foi revertido. A rodada T1 melhorou a seleção HOT, mas não recuperou keep perdidos nem aumentou a precisão total das gravadas.
- T0 continua abaixo da meta: 15/31 keep (48,4%). A precisão HOT manual nesse feed foi 10/17 (58,8%); é um snapshot da versão de produção, pois nenhuma mudança local foi publicada.
- Não reutilizei o lacre para outra regra. Para T2, é necessário um novo conjunto de avaliação sem URLs já vistas; T3 também precisa de pares positivos e negativos rotulados.
- Não houve duas rodadas consecutivas sem melhora; o platô ainda não foi declarado.

### 3.4 Dez exemplos de erros restantes

Exemplos do conjunto **fit**, após o corte T1; não são do lacre.

| # | Título | Rótulo | O que o portão fez | Por quê |
|---:|---|---|---|---|
| 1 | Trump administration moves closer to allowing crypto in 401(k) retirement plans | keep | DROP (`irrelevant`) | Falta léxico para regra de aposentadoria e cripto |
| 2 | Nigeria sets new crypto licensing rules, bans algorithmic stablecoins | keep | DROP (`irrelevant`) | Falta termo para licenciamento e regra cripto fora do léxico atual |
| 3 | Tesla to Wind Down Cybertruck Production as Elon Musk Pivots to Robotaxis and AI | keep | DROP (`irrelevant`) | Falta cobertura explícita de empresas e decisão de produção |
| 4 | Gnosis Pay breach exposes card numbers, home addresses and linked crypto wallets | keep | DROP (`irrelevant`) | Falta combinação de violação de pagamento, carteira e cripto |
| 5 | IREN’s bitcoin mining revenue drops 58% as firm plans full exit by year-end | keep | DROP (`irrelevant`) | Falta cobertura de receita e saída de empresa de mineração |
| 6 | Paraguay’s president quits after millions of people’s savings frozen in bank crisis | keep | DROP (`irrelevant`) | `bank crisis` e congelamento de depósitos não casam com os termos atuais |
| 7 | Global stocks fall amid ‘big worries over AI’ after Democrats’ midterms triumph | keep | DROP (`irrelevant`) | Falta variação de mercado `global stocks fall` |
| 8 | Mais de 1 milhão de correntistas do Banco Ueno foram ressarcidos; crise impacta comércio do Paraguai | keep | DROP (`irrelevant`) | Falta léxico PT para correntistas, ressarcimento e crise bancária |
| 9 | Mercado Bitcoin Said Its Hack Was Contained, But Blockchain Data Tells a Different Story | keep | DROP (`irrelevant`) | Falta variação de nome de exchange e hack com confirmação contestada |
| 10 | Japan considering early ICC funding contribution as court faces U.S. sanctions | drop | BUFFER | `sanctions` dispara comércio apesar do assunto não indicar efeito de mercado suficiente |

### 3.5 Auditoria do que já está no banco (T0)

GET somente leitura no feed público. As classes são relevância editorial, não confirmação de que as alegações são verdadeiras.

| # | Fonte | Título | Rótulo manual | Veredito armazenado |
|---:|---|---|---|---|
| 1 | times-of-israel | US military says strike disabled ship trying to run blockade on Iran | keep | HOT |
| 2 | aljazeera | Iran war live: US moves to block land supply routes; UAE rescues 22 sailors | keep | HOT |
| 3 | cnbc | Risk of Iran war escalation remains high despite Democratic sweep in U.S. midterm elections | marginal | HOT |
| 4 | theblock | Binance CFO steps down nine days after record hack; co-CEO says transition was planned six months ago | keep | BUFFER |
| 5 | straits-times | US military says it disabled cargo vessel in Gulf of Oman | keep | HOT |
| 6 | aljazeera | Abdul El-Sayed slams Trump’s tariff war with Canada | marginal | HOT |
| 7 | straits-times | Explosions heard in Iran's Qeshm Island, Iranian media reports | keep | HOT |
| 8 | bbc-world | Paraguay's former president charged after bank collapse | marginal | HOT |
| 9 | coindesk | Binance users in some European countries told to pull crypto before fees kick in, with accounts closing by year end | marginal | BUFFER |
| 10 | aljazeera | Paraguay’s ousted president charged over banking scandal | marginal | HOT |
| 11 | bbc-world | US offers $20m reward for information about Iran's nuclear programme | marginal | HOT |
| 12 | coindesk | U.S. Treasury moves to cut off crypto exchange MEXC over $16 billion in alleged illicit flows | keep | BUFFER |
| 13 | bbc-world | Houthis say at least 25 killed in Saudi air strike | marginal | BUFFER |
| 14 | theblock | Bitcoin ETFs flip negative for 2026 after $1.28 billion outflow week, worst since June | keep | BUFFER |
| 15 | marketwatch | The S&P 500 could be dangerously exposed to AI. Here are some simple alternatives. | drop | BUFFER |
| 16 | cnbc | Berkshire Hathaway more than doubles buybacks in third quarter as earnings decline | keep | BUFFER |
| 17 | cnbc | Berkshire shares surge as Wall Street swoons amid AI fears | keep | BUFFER |
| 18 | dw | Yemen: 22 killed in strike near Sanaa, Houthis say | marginal | BUFFER |
| 19 | straits-times | Expanding naval blockade, US military looks to constrain Iran on land, and in Caspian Sea | keep | HOT |
| 20 | guardian-world | Blackouts and water shortages in Kyiv after Russia strikes Ukraine’s energy grid | marginal | BUFFER |
| 21 | cnbc | Anthropic IPO meets AI backlash after midterms show stinging rebuke of data centers | marginal | BUFFER |
| 22 | france24 | Banking scandal topples Paraguay leader | marginal | BUFFER |
| 23 | cointelegraph | US sanctions Canadian money-exchange firms over Iran ties | marginal | BUFFER |
| 24 | dw | Ukraine: Russia hits Kyiv with airstrikes ahead of trilateral talks | marginal | BUFFER |
| 25 | cnbc | Trump says U.S. carried out ‘minor strikes’ on Iran as missiles hit Qeshm Island | keep | HOT |
| 26 | guardian-world | Strait of Hormuz could reopen as part of Qatari plan for Iran nuclear inspections | keep | HOT |
| 27 | straits-times | Iran says its forces ‘stronger’ than at beginning of war | marginal | HOT |
| 28 | japan-times | Japan considering early ICC funding contribution as court faces U.S. sanctions | drop | HOT |
| 29 | scmp | Trump confirms fresh Iran strikes days after voters punish war at polls | keep | HOT |
| 30 | japan-times | BOJ’s Ueda says unclear how long 2% inflation rate will remain | keep | HOT |
| 31 | boe-news | Bank rate increased to 4% - November 2026 Monetary Policy Summary and Minutes | keep | HOT |

| Rótulo | Qtde | Percentual |
|---|---:|---:|
| keep | 15 | 48,4% |
| marginal | 14 | 45,2% |
| drop | 2 | 6,5% |

### 3.6 Fichas das fontes (T5)

T5 não executada: o GET fornece um retrato de notícias salvas e contagens por fonte, não uma janela de ciclos por fonte suficiente para estimar idade, duplicatas, rendimento e quem publicou primeiro. Nenhuma confiabilidade foi alterada e nenhuma fonte foi desativada.

## 4. Munin

### 4.1 Invariantes e bancada

O `corvo_munin_eval.py --synthetic` cobre seis casos determinísticos. Saídas principais:

| Cenário | n | Brier | Brier da taxa-base | Skill | ECE | Resultado |
|---|---:|---:|---:|---:|---:|---|
| Calibrado | 3.000 | 0,1616 | 0,2499 | +0,353 | 0,0143 | Calibração confiável, sintética |
| Exagerado | 3.000 | 0,2278 | 0,2499 | +0,089 | 0,2113 | Calibrando; confiança exagerada |
| Taxa-base anterior 0,50 | 3.000 | 0,2500 | 0,2500 | +0,000 | 0,0113 | Calibrado, sem ganho sobre a régua |
| Conservador | 3.000 | 0,1845 | 0,2500 | +0,262 | 0,1318 | Calibrando; probabilidades encolhidas demais |
| Pouca amostra | 12 | 0,1047 | 0,2500 | +0,581 | 0,1773 | EXPERIMENTAL; pesos em HOLD porque 12 < 30 |
| Vazamento temporal | — | — | — | — | — | Linha recebida depois do corte bloqueada antes da pontuação |

O Skill alto do cenário com 12 itens é um exemplo de sorte possível em amostra pequena, não uma melhora. A bancada o deixa EXPERIMENTAL e impede a atualização de pesos.

Novos testes M1/M2: BUFFER conserva apenas campos permitidos; DROP continua sem texto; o registro aceita probabilidades exatamente em 0 e 1 quando o intervalo as contém; o guard de vazamento recusa dados recebidos após `as_of`. A suíte completa exigida passou, **55 testes**.

### 4.2 Propostas para aprovação do dono (sem mudar contrato)

**M3 — tema para ativos.** Proposta inicial, sem ligação automática e sem pesos enquanto não houver amostra:

| Tema | Ativos candidatos | Hipótese de direção | Horizonte |
|---|---|---|---|
| `banco_central` (decisão de corte) | USD, BTC, ouro, índices | USD ↓; BTC/ouro ↑ | 24 h |
| `energia` (corte de oferta OPEP) | petróleo, moedas de exportadores | petróleo ↑ | 24 h |
| `conflito_chave` (Golfo/rota marítima) | petróleo, ouro | volatilidade ↑ | 6 h a 3 d |
| `cripto` (hack de exchange) | token afetado, BTC | risco/pressão de baixa ↑ | 6 h |
| `comercio` (tarifa/sanção) | pares cambiais e ativos afetados | volatilidade ↑ | 24 h |

São hipóteses, não previsões nem fatos. Sem dados suficientes, resultado `INSUFFICIENT_DATA`.

**M6 — regra de aprendizado proposta:** mínimo de 30 resultados resolvidos por tema ou fonte e 100 no total antes de avaliar confiança; ajuste no trecho temporal mais antigo, validação no próximo e teste final no trecho mais recente (sem embaralhar); Benjamini–Hochberg com q≤0,05 para a família de temas/fontes testada, reportando o total de hipóteses; só aceitar peso versionado se bater a taxa-base, tiver Skill > 0 e ECE ≤ 0,05. Cada artefato precisa ser reversível. Não há hoje dados reais para executar essa regra.

## 5. Fontes

Nenhuma fonte nova sugerida ou ligada nesta rodada. T0 usou apenas GET no feed público já existente. T10 não foi executada porque não houve proposta de fonte nova.

## 6. Agrupamento por acontecimento (T11)

Não medido. A amostra não tem pares positivos/negativos rotulados para estimar fusões erradas ou economia de linhas; não proponho mudança de contrato sem essa medição.

## 7. Perguntas para o dono

1. Você confirma os rótulos marginais de T0 para comentários de banco central, conflito periférico, sanções específicas e balanços de empresas?
2. O novo corte HOT 0,91/0,95/0,95 pode permanecer até coletarmos um lacre maior, embora o lacre atual tenha apenas 15 keep?
3. Você aprova M6 com mínimo de 30 por tema/fonte, mínimo de 100 no total, Benjamini–Hochberg q≤0,05 e divisão temporal 70/15/15?
4. Pode ser gerado um conjunto novo e sem URLs já avaliadas para continuar T2? O lacre atual não será reutilizado para escolher outra regra.

## 8. Próximos passos sugeridos

1. Conseguir um conjunto lacrado novo e maior, com pelo menos 30 keep no lado de avaliação, antes de ajustar T2.
2. Usar o fit para corrigir falsos negativos de cripto, empresas, mercado e português; medir freio a cada candidato.
3. Rotular pares de duplicação positivos e negativos antes de T3.
4. Revisar manualmente os casos T0 marginais e confirmar o critério de relevância com o dono.
5. Esperar previsões reais resolvidas e registrar fontes de preços antes de declarar M4 ou qualquer acerto de Munin.

## 9. Conferência final

- [x] Suíte Python exigida: 55 testes passaram.
- [x] `corvo_budget_check.py` passou antes de cada commit; projeções verdes nos três níveis de pressão.
- [x] `sh scripts/gitcrypt_check.sh`: nenhum segredo em texto puro no índice.
- [x] Corpus, rótulos locais e SQLite não foram adicionados ao Git.
- [x] Branch `hen`; commits locais sem push; trava liberada após os commits técnicos.
- [x] Nenhum arquivo de `apps/worker`, `database`, `packages/shared` ou `.github/workflows` ficou alterado.
- [x] Incidente de comando registrado: `npm run typecheck` acionou `wrangler types`; `npm run build` acionou `wrangler deploy --dry-run`. Ambos saíram com código 0; o segundo encerrou em dry-run sem deploy. Esses scripts não serão executados novamente nesta tarefa.
