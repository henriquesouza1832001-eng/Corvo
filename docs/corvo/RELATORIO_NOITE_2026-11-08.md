# Relatório da noite — 2026-11-08

> **Rodada nota8 em andamento desde 19:30 BRT; checkpoint 21:30 BRT:** cadeia Munin, T9, T6 e censo T5 concluídos; ciclo 13 encerrou e coleta externa ainda ativa (PID 13596), sem reinício. Veja as atualizações nas seções 9.13–9.41.

**Agente:** codex-noite · **Sessões anteriores:** 01:19–01:39, 10:53–17:42 e retomadas curtas às 18:10 e 18:31 BRT; cada uma encerrou após `PARE` · **Rodada atual:** autorizada às 19:30 BRT, ativa às 21:30 · **Commits desta rodada:** `b4ac7b0`, `bae075e`, `12d17bb`, `e62deec`, `1084877`, `4dd7b9d`, `34e59d7`, `b28fcf3`, `4c7838f`, `0c29e4a`, `5f2aef8`, `3dd2a7a`

> **Correção de cronologia:** a versão anterior dizia que a coleta seguiria até 07:19. O log confirma que a primeira sessão terminou após o ciclo das 01:39; não houve coleta contínua até 07:19. A coleta foi retomada às 10:53 BRT e permaneceu ativa até o dono solicitar parada às 17:42.

## 1. Resumo para o dono

- T0 (fotografia GET mais recente): 31 notícias no bucket atual; rótulos manuais por título: 22 keep (71,0%), 8 marginais, 1 drop. A meta de 85% de keep não foi atingida; a fotografia está atrasada ~20,5 h.
- T1: corte HOT normal subiu de 0,75 para 0,91. No lacre, precisão HOT foi de 0,632 para 1,000 e HOT entre aceitos de 0,792 para 0,083.
- Hugin permanece em H2: o lacre anterior tinha 15 keeps; a amostra fresca teve 21/307 keeps no eval, recall 0,190 e precisão HOT n/d, abaixo das metas e instável. Nenhuma regra foi escolhida com exemplos do lacre.
- T8: projeções por 24 h e 5× passaram em normal (484/692), economia (480/672) e crítico (432/432) linhas/dia.
- Correção posterior: a primeira raspagem terminou às 01:39; foi retomada às 10:53 e concluiu 41 ciclos até 17:33, com 595 itens novos; houve um 404 isolado no ciclo 15 e nenhum feed falhou nos ciclos 16–41 (detalhes na seção 9). A coleta foi encerrada às 17:42 após o dono escrever `PARE`.
- Munin chegou a M3: seis cenários sintéticos, guarda contra vazamento e HOLD de pesos com amostra pequena; nenhum resultado real foi avaliado. Reprova sintética mais recente repetiu os seis cenários; painel local tem 59 eventos, 104 perguntas, 0 previsões e 104 abstenções.
- Nesta rodada, o corpus local está em 1.313 URLs; ciclo 13 trouxe 3 itens e nenhum preço novo; o único erro recente foi um 404 isolado em `fed-press` no ciclo 10. O freio está verde: 462 linhas/dia, 582 a 5×, 432/432 sob pressão crítica.
- T6 geolocalização: após o ciclo 13, a amostra dinâmica de ajuste tem 55 aprovados; a cobertura por título subiu de 39/55 (70,9%) para 47/55 (85,5%). O acerto conservador permanece 46/47 (97,9%), contando um caso ambíguo como erro. As oito manchetes sem ponto não citam lugar localizável.
- T5 (24 h, sem URLs do eval): 1.008 itens únicos em 23 feeds; G1 tem 210 e zero aceitos; 55 itens aceitos no total. Não ajustei `reliability`/`enabled`, pois sem rótulo de falso negativo a taxa de descarte não justifica desligar a fonte.
- Suíte obrigatória: 55 testes passaram; os testes `test_corvo_*.py` passaram (48), e as suítes Munin de pergunta/backtest passaram (10). T2 ainda precisa de um novo lacre adequado; T3 precisa de pares rotulados.
- Nota 8 ainda não foi declarada: o lacre fresco tem 21 keeps, abaixo dos 40 exigidos; o recall de eval é 0,190. Não usei o resultado para selecionar regras.
- Nenhuma fonte foi ligada, nenhuma previsão real foi criada, e não houve deploy, POST ou push nesta rodada.
- Os scripts npm invocaram `wrangler types` e `wrangler deploy --dry-run` indiretamente; o dry-run terminou sem publicar. Isso contrariou a restrição explícita de não rodar Wrangler; não repeti os comandos.

## 2. Condições da noite

| Item | Valor |
|---|---|
| Rede disponível? (T0 e T10 dependem dela) | Sim; GET público do feed respondeu HTTP 200 |
| Ciclos de coleta | Sessões anteriores: 01:19–01:39 e 10:53–17:33; rodada atual desde 19:30: ciclo 11 terminou, 24 feeds consultados, 3 novos itens |
| Corpus da rodada atual / feeds | `engine/data/corvo_corpus/corpus.jsonl`: 1.303 URLs únicas / 24 feeds consultados; freio verde |
| Destino da coleta contínua | `engine/data/corvo_corpus/corpus.jsonl`, `ciclos.log` e `precos.csv`; processo externo PID 13596, iniciado pelo dono às 19:30 BRT |
| Rótulos feitos (ajuste / lacrado) | 225 / 75; total 300 |
| Semente da amostra | 20261108; divisão estável por URL |
| Keep no lacre | 15 de 75; menos de 30, aviso de instabilidade do avaliador |
| Feeds com falha no período | 0 nos 3 ciclos iniciais; um HTTP 404 no ciclo 15 da retomada; 0 nos ciclos 16–41 |
| GET T0 mais recente | `generated_at=2026-11-08T23:40:46Z`; orçamento 232/300.000 linhas; estatística do ciclo: 818 recebidas, 17 HOT, 14 BUFFER, 787 DROP |

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
| Fusões erradas / cobertura geo / acerto de `kind` | ≤ 2% / ≥ 85% / ≥ 0,80 | n/d | n/d | n/d | ver T6: cobertura 70,4%→85,2%; acerto conservador 45/46 |

O lacre tem 75 itens, 15 keep e 2 HOT depois da mudança. Precisão HOT 1,000 atende o critério de T1, mas tem pouca amostra. Recall e keep entre gravadas não mudaram; ambos continuam abaixo das metas de H3. O nível de Hugin permanece **H2**.

**Freio de banco — antes de mexer:** corpus com 835 itens únicos, volume de 24 h 405, 26 aceitos, 484 linhas/dia, 692 a 5×, fração aceita 0,0642, HOT entre aceitos 0,731. Resultado: dentro dos limites seguros. Antes do commit T6, o corpus tinha 1.303 URLs; freio será repetido após a mudança.

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

## 9. Continuação iniciada às 10:53 BRT (em andamento)

### 9.1 Coleta e freio

O coletor local consultou os mesmos 24 feeds em oito ciclos de dez minutos, sempre com `--dry-run`, sem POST ou escrita no corpus oficial. Todos os ciclos retornaram `collect_exit=0`, `budget_exit=0`, `feeds_failed={}` e pressão normal.

| Ciclo | Hora BRT | Itens novos |
|---:|---:|---:|
| 1 | 10:53 | 258 |
| 2 | 11:03 | 13 |
| 3 | 11:13 | 9 |
| 4 | 11:23 | 10 |
| 5 | 11:33 | 19 |
| 6 | 11:43 | 9 |
| 7 | 11:53 | 6 |
| 8 | 12:03 | 14 |
| 9 | 12:13 | 8 |
| 10 | 12:23 | 15 |
| 11 | 12:33 | 7 |
| 12 | 12:43 | 5 |
| 13 | 12:53 | 11 |
| 14 | 13:03 | 5 |
| 15 | 13:13 | 4 (23 feeds; `fed-press` HTTP 404) |
| 16 | 13:23 | 8 (24 feeds; sem falhas) |
| 17 | 13:33 | 11 |
| 18 | 13:43 | 8 |
| 19 | 13:53 | 11 |
| **Total** | | **431** |

