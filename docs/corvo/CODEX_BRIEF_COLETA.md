# CODEX — briefing do treino noturno: coleta e destino das notícias do CORVO

> Leia inteiro antes de tocar em qualquer arquivo. Este documento é a sua ordem de serviço. Tempo estimado de execução: uma noite (6 a 8 h). Você trabalha sozinho: ninguém vai responder dúvidas até de manhã. Se travar, registre no relatório e passe para a próxima tarefa; não improvise fora das regras.

## 1. Missão em uma frase
Fazer o robô **decidir bem, antes de salvar qualquer coisa, se cada notícia do mundo vai ou não para o banco**, e provar com números que ele decide melhor de manhã do que à noite.

### O que "treinar" significa aqui
**Não é treinar rede neural.** O portão é determinístico (regras, listas de palavras, limiares). Treinar = coletar um corpus real, rotular uma amostra, **medir** erros (o que entrou e não devia, o que ficou de fora e devia entrar) e **ajustar regras e limiares** até as métricas melhorarem em dados que o ajuste nunca viu. Sem LLM tomando a decisão em produção, sem probabilidade inventada.

## 2. Contexto do produto (2 minutos)
- **CORVO** é um motor preditivo do mundo todo: lê notícias e sinais, filtra, localiza e (mais adiante) prevê política, catástrofes, câmbio, ações, cripto e commodities. Nome: Hugin (pensamento, lê e filtra) e Munin (memória, guarda e calibra), os corvos de Odin.
- **Arquitetura:** o Oracle (servidor do dono, junto do repositório MNEME) é o cérebro e coleta; o Cloudflare só exibe o painel (Worker `corvo-api` + painel `corvo-web`, banco Turso). O Oracle empurra lotes para `POST /api/corvo/ingest`.
- **Por que o portão existe:** o banco tem limite. Turso grátis: 10 milhões de escritas por mês (teto de projeto: 300 mil por dia, `DAILY_WRITE_LIMIT`). Cada notícia gravada custa ~2 linhas. **Toda linha gravada precisa merecer.**
- Leia também: `docs/corvo/TRATAMENTO_NOTICIAS.md` (política de armazenamento), `docs/corvo/ARQUITETURA.md`, `docs/COLLECTION_PROTOCOL.md`, `docs/sources/SOURCES.md`, `AGENTS.md`.

## 3. Estado atual (medido em 2026-11-07, primeiro ciclo real)
| Medida | Valor |
|---|---|
| Feeds ativos no catálogo | 24 (5 oficiais, 19 imprensa/mercado/cripto) |
| Feeds com falha | 0 |
| Itens lidos no ciclo | 818 |
| Aprovados (HOT+BUFFER) | 34 (4%): 8 HOT e 26 BUFFER |
| Descartados | 636 `stale`, 145 `irrelevant`, 3 `near_duplicate` |
| Testes do portão, publicador e coleta | 18 passando |

Leituras importantes dessa medição (confirme ou refute com mais dados):
1. **78% dos itens saíram como `stale`** porque o primeiro ciclo lê o histórico dos feeds (itens de 1 a 3 dias). No regime normal, só chegam itens novos. A janela de 6 h é igual para todas as fontes: **isso provavelmente está errado para fontes oficiais** (um comunicado do Fed de ontem ainda importa). Medir e decidir.
2. Muito item de política geral cai em BUFFER com relevância ~0,63. É esperado; a pergunta é se o corte HOT (0,75) está bom.
3. A relevância é por palavras-chave em inglês e português. Perde notícias em outros idiomas e pode deixar passar lixo com palavra "boa" (ex.: "Fed" em contexto esportivo).
4. A geolocalização só reconhece países e hubs de uma tabela fixa; vários itens relevantes ficam sem ponto no mapa.