O scratch começou esta retomada em **905 itens únicos**. Antes da retomada, o freio estava verde: volume 24 h 462, 25 aceitos, normal 482 linhas/dia e 682 a 5×; economia 478/662; crítico 432/432. Após o ciclo 19: **1.336 itens únicos**, volume 24 h 750, 22 aceitos e HOT share 0,045; normal **476/652**, economia **476/652**, crítico **432/432**. Todas as pressões seguem abaixo dos limites.

O corpus oficial local não foi alterado. A checagem de referência e a checagem após a auditoria T0 deram o mesmo resultado: 904 URLs únicas, volume 24 h 465, 27 aceitos, normal 486/702, economia 482/682 e crítico 432/432; freio verde.

### 9.2 T0 parcial, somente leitura

Na cópia local oficial: 906 linhas, 904 URLs únicas, duas linhas duplicadas e 23 fontes. Recalculando somente o escore por título atual, 86 itens passam o corte BUFFER e 7 deles chegam a HOT. Isso não é taxa de acerto editorial nem auditoria do banco remoto. Não houve leitura de Turso ou API de produção. A rodada usou apenas agregados; nenhum título lacrado foi aberto.

### 9.3 Hugin — T2 experimental, corte não promovido

Hipótese congelada no ajuste: BUFFER normal 0,50 → candidato 0,45. O candidato foi comparado uma vez no lacrado, depois de rotular os itens, sem usar esses títulos para escolher a regra.

| Métrica | Ajuste 0,50 | Ajuste 0,45 | Lacrado 0,50 | Lacrado 0,45 |
|---|---:|---:|---:|---:|
| Recall keep | 0,176 | 0,471 | 0,000 | 0,571 |
| Keep entre gravadas | 0,375 | 0,533 | 0,000 | 0,571 |
| Drop gravado | 0,125 | 0,133 | 0,000 | 0,000 |
| HOT entre aceitos | 0,000 | 0,000 | 0,000 | 0,000 |

O lacrado tem 63 itens e só 7 `keep`; o avaliador alerta que a métrica é instável. O corte 0,45 recuperou alguns casos no lacrado, mas o ajuste piorou `drop_gravado` em 0,008. **Não foi aplicado nem commitado código de Hugin**; o corte continua 0,50. Hugin permanece **H2**.

### 9.4 Munin e entregas da retomada

- `corvo_munin_eval.py --synthetic`: seis cenários sintéticos, com vazamento bloqueado e pesos em HOLD para `n=12`; nenhuma previsão real avaliada.
- Testes de Munin: **30 passaram** (`test_munin.py` e `test_munin_baseline.py`).
- A regra M6 operacional foi registrada em `HUGIN_MUNIN_TREINO.md`: eventos independentes, mínimo 30 por chave/fonte, walk-forward temporal, Benjamini–Hochberg `q=0.05`, ganho sobre taxa-base e dois períodos futuros consecutivos. É uma proposta, ainda sem validação com resultados reais.
- O intervalo do baseline usa aproximação normal da posterior Beta; a documentação agora diz que não são quantis exatos e que a cobertura ainda precisa de validação. Sem mudança nas probabilidades; 30 testes de Munin passaram.
- Munin permanece **M3**; não há resultado real ou nível M4 alegado.
- Commits locais desta retomada: `8fc9156`, `0174825`, `9ef3694`, `66fd55a`, `a351101`, `365c2c2`. Nenhum push: não foi verificado CI verde.

### 9.5 T3 — disponibilidade de pares de deduplicação

Nos 173 itens coletados depois da amostra usada para T2, um censo agregado encontrou 2 pares entre fontes com Jaccard ≥ 0,40, 1 com Jaccard ≥ 0,50/0,60 e nenhum no corte atual de 0,70. Não rotulei nem abri títulos lacrados. É insuficiente para estimar fusões erradas; o corte de deduplicação foi mantido.

O único erro de feed desta retomada foi o HTTP 404 do `fed-press` no ciclo 15; o ciclo 16 voltou sem falhas.

### 9.6 Perguntas atualizadas para o dono

1. Confirma manter o corte BUFFER em 0,50 até haver um lacrado novo com pelo menos 30 casos `keep`?
2. Confirma os rótulos marginais do snapshot T0 listados na seção 3.5?
3. Há objeção ao protocolo M6 temporal + Benjamini–Hochberg `q=0.05`, mantido em HOLD até cumprir os critérios?
4. Mantemos G1 habilitado até revisar falsos negativos em uma amostra rotulada por fonte?

### 9.7 Continuidade da coleta até 14:53 BRT

Após o checkpoint de 13:53, os ciclos 20–25 concluíram às 14:03, 14:13, 14:23, 14:33, 14:43 e 14:53, com 6, 12, 5, 14, 9 e 5 itens novos, respectivamente (51 no trecho). Todos usaram `--dry-run`; os 24 feeds responderam sem falhas e cada ciclo retornou `collect_exit=0` e `budget_exit=0`. O acumulado da retomada passou de 431 para 482 itens novos e o corpus temporário chegou a 1.387 únicos.

Freio às 14:53: corpus temporário com volume 24 h 784, aceitos 21, HOT entre aceitos 0,048; normal/economia 474 linhas/dia e 642 a 5×; crítico 432/432. Corpus oficial local: volume 24 h 465, aceitos 27, HOT entre aceitos 0,074; normal 486/702, economia 482/682 e crítico 432/432. Ambos dentro dos limites seguros. Não houve alteração de regra de Hugin nem leitura de novos títulos lacrados neste checkpoint; Hugin segue H2 e Munin M3, sem previsões reais.

O coletor permanece em execução, com intervalo de dez minutos. Naquele checkpoint, a próxima verificação estava prevista para 15:03 BRT. O relatório será atualizado antes do encerramento explícito do dono (`PARE`).

### 9.8 Continuidade da coleta até 15:53 BRT

Após o checkpoint de 14:53, os ciclos 26–31 concluíram às 15:03, 15:13, 15:23, 15:33, 15:43 e 15:53, com 6, 9, 15, 8, 6 e 8 itens novos, respectivamente (52 no trecho). Todos usaram `--dry-run`; os 24 feeds responderam sem falhas e cada ciclo retornou `collect_exit=0` e `budget_exit=0`. O acumulado da retomada passou de 482 para 534 itens novos e o corpus temporário chegou a 1.439 únicos.

Freio às 15:53: corpus temporário com volume 24 h 824, aceitos 19, HOT entre aceitos 0,053; normal/economia 470 linhas/dia e 622 a 5×; crítico 432/432. Corpus oficial local: volume 24 h 465, aceitos 27, HOT entre aceitos 0,074; normal 486/702, economia 482/682 e crítico 432/432. Ambos dentro dos limites seguros. Sem alteração de regra de Hugin nem avaliação de novos títulos lacrados; Hugin segue H2 e Munin M3, sem previsões reais.

O coletor permanece em execução, com intervalo de dez minutos. Naquele checkpoint, a próxima verificação estava prevista para 16:03 BRT. O relatório será atualizado antes do encerramento explícito do dono (`PARE`).

### 9.9 Continuidade da coleta até 16:53 BRT

Após o checkpoint de 15:53, os ciclos 32–37 concluíram às 16:03, 16:13, 16:23, 16:33, 16:43 e 16:53, com 4, 3, 6, 5, 7 e 7 itens novos, respectivamente (32 no trecho). Todos usaram `--dry-run`; os 24 feeds responderam sem falhas e cada ciclo retornou `collect_exit=0` e `budget_exit=0`. O acumulado da retomada passou de 534 para 566 itens novos e o corpus temporário chegou a 1.471 únicos. No ciclo 34, `sent_news=1` foi somente contador de simulação; a API permaneceu `dry_run=true`.