## 4. Regras invioláveis
**Git e coordenação** (de `AGENTS.md`, valem para você):
1. Trabalhe só na branch **`hen`**. Nunca na `main`, **nunca crie outras branches**. Antes: `git status`, `git branch --show-current`, `git pull`.
2. Há um quadro de agentes: `py scripts/agentbus.py register codex-noite --role "treino noturno do portao CORVO"`; `py scripts/agentbus.py who`; reserve o que vai editar com `claim`. Para commitar: `py scripts/agentbus.py lock acquire codex-noite --note "..."` e `lock release` ao terminar. `git add` **sempre por nome de arquivo** (nunca `-A` nem `.`). Rode `py scripts/agentbus.py check-staged codex-noite` antes de commitar.
3. Commits pequenos, mensagem em inglês no formato `tipo(escopo): resumo`, **no nome do dono do repositório** (use a configuração de git já existente; não troque `user.name` nem `user.email`). Termine a mensagem com a linha de coautoria que o seu ambiente usa. **Nunca `push --force`.** Nunca faça merge na `main`.
4. Antes de cada commit: `cd engine && py -m pytest tests/test_intake_gate.py tests/test_oracle_publisher.py tests/test_collect_runner.py -q`. Se algo vermelho for seu, conserte ou reverta o commit; não deixe vermelho.

**Segredos e produção** (nada disso é seu):
5. **Não rode** `wrangler deploy`, `wrangler secret`, `wrangler d1`, comandos do Turso, nem `gh secret`. **Não leia nem imprima** `deploy/oracle/.env`, `apps/worker/.dev.vars` nem tokens. **Não envie nada à API de produção** (`corvo-api`): todo o seu trabalho é local, com `--dry-run`.
6. Nunca commite o corpus coletado (`engine/data/corvo_corpus/` está no `.gitignore`: títulos e links de terceiros, só para uso local de medição).

**Fontes e coleta** (de `docs/COLLECTION_PROTOCOL.md`):
7. Só **RSS/Atom públicos e APIs oficiais**. Nada de raspar HTML, burlar login, captcha, paywall ou limite, nem fingir ser navegador. Mantenha o `User-Agent` identificado do projeto.
8. **Educação com os servidores:** no máximo 1 leitura a cada 5 min por feed (o `--interval` já impõe mínimo de 300 s) e 2 conexões simultâneas por servidor. Se um servidor devolver 403/429, **desative aquele feed** e anote no relatório; não insista.
9. Antes de **ligar qualquer fonte nova**, registre em `docs/sources/SOURCES.md`: API/feed oficial, termos de uso, limite, custo, autenticação, licença, retenção permitida e se pode exibir publicamente. Sem isso, a fonte entra com `"enabled": false`.
10. O CORVO guarda **título, link e resumo curto** com atribuição. **Nunca o corpo da matéria.** Nunca pessoas, rostos ou perfis individuais.

**Honestidade científica:**
11. **Separe os dados:** ajuste regras com 70% dos itens rotulados e avalie com os 30% restantes, **que você não pode olhar enquanto ajusta**. Reporte as duas medidas. Melhoria que só existe no conjunto de ajuste não conta.
12. Não esconda resultado ruim. Se uma ideia piorou, reverta e registre.
13. Não invente dados, rótulos "oficiais" nem manchetes. Alegação não é fato.
14. **Mudança de contrato** (formato do lote em `apps/worker/src/routes/corvo.ts`, tabelas em `database/migrations/`): **não faça**. Proponha no relatório. Você só altera `engine/corvo_engine/` (portão, coleta, geocodificador, publicador), seus testes e a documentação.

## 5. Mapa do código
| Arquivo | O que faz |
|---|---|
| `engine/corvo_engine/collect/catalog.json` | catálogo de feeds (id, url, região, tipo, `reliability` 0 a 1, `official`, `enabled`) |
| `engine/corvo_engine/collect/feeds.py` | lê um feed e devolve `NewsItem` (reusa o leitor endurecido de `collectors/news/rss.py`) |
| `engine/corvo_engine/collect/runner.py` | um ciclo: feeds, descarta já vistos, portão, publica. CLI `python -m corvo_engine.collect` |
| `engine/corvo_engine/intake/gate.py` | **o portão**: frescor, URL repetida, quase-duplicata, relevância por tema (`TOPICS`), cota por fonte, pressão (`GateConfig`) |
| `engine/corvo_engine/intake/geo.py` | geocodificador por tabela (`_PLACES`) |
| `engine/corvo_engine/intake/store.py` | memória de URLs já vistas (SQLite, 48 h) |
| `engine/corvo_engine/oracle/publisher.py` | monta o lote, classifica `kind` (`classify_kind`), agrega estatística, registra `last_decisions` |
| `engine/tests/test_intake_gate.py`, `test_oracle_publisher.py`, `test_collect_runner.py` | testes que protegem o comportamento atual |
| `apps/worker/src/routes/corvo.ts` | API (só leia: define o teto de escrita e o formato do lote) |

Vocabulário de decisão: **HOT** (grava já, relevância ≥ corte alto), **BUFFER** (grava, relevância média), **DROP** (não grava; vira só contador e hash da URL por 48 h). Motivos de DROP: `stale`, `duplicate_url`, `near_duplicate`, `irrelevant`, `below_threshold`, `source_quota`, `malformed`.

## 6. Comandos (PowerShell, na raiz do repositório)
```powershell
cd C:\projetos\Pulso\engine
# teste rápido de um ciclo, imprime até 15 itens aprovados
py -m corvo_engine.collect --once --dry-run
# registrar a decisão de CADA item (inclusive descartes) para análise
py -m corvo_engine.collect --once --dry-run --quiet --dump data\corvo_corpus\corpus.jsonl
# laço da noite: um ciclo a cada 10 min, sem enviar nada (use o limite de tempo que preferir)
$fim = (Get-Date).AddHours(6)
while ((Get-Date) -lt $fim) { py -m corvo_engine.collect --once --dry-run --quiet --dump data\corvo_corpus\corpus.jsonl; Start-Sleep -Seconds 600 }
```
Cada linha do `corpus.jsonl`: `cycle_at, source_id, url, title, published_at, verdict, reason, relevance, topics, region, pressure`. A memória de vistos do teste a seco fica em `corvo_seen_dry.sqlite` (não é a do envio real). Apague esse arquivo para recomeçar do zero.

## 7. O plano da noite
**Fase 0 (15 min), preparar.** Registre-se no quadro, rode os testes (devem passar), rode um ciclo e confira que os 24 feeds respondem. Anote versões e hora de início.

**Fase 1 (a noite toda, em segundo plano), coletar o corpus.** Inicie o laço da seção 6 em uma janela separada e **deixe rodando durante as outras fases**. Meta: pelo menos 30 ciclos e 3.000 itens únicos, de preferência cobrindo horários de Ásia, Europa e Américas. Registre por ciclo: feeds com falha, tempo, itens novos.

**Fase 2 (≈1 h), rotular.** Com o corpus parcial (≥ 1.500 itens), sorteie uma amostra **estratificada por fonte e por decisão atual** de 400 itens (mínimo 300) e rotule cada um em `engine/data/corvo_corpus/labels.jsonl` (`{"url": "...", "label": "keep|marginal|drop", "topic": "...", "kind": "fato|reportagem|rumor|opiniao|previsao", "region": "..."}`).
- **keep**: pode mexer em preço de ativo, câmbio, juros, política de países relevantes, conflito, desastre, regulação, hack ou ruptura de infraestrutura. Exemplos: decisão de juros; ataque a um oleoduto; terremoto M6+ em região industrial; exploit em protocolo grande de cripto; sanção a país exportador de energia.
- **marginal**: contexto político ou econômico com efeito indireto ou lento. Exemplos: pesquisa eleitoral; discurso de ministro sem medida concreta; balanço de empresa média.
- **drop**: sem efeito previsível em mercado, política ou segurança. Exemplos: celebridade, esporte, receita, horóscopo, publieditorial, clima ordinário, "como fazer".
- Rotule o item **pelo conteúdo**, nunca pela decisão que o portão tomou. Reserve **30% dos rótulos** (sorteados com semente fixa e registrada) como conjunto de avaliação lacrado.
- Registre as regras de rotulagem que usou e os casos ambíguos no relatório.

**Fase 3 (≈45 min), medir.** Crie `engine/benchmarks/corvo_gate_eval.py` que lê `corpus.jsonl` e `labels.jsonl` e imprime, **por conjunto (ajuste e avaliação)**:
- matriz `label × verdict` (keep/marginal/drop contra hot/buffer/drop);
- **precisão do HOT** (fração de HOT que é keep) e **recall do keep** (fração de keep que ficou HOT ou BUFFER);
- **taxa de keep descartado** (o pior erro) e **taxa de drop gravado** (o erro que gasta banco), cada uma com o motivo do descarte;
- projeção de **linhas por dia** = (aprovados por dia) × 2 + estatísticas, extrapolada do ritmo medido;
- cobertura do geocodificador (itens aprovados com `region`) e, na amostra, acerto do local;
- acerto do `kind` contra o rótulo.
Salve o resultado base em `docs/corvo/RELATORIO_NOITE_<data>.md` antes de mudar qualquer regra.