Freio às 16:53: corpus temporário com volume 24 h 838, aceitos 18, HOT entre aceitos 0,056; normal/economia 468 linhas/dia e 612 a 5×; crítico 432/432. Corpus oficial local: volume 24 h 465, aceitos 27, HOT entre aceitos 0,074; normal 486/702, economia 482/682 e crítico 432/432. Ambos dentro dos limites seguros. Sem alteração de regra de Hugin nem avaliação de novos títulos lacrados; Hugin segue H2 e Munin M3, sem previsões reais.

Naquele checkpoint, a próxima verificação estava prevista para 17:03 BRT; a coleta continuou pelos ciclos 38–41 e terminou após o pedido explícito do dono às 17:42 BRT.

### 9.10 Trecho final e parada solicitada pelo dono

Após o checkpoint de 16:53, os ciclos 38–41 concluíram às 17:03, 17:13, 17:23 e 17:33, com 7, 4, 14 e 4 itens novos (29 no trecho). Todos usaram `--dry-run`; os 24 feeds responderam sem falhas e cada ciclo retornou `collect_exit=0` e `budget_exit=0`. O acumulado da retomada passou de 566 para 595 itens novos, totalizando 1.500 itens únicos no corpus temporário. Nos ciclos 40 e 41, `sent_news=1` foi apenas contador de simulação, com `dry_run=true`; nenhum envio foi feito.

Freio final após a parada: corpus temporário com volume 24 h 847, aceitos 19, HOT entre aceitos 0,053; normal/economia 470 linhas/dia e 622 a 5×; crítico 432/432. Corpus oficial local: volume 24 h 465, aceitos 27, HOT entre aceitos 0,074; normal 486/702, economia 482/682 e crítico 432/432. Ambos dentro dos limites seguros. A coleta foi interrompida por `PARE` às 17:42 BRT, antes do próximo ciclo previsto para 17:43.

Revisão do resultado: Hugin permanece H2 porque o candidato BUFFER 0,45 não passou pelo critério combinado de promoção e não foi aplicado; nenhum título da avaliação lacrada nova foi aberto. Munin permanece M3, com seis cenários sintéticos e nenhuma previsão real avaliada. Nenhuma regra, métrica ou nível foi promovido durante os ciclos contínuos. Os commits de checkpoint ficaram locais na branch `hen`; não houve push.

## 10. Conferência final (estado da primeira sessão; revisar antes de encerrar a retomada)

- [x] Suíte Python exigida: 55 testes passaram.
- [x] `corvo_budget_check.py` passou antes de cada commit; projeções verdes nos três níveis de pressão.
- [x] `sh scripts/gitcrypt_check.sh`: nenhum segredo em texto puro no índice.
- [x] Corpus, rótulos locais e SQLite não foram adicionados ao Git.
- [x] Branch `hen`; commits locais sem push; trava liberada após os commits técnicos.
- [x] Nenhum arquivo de `apps/worker`, `database`, `packages/shared` ou `.github/workflows` ficou alterado.
- [x] Incidente de comando registrado: `npm run typecheck` acionou `wrangler types`; `npm run build` acionou `wrangler deploy --dry-run`. Ambos saíram com código 0; o segundo encerrou em dry-run sem deploy. Esses scripts não serão executados novamente nesta tarefa.


### 9.11 Retomada curta e parada solicitada pelo dono (18:10 BRT)

Após a retomada autorizada, a coleta local continuou em `--dry-run` nos ciclos 42–44, concluídos às 17:45:32, 17:55:39 e 18:05:45 BRT. Entraram 6, 6 e 2 itens novos (14 no trecho); o corpus temporário passou de 1.500 para 1.514 itens únicos, e o acumulado desde o começo da sessão chegou a 609 itens novos. O ciclo 43 registrou `fed-press` com HTTP 404; os outros 23 feeds responderam. Os ciclos 42 e 44 tiveram 24 feeds saudáveis. `collect_exit=0` e `budget_exit=0` nos três ciclos. No ciclo 44, `sent_news=1` foi contador simulado: `dry_run=true`, sem POST ou envio à API.

Freio final, conferido após a parada às 18:10 BRT: corpus temporário com volume 24 h 845, aceitos 19 e HOT entre aceitos 0,053; normal/economia 470 linhas/dia e 622 a 5×; crítico 432/432. Corpus oficial local: volume 24 h 465, aceitos 27 e HOT entre aceitos 0,074; normal 486/702, economia 482/682 e crítico 432/432. Ambos verdes. O processo de coleta foi encerrado após o ciclo 44; nenhum processo do coletor permaneceu ativo.

Nenhuma regra foi ajustada nesta retomada e nenhum conjunto lacrado foi aberto. Portanto Hugin segue H2 e Munin M3, sem previsão real avaliada. A rodada de avaliação fresca ficou pendente; não se afirma melhora de qualidade a partir do volume raspado. O dono pediu `PARE` e revisão às 18:10 BRT. Os artefatos temporários e os commits permanecem locais, sem push.

Pergunta para o dono: ao retomar em outra sessão, autoriza completar a avaliação lacrada fresca a partir de dados posteriores ao lacre anterior?


### 9.12 Retomada, avaliação de ajuste e parada solicitada pelo dono (18:31 BRT)

Na nova retomada, os ciclos 45 e 46 terminaram às 18:13:08 e 18:23:14 BRT: 6 e 8 itens novos, 24 feeds sem falhas, `collect_exit=0`, `budget_exit=0` e `dry_run=true` em ambos. O corpus temporário chegou a 1.528 itens únicos (+14 desde 18:10). A coleta foi interrompida durante a espera anterior ao ciclo 47, após o pedido `PARE` às 18:31 BRT; a sessão terminou e a checagem não encontrou processo residual.

O freio final do corpus temporário marcou volume 24 h 845, aceitos 19 e HOT entre aceitos 0,053; projeções normal/economia 470 linhas/dia e 622 a 5×; crítico 432/432. O corpus oficial local permaneceu em volume 24 h 465, aceitos 27, HOT entre aceitos 0,074; normal 486/702, economia 482/682 e crítico 432/432. Ambos dentro dos limites seguros.

Para a amostra fresca posterior ao lacre anterior, foram excluídas as 258 URLs já lacradas; o pool tinha 365 URLs de 17 fontes no último recálculo. Rotulei somente o lado `fit` (248 itens: 14 keep, 6 marginal, 228 drop; pesos 1 por ser o censo disponível). Com o corte BUFFER normal 0,50, recall keep ponderado 0,143, keep entre gravadas 0,667 e drop gravado 0. Uma hipótese única, ainda somente em memória e escolhida pelo fit, acrescentou o termo específico `Aramco` ao tema energia: no fit, recall 0,214, keep entre gravadas 0,750 e drop gravado 0. São apenas 14 keep; o resultado é instável e a alteração não foi aplicada ao código.

O `eval` fresco permaneceu sem rótulos e seus títulos não foram consultados. Não houve prova lacrada da hipótese, promoção nem mudança de nível: Hugin H2; Munin M3, sem previsões reais avaliadas. Resultado desta sessão é evidência preliminar de ajuste, não melhora confirmada. Próxima etapa: ampliar o corpus fresco, terminar a rotulagem `fit`, congelar a hipótese antes de abrir/rotular `eval` e fazer a prova lacrada uma única vez. Pergunta ao dono: para a próxima retomada, mantém autorização para completar essa prova depois de mais dados?

### 9.13 Rodada nota8 ? checkpoint 19:30?20:00 BRT (coleta externa ainda ativa)

Esta rodada come?ou na `hen` em `b2c1508`. O preflight retornou **PRONTO** (55 testes); o freio inicial marcou 1.260 itens ?nicos, volume 24 h de 528, 458 linhas/dia e 562 a 5?; cr?tico 432/432, tudo verde. ?s 19:54 BRT, o corpus local tinha 1.265 itens ?nicos e 527 itens nas ?ltimas 24 h; o freio continuou em 458/562 (normal e economia) e 432/432 (cr?tico), verde. O processo externo de coleta permaneceu ativo em `--dry-run`: ciclos 1?3 entre 19:30 e 19:50, 24 feeds por ciclo; um HTTP 404 de `fed-press` no ciclo 2 foi isolado, sem interromper a coleta. O arquivo local de pre?os tinha 5.215 linhas para BNB, BTC, ETH, SOL, XRP e cinco pares USD/FX. N?o reiniciei nem encerrei esse processo.

O avaliador Hugin foi executado uma vez e s? seus agregados foram consultados; nenhum exemplo `eval` foi aberto para escolher regra. O port?o n?o mudou nesta rodada, portanto os agregados antes/depois s?o iguais:

| M?trica ponderada | Fit (225; 46 keep) | Eval lacrado existente (75; 15 keep) | Antes ? depois |
|---|---:|---:|---|
| Precis?o HOT | 1,000 | 1,000 | igual |
| Recall keep | 0,540 | 0,800 | igual |
| Keep descartado | 0,460 | 0,200 | igual |
| Drop gravado | 0,049 | 0,125 | igual |
| Keep entre gravadas | 0,607 | 0,583 | igual |
| HOT entre aceitos | 0,082 | 0,083 | igual |
| Linhas/dia (normal; 5?) | 458; 562 | ? | or?amento verde antes/depois |

N?o foi poss?vel gerar um novo lacre com 40+ casos `keep`: o conjunto existente tem 15 `keep` no `eval`, e n?o havia r?tulos humanos novos. N?o abri os itens lacrados. Assim Hugin permanece **H2**; H3 n?o ? alegado. A m?trica de eventos ? uma adjudica??o manual de desafio no `fit`, separada do port?o Hugin: em 30 pares entre fontes, 4 merges corretos, 0 falsos, 8 pares positivos perdidos e 18 negativos separados (precis?o 1,00, recall 0,33). ? uma amostra pequena e selecionada, n?o estimativa populacional.

Blocos entregues nesta rodada:

| Bloco | Prova | Commit |
|---|---|---|
| Eventos Munin: Jaccard ?0,30, mesmo t?pico, at? 48 h, complete-link | teste novo; pares `fit` 0/30 fus?es erradas, recall baixo explicitado | `a5afa14` |
| Perguntas fechadas e resolu??o local | teste novo; regra usa 30 retornos anteriores do mesmo horizonte e fecha por pre?o local; sint?tico s? nos testes | `08c6a40` |
| Walk-forward, absten??o, registro `previsoes.jsonl` e painel | teste novo; corpus/pre?os reais locais: 58 eventos, 106 perguntas, **0 previs?es** por `n<30`, 106 abstencoes; resolu??o: 18 resolvidas, 2 sem fechamento futuro, 86 sem instrumento; Brier N/A | `1112aa9` |
| T9 robustez da coleta | teste novo; payload `None` de uma fonte foi registrado como falha, enquanto fonte saud?vel completou ciclo e foi marcada uma vez; 72 testes da bateria passaram no commit T9; a su?te final ap?s o complemento teve 74 aprovados | `ab2a42c` |

As 18 resolu??es usaram pre?os locais existentes, n?o sint?ticos; nenhuma era resultado de previs?o. Os 86 casos sem instrumento foram `OURO` (32), `PETROLEO` (32), `SP500` (13) e `USD` sem escolha de par (9); permanecem aguardando fonte/mapeamento. Os dois casos adicionais BTC/ETH aguardam pre?o posterior ao horizonte. Munin permanece **M3**; M4 n?o ? alegado porque o painel n?o produziu previs?es resolvidas nem uma avalia??o independente de calibra??o. A taxa-base exige 30 eventos resolvidos anteriores por chave (incluindo dire??o); a divis?o walk-forward n?o usa resultado futuro; corre??o Benjamini?Hochberg `q=0,05` e regra de 100 resolvidas/ECE ?0,05 continuam como protocolo, n?o como resultado emp?rico.

T0 (leitura de banco remoto) e T10 (verifica??o de novas fontes) n?o foram executados; nenhuma fonte foi adicionada. A coleta e o pre?o local vieram do processo externo; n?o houve POST, deploy ou acesso a `.env`. `previsoes.jsonl` foi escrito localmente e n?o entrou no Git. O teste sint?tico ficou restrito aos testes e cada linha de fixture est? marcada `synthetic`.

**Perguntas para o dono (uma por linha):**
- Qual par USD/FX deve representar as hip?teses de `USD` (por exemplo, USDBRL ou USDEUR), e qual ser? a refer?ncia registrada em `SOURCES.md`?
- O limite de agrupamento (Jaccard 0,30 / 48 h) ? aceit?vel como ponto inicial, dado recall de 0,33 no desafio manual?
- Pode fornecer/anotar um novo conjunto lacrado com pelo menos 40 `keep`; o `eval` atual tem apenas 15?
- A fonte/termos dos pre?os locais deve ser formalmente registrada em `SOURCES.md` antes de qualquer alega??o M4?

**Pr?ximos passos:** manter o processo externo de coleta intocado; quando houver r?tulos novos, congelar uma amostra sem URLs vistas e executar o `eval` agregado uma vez; acumular 30+ eventos independentes resolvidos por chave antes de emitir previs?es; confirmar proxy USD e proveni?ncia de pre?os antes de resolver hip?teses n?o cobertas.

### 9.14 Fechamento dos crit?rios preditivos expl?citos (20:00 BRT)

A tabela `impact.py` foi exercitada com os 58 eventos aprovados agrupados: 53 eventos t?m uma fonte, 4 t?m duas e 1 tem tr?s. O cat?logo local marca explicitamente 5 fontes oficiais; 4 eventos foram confirmados por fonte oficial, 5 por cobertura de m?ltiplas fontes e 49 ficaram como fonte ?nica. N?o mudei os candidatos porque os dados ainda n?o permitem validar dire??o/ativo: o tema `conflito_chave` gerou 28 eventos e suas hip?teses PETROLEO/OURO n?o t?m s?rie local; os candidatos SP500 tamb?m n?o t?m pre?o, e `USD` n?o determina qual dos cinco pares FX usar. S?o hip?teses audit?veis, n?o efeitos provados. `catastrofe ? SP500 volatile` e `infraestrutura ? PETROLEO volatile` parecem amplos demais sem evento sist?mico/choque de oferta; ficam como perguntas para aprova??o e futura contagem, sem peso aprendido.

Ajustei a regra de `questions.py`/`resolve.py` para declarar anula??o e horizonte; o registro inclui IDs de fonte, contagem, n?vel de confirma??o e as regras usadas. Cripto ? cont?nuo; para FX com instrumento exato, uma janela que intersecta o fechamento de fim de semana (aproxima??o UTC de sexta 22:00 a domingo 22:00) ? `cancelled_market_closed`; calend?rios desconhecidos n?o s?o adivinhados e sem s?rie o estado continua `awaiting_price`. Testes novos cobrem cancelamento FX e n?o cancelamento por calend?rio para cripto. Feriados e hor?rio de ver?o n?o est?o modelados; o intervalo ? uma aproxima??o expl?cita a confirmar com o dono.

O painel de prova agora imprime Brier, Brier da taxa-base ponto-no-tempo, skill, ECE e, por chave aberta, quantas resolu??es independentes faltam para `n=30`. O arquivo local cont?m tr?s snapshots determin?sticos (318 linhas no total); a execu??o mais recente tem 106 entradas e ? identificada por `run_id`, sem gravar corpus ou dados sint?ticos. No snapshot local atual n?o h? nenhuma previs?o, logo as quatro m?tricas s?o **N/A**, n?o zero. H? 17 chaves abertas: BTC/ETH cripto t?m 6 resultados resolvidos anteriores e faltam 24; BTC volatilidade de banco central tem 2 e faltam 28; todas as demais t?m 0 e faltam 30. A taxa-base ? o ?nico previsor, ent?o, quando houver previs?es, a r?gua de taxa-base ? a mesma probabilidade e o skill contra essa r?gua ser? zero por defini??o; qualquer ganho exige outro m?todo futuro e prova temporal separada.