**Fase 4 (≈2 h), ajustar** na ordem da seção 8. Depois de cada mudança: testes verdes, rodar a avaliação e comparar com a linha de base **nos dois conjuntos**.

**Fase 5 (≈30 min), relatório e entrega.** Escreva o relatório (seção 10), faça os commits, `lock release`, deixe o laço de coleta terminar ou pare-o.

## 8. Tarefas (por prioridade) e critérios de aceite
| # | Tarefa | Aceite |
|---|---|---|
| T1 | **Janela de frescor por fonte.** Medir idade típica dos itens por feed (mediana, p90). Propor `max_age_s` por classe (oficial, agência, mercado, cripto), configurável no catálogo. | Menos keeps oficiais perdidos por `stale`; nenhuma explosão de linhas; teste novo cobrindo cada classe. |
| T2 | **Relevância.** Ampliar o léxico (inglês, português, espanhol) e criar **padrões negativos** (esporte, celebridade, estilo de vida, "opinião" de colunista, resultado de loteria). Manter determinístico. Reavaliar os pesos de `TOPICS` e o corte HOT. | Precisão do HOT ≥ 0,85 e recall do keep ≥ 0,90 **no conjunto lacrado**; taxa de drop gravado cai sem aumentar keep descartado. |
| T3 | **Quase-duplicata.** Normalizar títulos (acento, caixa, stopwords, aspas), testar limiares de Jaccard e comparação também com o resumo. Medir **fusões erradas** (dois fatos diferentes tratados como um): é pior que deixar passar uma cópia. | Fusões erradas ≤ 2% das comparações revisadas; cópias entre fontes reduzidas; testes com pares positivos e negativos. |
| T4 | **Cobertura do geocodificador.** Adicionar países, capitais e hubs financeiros que apareçam no corpus sem local, **evitando falso positivo** (ex.: "Georgia" estado x país, "Jordan" pessoa x país, "Turkey" ave, nomes de empresas). | Cobertura dos aprovados ≥ 85% e acerto na amostra ≥ 95%; testes de falso positivo. |
| T5 | **Classificação `kind`** (fato, reportagem, rumor, opinião, previsão). Medir contra seus rótulos e melhorar as regras. Regra de ouro: na dúvida, **reportagem**; só fonte oficial vira **fato**. | Acerto geral ≥ 0,80 e **nenhum rumor ou opinião classificado como fato**. |
| T6 | **Ficha de cada fonte.** Para cada feed: itens por dia, % `stale`, % duplicata, % aprovados, quem publica primeiro um fato (primeira fonte). Gerar tabela e recomendar `reliability` e quem desativar (ruidoso ou quebrado). Não altere `enabled` sem justificar no relatório. | Tabela no relatório; ajustes de `reliability` no catálogo com a evidência. |
| T7 | **Simulação de carga e orçamento.** Simule 24 h com o volume medido e com **5× o volume**, sob pressão normal, economia e crítico. Confirme a projeção de linhas/dia abaixo do teto e que a pressão aperta os cortes sem zerar o que é crítico. | Projeção ≤ 5 mil linhas/dia no ritmo medido e ≤ 25 mil com 5×; teste automatizado dessa simulação. |
| T8 | **Novas fontes candidatas** (só oficiais e RSS/Atom): SEC (comunicados), CFTC, US Treasury, BCE/BoJ/PBoC (se houver feed), GDACS, NOAA/NHC (ciclones), USGS (mais feeds), IMF/WTO/OPEC (comunicados), agências de Ásia, África e América Latina, em espanhol e português. **Verifique cada URL na hora** (não assuma que existe). | Cada fonte nova com linha em `SOURCES.md` e `enabled: false` se os termos não estiverem claros. Máximo de 15 fontes novas. |
| T9 | **Robustez.** Feed que muda de formato, devolve HTML, trava ou dá 5xx não pode derrubar o ciclo. Teste com respostas ruins (XML quebrado, resposta vazia, gigante, redirecionamento). | Testes novos; o ciclo sempre termina e registra a falha por fonte. |
| T10 | **Agrupamento por acontecimento** (proposta, **sem implementar o contrato**): estudar quantos itens aprovados são o mesmo fato em fontes diferentes e quanto o agrupamento economizaria de linhas. | Seção no relatório com números e um desenho de contrato para o dono aprovar. |

Não precisa terminar tudo. **Prioridade: T1, T2, T3, T7 (economia e qualidade do que vai ao banco)**, depois T4, T5, T6, T9. Se faltar tempo, termine bem o que começou.