A coleta externa continuou sem rein?cio: o ciclo 4 concluiu ?s 20:00 BRT, 24 feeds sem falhas, 2 itens novos; a renova??o local acrescentou 5 linhas de pre?o (5.220 totais). O painel foi repetido ap?s as altera??es e manteve 58 eventos, 106 perguntas, 0 previs?es e 106 abstencoes, sem mudan?a de status de resolu??o. O processo continua ativo em `--dry-run`. Nenhuma nova avalia??o lacrada foi consultada.

### 9.15 Verifica??o completa do engine (20:09 BRT)

`py -m pytest -q` terminou com **1.098 passed, 6 xfailed, 6 failed** em 150,03 s. As seis falhas s?o os casos parametrizados de formas num?ricas de loopback em `tests/test_failure_injection.py`; `socket.getaddrinfo` lan?ou `socket.gaierror` em `corvo_engine/safe_http.py` antes da exce??o `UnsafeURLError` esperada. Esses arquivos est?o fora do escopo permitido e n?o foram alterados; n?o atribuo as falhas a esta rodada nem as escondo. A bateria direcionada ao CORVO continuou verde: **74 passed**. A su?te completa tamb?m emitiu avisos de conformidade pendente para 279 fontes ativas; ficam registrados para an?lise do propriet?rio dos coletores.

O freio p?s-commit de `c98c52d` ficou verde: 1.267 itens ?nicos, 529 nas ?ltimas 24 h, 458 linhas/dia (562 a 5?) em normal/economia e 432/432 em cr?tico. Branch `hen`, ?rvore limpa, trava livre. O PID 13596 continua ativo; n?o encerrei a coleta solicitada por tr?s horas.

Pergunta adicional ao dono: as seis falhas de `safe_http.py` devem ser encaminhadas ao agente Codex/red-team respons?vel por esse m?dulo?

### 9.16 Segunda prova P1 no conjunto fit (20:10 BRT)

Com os mesmos 30 pares manualmente rotulados no `fit` (sem tocar no `eval`), alterei s? o limiar lexical de 0,30 para 0,25. O desafio passou de TP=4, FP=0, FN=8, TN=18 para TP=5, FP=0, FN=7, TN=18: fus?es falsas 0/30 (0%) e recall 0,333?0,417. A amostra ? um desafio selecionado, n?o uma estimativa populacional; o recall continua baixo e a regra ainda precisa de mais pares.

No corpus local aprovado, o agrupamento passou de 58 para 56 eventos; cobertura multifuente subiu de 5 para 7 eventos; distribui??o final de fontes por evento: 49 eventos com 1 fonte, 6 com 2 e 1 com 3. Confirma??o final: 4 eventos com fonte oficial, 7 multifuente e 45 com fonte ?nica. O painel real atualizado ficou em 56 eventos, 102 perguntas, zero previs?es, 102 abstencoes por `n<30`; 18 pre?os locais resolveram perguntas sem previs?o, 2 aguardam pre?o futuro e 82 aguardam instrumento. Brier/taxa-base/skill/ECE seguem N/A. O registro local tem 420 linhas em quatro `run_id`s; a execu??o atual tem 102 linhas e repeti??o idempotente n?o criou c?pia.

O ciclo externo 5 terminou ?s 20:10 BRT: 24 feeds saud?veis, 11 itens recebidos e nenhuma altera??o de pre?o; corpus com 1.278 itens ?nicos. Freio: volume 24 h 514, 458 linhas/dia (562 a 5?), cr?tico 432/432, verde. Hugin permaneceu H2; a altera??o foi no agrupador de eventos Munin e n?o na relev?ncia Hugin. Nenhum lacre foi aberto para decidir o limiar.


A mudan?a de limiar e seu teste de fronteira foram commitados em `715751a`; a bateria direcionada final teve 75 aprovados, e o freio permaneceu verde antes e depois do commit (1.278 itens, 458/562 linhas e 432/432 cr?tico).
Pergunta ao dono: aceita manter 0,25 como limiar provis?rio enquanto se coletam mais pares fit independentes, dado recall de 0,417 e 0/30 fus?es falsas no desafio atual?

### 9.17 Terceira prova P1 no fit e corte rejeitado (20:10 BRT)

Mantive os mesmos 30 pares do `fit` e testei 0,235. Em rela??o a 0,25, TP subiu 5?7, FP ficou 0, FN caiu 7?5, TN ficou 18; recall 0,417?0,583 e fus?es falsas 0/30. O candidato 0,23 capturaria os mesmos 7 positivos, mas faria 1 fus?o falsa em 30 (3,3%); foi rejeitado e n?o entrou no c?digo. O corte padr?o fica 0,235, com limite inferior ainda incerto pela amostra pequena.

No corpus aprovado real, 0,25?0,235 reduziu grupos de 56 para 55; cobertura multifuente ficou em 7 eventos; distribui??o final: 48 com uma fonte, 5 com duas e 2 com tr?s; confirma??o: 4 oficiais, 7 multifuente, 44 de fonte ?nica. O painel final tem 55 eventos, 100 perguntas, 0 previs?es, 100 abstencoes, 18 resolu??es de pre?o local sem previs?o, 2 aguardando pre?o futuro e 80 sem instrumento; Brier, base, skill e ECE N/A. Registro local: 520 linhas em cinco snapshots idempotentes; execu??o atual com 100 linhas (`run_id=run_71e39f445d40751646a5`).

Essa itera??o usa somente `fit` para ajustar a identidade de eventos; n?o abriu o lacre nem mudou o port?o Hugin. Hugin H2, Munin M3. O novo conjunto de avalia??o Hugin segue indispon?vel: eval existente tem 15 `keep`, abaixo dos 40 pedidos.

### 9.18 T9: ciclo resiliente a falhas distintas por fonte (20:10 BRT)

Ampliei o teste de integra??o do `run_cycle` com oito fontes simuladas: XML quebrado, corpo vazio, HTML inesperado, corpo excessivo, timeout, HTTP 403, HTTP 503 e erro de redirecionamento. Cada falha foi registrada pelo ID da fonte; a fonte saud?vel completou envio local `dry-run` e foi marcada uma vez; nenhum acesso de rede ocorreu. A su?te direcionada final ficou em **76 passed**; matriz T9 commit `310eb9b`. O c?digo de agrupamento 0,235 est? no commit `09b4c36`; o freio antes deste commit T9 permaneceu verde (1.278 itens, 458/562 normal/economia, 432/432 cr?tico).


### 9.19 Checagem de lacre fresco e honestidade Munin (20:23 BRT)

Sem abrir exemplos do lacre existente, comparei apenas URLs ja rotuladas com o corpus local para estimar se havia pool fresco suficiente. Restaram 989 URLs ineditas (988 unicas validas no snapshot); o portao atual aceita 10. A divisao estavel 70/30 coloca 304 itens frescos no `eval`, dos quais 4 estao no estrato atualmente aceito. Isso **nao** diz quantos itens rejeitados sao `keep`: eles nao foram rotulados nem pontuados. Nao ha base para afirmar um lacre de 40+ `keep`; nenhum rotulo foi inventado e nenhuma regra Hugin foi escolhida com esse pool. O conjunto avaliado disponivel continua com 15 `keep`, abaixo da exigencia. Hugin segue H2.

Rodei novamente `corvo_munin_eval.py --synthetic`; os seis cenarios foram explicitamente sinteticos, sem resultados reais: calibrado (`n=3000`, skill +0.353, ECE 0.014, confiavel); exagerado (`n=3000`, skill +0.089, ECE 0.211, calibrando); taxa-base (`n=3000`, skill 0); conservador (`n=3000`, skill +0.262, ECE 0.132, calibrando); pouca amostra (`n=12`, estado experimental e atualizacao HOLD); vazamento temporal foi bloqueado antes da pontuacao. Isso testa os freios da bancada, nao mede a qualidade de previsoes reais. Munin segue M3, sem previsao real avaliada.

O freio do corpus local antes deste registro ficou verde: 1288 URLs unicas, 522 itens em 24 h, 458 linhas/dia (562 a 5x) e 432/432 em pressao critica. Nenhum arquivo de dados foi alterado; o snapshot temporario ficou fora do repositorio. Nenhuma regra foi promovida neste checkpoint.


### 9.20 Ciclo 6 e repeticao do painel local (20:20 BRT)

O processo externo nao foi reiniciado: o ciclo 6 terminou em 20:20:08, com 24 feeds sem falhas e 10 itens novos; a coleta de precos terminou em 20:20:20 sem linhas novas (5.220 no total). O freio apos o ciclo marcou 1288 URLs unicas, 522 itens em 24 h, 458 linhas/dia (562 a 5x) e 432/432 em pressao critica, dentro dos limites.

Reexecutei `corvo_munin_backtest.py --dry-run` com os arquivos locais. Resultado: 55 eventos, 100 perguntas, 0 previsoes e 100 abstencoes; 18 perguntas resolvidas por precos locais sem previsoes, 2 aguardam preco futuro e 80 aguardam instrumento. Brier, Brier da taxa-base, skill e ECE seguem N/A porque nao ha previsoes resolvidas. A chave de registro foi idempotente (`run_id` existente), sem duplicar entradas. O processo de coleta segue ativo, PID 13596; nenhuma afirmacao de acerto foi feita.


### 9.21 Correcao do relogio temporal Munin (20:29 BRT)

A revisao do fluxo encontrou uma fonte de vazamento: o backtest usava `published_at` como hora da pergunta, embora as linhas locais tenham `cycle_at`, a hora em que o coletor conheceu a noticia. Alem disso, o agrupamento contava fontes que podiam ter chegado depois da primeira publicacao. As 1.290 linhas brutas atuais possuem `cycle_at`; nao usei exemplos do lacre Hugin.

Corrigi a disponibilidade do evento para o maior `cycle_at` entre as materias agrupadas (a primeira hora em que todas as fontes usadas sao conhecidas), ordenei o walk-forward por essa hora, gravei `observation_time_basis=cycle_at` e passei a omitir e contar eventos sem essa informacao, sem adivinhar pela publicacao. Testes novos cobrem a chegada tardia de uma fonte, reordenacao temporal e omissao de evento sem `cycle_at`.

A bateria Munin direcionada ficou em **22 passed**. No painel real local, os 55 eventos continuam produzindo 100 perguntas, 0 previsoes e 100 abstencoes por `n<30`; nenhum evento foi omitido por falta de `cycle_at`. Resolucoes locais sem previsao cairam de 18 para 8, enquanto `awaiting_future_price` subiu de 2 para 12 e `awaiting_price` permaneceu 80. Esta mudanca reduz resultados historicos aparentes porque inicia o horizonte quando a informacao realmente estava disponivel; nao e ganho de precisao. Brier, skill e ECE seguem N/A, Munin M3 sem avaliacao preditiva real.

Freio antes deste commit: 1288 URLs unicas, volume 24 h 522, 458 linhas/dia (562 a 5x), pressao critica 432/432; dentro dos limites. A coleta externa permanece ativa em `--dry-run`.


### 9.22 Janelas independentes no baseline (20:30 BRT)

A regra M6 pedia 30 eventos independentes, mas o replay ainda podia contar duas resolucoes da mesma chave cujas janelas de preco se sobrepunham. Acrescentei um filtro conservador por `(tema, ativo, direcao, horizonte)`: uma resolucao so entra no baseline se a janela dela comecar no fechamento da ultima janela aceita. Resultados sobrepostos continuam registrados como resolvidos, mas nao aumentam `n`.

Teste sintetico marcado `synthetic` usa eventos a cada 3 horas com horizonte de 6 horas: janelas sobrepostas nao levam uma chave de `n=1` a `n=2`; o replay informa a exclusao. A bateria direcionada Munin ficou em **23 passed**. No corpus local, 6 resultados sobrepostos foram retirados das contagens de amostra; BTC e ETH cripto ficam com 1 resultado independente cada e precisam de mais 29 para `n=30` (antes, o painel contava 4). As resolucoes de preco permanecem 8 `resolved`, 12 `awaiting_future_price` e 80 `awaiting_price`; previsoes continuam 0, abstencoes 100 e Brier/ECE N/A.

Atualizei o protocolo M6 e a documentacao preditiva para definir independencia como janelas nao sobrepostas por chave; atualizei tambem a nota 8 para separar ID ancorado na publicacao da hora local de disponibilidade (`cycle_at`). Esta e uma regra de amostragem mais cautelosa, nao uma melhora de acerto. Munin segue M3, Hugin H2.

O ciclo 7 terminou as 20:30:07 com 24 feeds sem falhas e 1 item novo; precos sem novas linhas (5.220). Freio antes do commit: 1.289 URLs unicas, volume 24 h 520, 458 linhas/dia (562 a 5x), pressao critica 432/432; verde. A coleta permanece ativa.


### 9.23 Integridade do arquivo local de precos (20:33 BRT)

Auditei `precos.csv` local sem alterar linhas: 5.220 registros, 5.220 chaves ativo/horario unicas, zero linhas invalidas, fechamento nao positivo, duplicata, duplicata conflitante ou fechamento futuro. As series cripto chegam ate 2026-11-08 23:00 UTC; as cinco series FX diarias, ate 2026-11-06 16:00 UTC, coerente com a janela de fim de semana desta coleta. Nenhum preco foi sintetizado.

A checagem valida apenas a estrutura temporal local; nao comprova licenca/proveniencia da fonte nem cria previsoes resolvidas. Os resultados do painel permanecem os do ciclo 7: 0 previsoes, 100 abstencoes, 8 resolucoes de preco sem forecast e metricas preditivas N/A. Hugin H2 e Munin M3.


### 9.24 Testes cruzados Munin e matriz de payloads T9 (20:36 BRT)

A bateria completa de testes Munin ficou em **53 passed**. Ampliei o teste de robustez da coleta com cinco retornos invalidos do adaptador (`None`, tupla, objeto, lista com registro invalido e texto); em cada caso, a fonte foi isolada e a fonte saudavel concluiu o mesmo ciclo local. A bateria T9 junto dos testes de `collect` ficou em **10 passed**, sem rede real. Rodei tambem 31 casos da matriz HTTP de caos em servidor loopback local (6 foram omitidos), incluindo hang/gotejamento limitados pelo deadline; 31 passaram em 7,74 s.

A medicao Hugin consultou somente `fit`: n=225/keep=46, precisao HOT 1.000, recall keep 0.540 (46% dos keep descartados), drop gravado 0.049, keep entre gravadas 0.607 e HOT entre aceitos 0.082. Nao reabri `eval` nem alterei o gate; Hugin permanece H2.

O freio permaneceu verde antes deste bloco (1.289 URLs unicas, volume 24 h 520; 458 linhas/dia, 562 a 5x, 432/432 critico). Nao houve mudanca no portao Hugin nem no placar de previsoes: Hugin H2, Munin M3, sem forecast real resolvido.


### 9.25 T0: auditoria GET do feed de producao (20:40 BRT)

Fiz somente GET em `/api/corvo/feed`; nao houve POST nem outra escrita. A resposta gerada em 2026-11-08T23:40:46Z trouxe 31 noticias e um orcamento remoto de 232/300.000 linhas. As estatisticas do painel indicam 818 recebidas, 17 HOT, 14 BUFFER e 787 descartadas. Os 31 itens retornados coincidem com os 31 gravados reportados (`17 HOT + 14 BUFFER`); os 818 incluem descartes e nao sao o total armazenado. Os 31 itens retornados tinham `ingested_at=2026-11-08T03:13:32Z`, cerca de 20,5 horas antes da leitura, embora o processo local de raspagem siga ativo em `--dry-run`.