## 9. A regra de decisão que você está calibrando
```
chegou um item
  ├─ URL já vista nas últimas 48 h?            → fora, sem contar (nem aparece em "recebidas")
  ├─ mal formado?                               → DROP malformed
  ├─ velho demais (janela da fonte)?            → DROP stale
  ├─ mesma URL (sem rastreio) ou título quase igual de outra fonte? → DROP duplicate_url / near_duplicate
  ├─ relevância < corte do buffer (depende da pressão)?             → DROP irrelevant / below_threshold
  ├─ cota por hora da fonte estourada?          → DROP source_quota
  ├─ relevância ≥ corte HOT?                    → HOT   (grava)
  └─ senão                                      → BUFFER (grava, entra em lote)
descarte = só contador por motivo + hash da URL (48 h). Nunca o texto.
```
Pressão (lida do Worker): **normal** (<60% do teto diário), **economia** (60 a 85%), **crítico** (>85%). Cortes padrão em `GateConfig`: HOT 0,75 / 0,85 / 0,95; BUFFER 0,30 / 0,50 / 0,95. Esses números são palpites a medir, não verdades.

**Princípio de custo dos erros:** deixar passar uma notícia importante (keep descartado) é **pior** que gravar uma irrelevante (drop gravado), mas cada linha custa quota. Calibre para que o primeiro seja raro e o segundo, pequeno, e mostre a troca nos números.

## 10. O que entregar de manhã
1. **`docs/corvo/RELATORIO_NOITE_<data>.md`** com: (a) resumo de 10 linhas para o dono; (b) tabela antes e depois das métricas, nos dois conjuntos; (c) mudanças feitas, uma por linha, com o commit; (d) fichas das fontes (T6); (e) o que **piorou** ou foi revertido; (f) casos que o portão ainda erra (10 exemplos reais com título e motivo); (g) fontes sugeridas, ligadas ou não; (h) perguntas para o dono; (i) próximos passos.
2. Commits pequenos na `hen` (nada de commit gigante), testes verdes, `lock release` feito.
3. `engine/benchmarks/corvo_gate_eval.py` funcionando e documentado no topo do arquivo, para qualquer pessoa repetir a medição.
4. Nada de segredo, corpus ou arquivo `.sqlite` no commit. Confira com `git diff --cached --name-only` antes de commitar.

## 11. Armadilhas já conhecidas
- O console do Windows não é UTF-8: títulos com acento e emoji quebram `print`. O CLI já reconfigura a saída; scripts novos precisam fazer o mesmo ou escrever em arquivo UTF-8.
- O **primeiro ciclo** lê histórico dos feeds (muito `stale`); meça o regime normal a partir do segundo ciclo, ou descarte o primeiro da análise.
- `received` não conta itens já vistos: não compare com o total bruto do feed.
- O heredoc do shell do ambiente pode falhar com certos caracteres; para criar arquivos longos use a ferramenta de escrita de arquivos, não `cat <<EOF`.
- Datas de feed podem estar no futuro ou ausentes: o leitor limita ao "agora"; item sem data vira "agora" (pode inflar a frescura de feed sem data, verifique).
- Palavras ambíguas: "Fed" (banco central x "fed up"), "SEC" (regulador x segundos), "ETF", "Georgia", "Jordan", "Turkey". Teste sempre com contraexemplos.
- Não otimize para o seu conjunto de ajuste: o conjunto lacrado é o juiz.

## 12. Condições de parada
Pare e escreva no relatório (sem insistir) se: um servidor bloquear o projeto (403/429 repetido); os testes ficarem vermelhos por algo que você não entende; qualquer ação exigir segredo, deploy ou mudança de contrato; o disco ou o corpus crescer de forma anormal (acima de ~200 MB). A noite é de coleta e medição; **nenhuma ação irreversível**.

## 13. Definição de pronto
- [ ] Corpus de ≥ 3.000 itens únicos e ≥ 300 rótulos, com conjunto de avaliação lacrado e semente registrada.
- [ ] Script de avaliação reproduzível e linha de base salva.
- [ ] Pelo menos T1, T2, T3 e T7 entregues, com métricas antes/depois **no conjunto lacrado**.
- [ ] Testes verdes; nenhum arquivo de segredo, corpus ou `.sqlite` versionado.
- [ ] Relatório completo, honesto sobre o que não melhorou.