Classifiquei manualmente os 31 titulos, ignorando os campos `verdict`, `reason` e `relevance` do payload: **22 keep, 8 marginal, 1 drop**; `keep=71,0%`, abaixo da meta T0 de 85%. A resposta nao inclui corpo ou resumo, entao os rotulos sao de agente baseados apenas em manchete; as notas marginais incluem comentario sem mudanca de politica, cobertura repetida/ambigua sobre o escandalo bancario no Paraguai, analise de investimento sobre IA/S&P e retorica sem acao. O item drop foi a contribuicao de financiamento ao TPI/Japao, sem canal de mercado claro no titulo. Nao ajustei Hugin com esta amostra de producao e nao abri o lacre.

| Universo lido | Keep | Marginal | Drop | Keep % | Meta | Resultado |
|---|---:|---:|---:|---:|---:|---|
| 31 itens gravados devolvidos pelo GET (17 HOT + 14 BUFFER) | 22 | 8 | 1 | 71,0% | >=85% | abaixo; bucket atual, mas fotografia atrasada |

O T0 cobre os 31 itens gravados reportados no bucket; a fotografia esta cerca de 20,5 horas atrasada porque a coleta local roda em `--dry-run` e nao atualiza producao. Nenhum dado foi alterado. O freio local segue verde.


### 9.26 Ciclo 8 e painel local atualizado (20:40 BRT)

O ciclo 8 terminou as 20:40:08: 24 feeds sem falhas, 1 item novo e nenhum preco novo (5.220 candles). O freio local ficou verde: 1.290 URLs unicas, volume 24 h 515, 458 linhas/dia (562 a 5x) e 432/432 em pressao critica.

A repeticao `corvo_munin_backtest.py --dry-run` permaneceu em 55 eventos, 100 perguntas, 0 previsoes e 100 abstencoes. Ha 8 resolucoes locais sem forecast, 12 aguardando preco futuro e 80 aguardando instrumento; 6 janelas sobrepostas foram excluidas do baseline. BTC/ETH tem 1 resultado independente cada, faltando 29 para `n=30`. Brier, taxa-base, skill e ECE seguem N/A. A raspagem externa segue ativa em `--dry-run`, PID 13596.


### 9.27 Chave de amostra por direcao (20:44 BRT)

Alinhei `PREDITIVO.md`, o protocolo M6, a nota 8 e os docstrings de Munin com a chave real do baseline: `(tema, ativo, direcao da pergunta, horizonte)`. Uma resposta binaria a "subiu" nao pode ser misturada com a resposta a "caiu" ou "volatilidade"; cada direcao exige seus proprios 30 resultados independentes, em janelas nao sobrepostas. Esta foi uma correcao documental, sem alteracao de comportamento, registros ou contrato.


### 9.28 Texto da pergunta alinhado ao instante de observacao (20:50 BRT)

A pergunta fechada indicava que os 30 retornos de referencia eram anteriores a publicacao, mas o replay usa o instante em que todas as fontes do evento ficaram disponiveis (`cycle_at`). Troquei o texto para nomear esse instante e acrescentei assercoes ao teste de perguntas. Tambem acrescentei um caso sintetico que prova que chaves BTC `up` e `down` nao compartilham amostras. A regra de resolucao e os precos nao mudaram; nenhum placar real de previsao foi criado.


### 9.29 Ciclo 9 e painel Munin (20:50 BRT)

O ciclo 9 terminou com 24 feeds sem falhas, 3 itens novos e nenhum candle novo (5.220 linhas de preco). O corpus tem 1.293 URLs unicas; o freio segue verde em 460 linhas/dia, 572 a 5x e 432/432 sob pressao critica. O painel agora mostra 56 eventos, 100 perguntas, 0 previsoes, 100 abstencoes, 8 resolucoes sem forecast, 12 aguardando preco futuro e 80 aguardando instrumento. Continua sem Brier, skill ou ECE reais; seis janelas sobrepostas seguem fora da contagem e BTC/ETH ainda tem apenas um resultado independente cada.


### 9.30 Revalidação sintética de honestidade Munin (20:53 BRT)

Rodei de novo `corvo_munin_eval.py --synthetic`: calibrado n=3.000, skill +0,353 e ECE 0,014; exagerado +0,089 e ECE 0,211; taxa-base skill 0; conservador +0,262 e ECE 0,132; amostra n=12 classificada EXPERIMENTAL/HOLD; cenário com vazamento bloqueado antes da pontuação. Os seis cenários são sintéticos e não representam desempenho real.


### 9.31 Rechecagem Hugin somente no ajuste (20:56 BRT)

O conjunto `fit` continua em n=225/keep=46: precisão HOT 1,000, recall keep 0,540, keep descartado 0,460, drop gravado 0,049, keep entre gravadas 0,607 e HOT entre aceitos 0,082. As métricas repetem o placar anterior; não alterei regra e não reabri o conjunto lacrado. Hugin segue em H2.


### 9.32 Ciclo 10 e tentativa de lacre novo (21:00 BRT)

O ciclo terminou com 24 feeds consultados, 7 itens novos e cinco candles adicionados (5.225 linhas); `fed-press` retornou HTTP 404 e a falha ficou isolada. O corpus chegou a 1.300 URLs; o freio ficou verde em 460 linhas/dia, 572 a 5× e 432/432 na pressão crítica. O painel local tem 57 eventos, 100 perguntas, 0 previsões e 100 abstenções; as resoluções seguem 8/12/80, sem Brier, skill ou ECE reais.

Para tentar um lacre novo, copiei 993 URLs ainda sem rótulo para `%TEMP%` (excluí 300 URLs já rotuladas sem ler seus títulos ou separar por split), usei semente 20261109 e amostra de 993. Até 21:00, rotulei manualmente 300 por conteúdo, sem ler o veredito do gate; 21 dos 300 são keep no total. Ainda não rodei avaliação do novo lacre e não alterei regra. A bancada antiga permanece fechada para decisão.


### 9.33 Avaliação agregada do lacre fresco (21:10 BRT)

Rotulei as 993 URLs frescas por conteúdo, sem usar o veredito do gate: fit 686 (45 keeps), eval 307 (21 keeps). Rodei `corvo_gate_eval.py --split fit` e depois `--split eval` uma vez, só em agregados. Fit: precisão HOT n/d, recall keep 0,044, keep descartado 0,956, drop gravado 0,143, keep entre gravadas 0,286. Eval: precisão HOT n/d, recall keep 0,190, keep descartado 0,810, drop gravado 0, keep entre gravadas 0,800. Só houve 0 HOT aceitos; 21 keeps no eval não atingem 40. Não usei o resultado para escolher regra; Hugin fica H2 e não há afirmação de melhora.


### 9.34 Ciclo 11 e painel Munin (21:10 BRT)

O ciclo 11 teve 24 feeds sem falhas, 3 itens novos e nenhum preço novo (5.225 linhas). O corpus chegou a 1.303 URLs únicas. Freio verde: 458 linhas/dia, 562 a 5× e 432/432 na pressão crítica. O painel manteve 57 eventos, 100 perguntas, 0 previsões e 100 abstenções; 8 resoluções sem forecast, 12 aguardando preço futuro e 80 aguardando instrumento; nenhum placar real de previsão.


### 9.35 T6: ordem textual, cobertura e falsos positivos (21:20 BRT)

Hipótese definida no ajuste: selecionar a menção geográfica mais cedo no título, acrescentar lugares explicitamente citados que faltavam (Letônia/Riga, Iêmen/Sanaa/Taiz, Mar Negro, Golfo de Omã) e deixar de tratar o substantivo comum “turkey” como país. O texto de corpo continua como fallback só quando o título não contém correspondência.

Na mesma amostra de 53 aprovados fora do eval lacrado, a versão anterior localizava 37/53 títulos (69,8%); a nova localiza 44/53 (83,0%), ganho de 7 títulos. Nove títulos ainda não nomeiam uma localidade; não atribuí sede presumida a empresa ou ativo. Uma auditoria positiva curada e pré-especificada de 20 títulos de ajuste acertou 20/20 (100%); quatro testes negativos cobrem “Turkey” como alimento, Georgia/Jordan ambíguos e empresa sem sede. Isso não é uma estimativa independente de precisão: não há rótulo geográfico independente de toda a amostra. O critério de cobertura T6 (≥85%) permanece pendente.

O teste novo cobre menção mais cedo, os quatro lugares adicionados, preservação da prioridade do título sobre o corpo e ausência de inferência para nomes ambíguos/empresa. Os 108 testes CORVO e regressões selecionadas passaram. Nenhum item do eval lacrado foi aberto ou usado. Hugin segue H2. Freio antes do commit T6: corpus 1.310, 460 linhas/dia, 572 a 5×, 432/432 crítico; freio depois: mesmos valores, verde em normal, economia e crítico.


### 9.36 Ciclo 12 e conferência posterior ao commit T6 (21:20 BRT)

O ciclo 12 consultou 24 feeds sem falhas, trouxe 7 itens e não adicionou preços; o corpus tem 1.310 URLs e o arquivo de preços 5.225 linhas. Após o commit `1084877`, o freio foi repetido: 460 linhas/dia, 572 a 5×, aceitos 14/505 e 432/432 sob pressão crítica; todos os cenários verdes. A coleta do dono segue em `--dry-run`, PID 13596. Nenhum forecast real foi resolvido nesta atualização.


### 9.37 T6 revisão de acerto: local da ação supera o ator (21:25 BRT)

Ao revisar os 45 títulos que o geocodificador localizava, encontrei um risco na regra “primeira menção”: notícias como “Russia strikes Ukraine” podiam apontar o ator, não o local atingido. Ajustei a seleção para priorizar um local explicitamente ligado a uma ação por construções como “damage Ukraine”, “strike on Kyiv” e “ship in the Gulf of Oman”; sem esse contexto, continua vencendo a primeira menção. Acrescentei testes de regressão Rússia/Ucrânia e EUA/Irã.

No mesmo conjunto de ajuste atualizado (54 aprovados; sem URLs do eval), a versão do commit `1084877` localizava 38/54 (70,4%) e a versão do commit `34e59d7` localiza 45/54 (83,3%). Revisei os 45 resultados: 44 correspondem claramente ao local do acontecimento; um caso de deslocamento de tropas entre Síria, Iêmen e Arábia Saudita ficou ambíguo e foi contado como erro, portanto acerto conservador de 44/45 (97,8%). A seção 9.38 acrescenta uma região explicitamente citada e atualiza o placar. Nenhum item lacrado foi usado.


### 9.38 T6: região continental explicitamente nomeada (21:28 BRT)

O título “Binance users in some European countries...” nomeia uma região de mercado, mas não um país. Adicionei “Europa” com ponto regional aproximado, limitado às expressões “Europe”, “European countries/markets/Union”; não inferi a sede da Binance. Um teste assegura que “European Investment Bank” como nome de instituição não gera localização.

Na mesma amostra dos 54 aprovados do ajuste: 38/54 títulos localizáveis antes das mudanças T6 (70,4%), 46/54 agora (85,2%). A amostra de acerto cobre 46 retornos: 45 lugares claros e um caso de tropas ambíguo contado como erro, 45/46 (97,8%) de acerto conservador. A cobertura e o acerto atingem os limiares T6 neste conjunto de ajuste; isso não é prova lacrada. A bateria tem 23 exemplos positivos e cinco negativos; o conjunto eval não foi aberto. O commit `b28fcf3` passou o freio antes e depois: corpus 1.310, 460 linhas/dia, 572 a 5× e 432/432 na pressão crítica; tudo verde.


### 9.39 Ciclo 13, reprova sintética Munin e painel local (21:30 BRT)

`corvo_munin_eval.py --synthetic` repetiu seis cenários sem mudança: previsor calibrado skill +0,353/ECE 0,014; exagerado +0,089/0,211; taxa-base 0; conservador +0,262/0,132; n=12 continua EXPERIMENTAL/HOLD; vazamento continua bloqueado. Todos os números são sintéticos.

O ciclo 13 consultou 24 feeds sem falhas, trouxe 3 itens e nenhum preço novo. O corpus está em 1.313 URLs; o painel local mostra 59 eventos e 104 perguntas, 0 previsões e 104 abstenções; 8 resoluções locais sem forecast, 12 aguardando preço futuro e 84 aguardando instrumento. Brier, taxa-base comparável, skill e ECE de previsões reais continuam N/A; nenhum resultado de previsão foi pontuado. O freio pós-ciclo está verde em 462 linhas/dia, 582 a 5× e 432/432 na pressão crítica. Coleta do dono segue ativa, PID 13596.


### 9.40 T6 rechecagem com aprovados do ciclo 13 (21:30 BRT)

Recalculei a cobertura no conjunto de ajuste atual, excluindo todas as URLs do eval lacrado apenas pelo identificador. Agora são 55 aprovados: o geocodificador anterior localizava 39/55 (70,9%), o atual 47/55 (85,5%). A nova manchete “Rubio sees no Iran breakthrough...” foi localizada como Irã. A auditoria conservadora passa a 46/47 (97,9%): 46 claras e um caso de tropas ambíguo contado como erro. O resultado reforça que T6 continua acima dos dois limiares com a coleta; nenhuma linha do eval foi lida.


### 9.41 T5 censo de feeds nas últimas 24 h (21:30 BRT)

Agreguei apenas metadados (`source_id`, veredito e motivo) de registros com `cycle_at` entre 00:30:07Z de 8/11 e 00:30:07Z de 9/11. Excluí as URLs do eval lacrado por identificador, sem abrir títulos/corpos; são 1.008 URLs únicas de 23 feeds. O 24º feed (`usgs-sig`) teve zero registros no corpus neste intervalo. “Aceitos” = HOT + BUFFER; “stale” conta motivos com stale. Como a amostra não rotula falsos negativos, não alterei `reliability` ou `enabled`.

| Feed | Itens | Aceitos | DROP | `stale` |
|---|---:|---:|---:|---:|
| g1 | 210 | 0 | 210 | 0 |
| dw | 105 | 1 | 104 | 8 |
| straits-times | 76 | 10 | 66 | 1 |
| scmp | 75 | 3 | 72 | 1 |
| guardian-world | 54 | 3 | 51 | 2 |
| aljazeera | 49 | 10 | 39 | 0 |
| france24 | 40 | 3 | 37 | 0 |
| boe-news | 39 | 1 | 38 | 6 |
| japan-times | 39 | 2 | 37 | 4 |
| decrypt | 33 | 0 | 33 | 11 |
| allafrica | 32 | 0 | 32 | 1 |
| bbc-world | 29 | 5 | 24 | 1 |
| cointelegraph | 26 | 2 | 24 | 7 |
| times-of-israel | 26 | 2 | 24 | 0 |
| un-news | 26 | 0 | 26 | 2 |
| abc-au | 24 | 0 | 24 | 0 |
| cnbc | 24 | 6 | 18 | 0 |
| coindesk | 24 | 3 | 21 | 6 |
| theblock | 21 | 2 | 19 | 8 |
| fed-press | 18 | 0 | 18 | 4 |
| marketwatch | 16 | 1 | 15 | 0 |
| ecb-press | 11 | 1 | 10 | 5 |
| npr-world | 11 | 0 | 11 | 0 |
| usgs-sig | 0 | 0 | 0 | 0 |

G1 gerou o maior volume (210), sem nenhum item aprovado; isso é sinal para amostrar falsos negativos e analisar o feed geral, não evidência suficiente para desligá-lo, pois o recall de Hugin ainda é baixo. `decrypt` (11/33 stale), `theblock` (8/21), `cointelegraph` (7/26), `boe-news` (6/39) e `ecb-press` (5/11) merecem uma revisão temporal de frescor. Os contadores de duplicata são zero neste censo por URL: o corpus guarda URL única, então isso não mede near-duplicates.
