# CODEX — ordem de serviço: coleta e treino do bot do CORVO

> Leia inteiro antes de tocar em qualquer arquivo. Você trabalha sozinho por várias horas e ninguém responde dúvidas até de manhã. Se travar, registre no relatório e passe para a próxima tarefa. Não improvise fora das regras da seção 4.

## Prompt de partida (cole isto no Codex)
```text
Você é o agente "codex-noite" do projeto CORVO, repositório C:\projetos\Pulso, branch hen.

MISSÃO: TREINAR HUGIN E MUNIN PARA FICAREM MELHORES, rodada após rodada. "Melhor" não é opinião: é número no placar
(docs/corvo/TREINO_LOG.md) e subida na escada de níveis (docs/corvo/HUGIN_MUNIN_TREINO.md, seção 0.1).
  - HUGIN (lê e filtra): grava só o que pode mexer em mercado. Meça o que ele erra (grava lixo, perde o que importa) e ensine-o
    ajustando termos, ruído, pesos e cortes, provando cada melhora no conjunto de avaliação LACRADO.
  - MUNIN (lembra e confere): ainda não há previsões reais. Ensine-o a ser honesto: endureça a bancada (engine/corvo_engine/munin),
    simule cenários (previsor calibrado, exagerado, com vazamento, com pouca amostra) e escreva as regras de como ele aprenderá
    quando houver dados (amostra mínima, correção de múltiplos testes, divisão temporal). Nunca invente acerto.
Treino aqui NÃO é rede neural: é o ciclo MEDIR → AJUSTAR → PROVAR → REGISTRAR, repetido. Na dúvida sem efeito plausível em preço, descarte.

COMECE por docs/corvo/CODEX_START_HERE.md (1 página): traz a regra de ouro de NÃO ESTOURAR O BANCO. O freio
engine/benchmarks/corvo_budget_check.py precisa passar antes de CADA commit; freio vermelho = não commite.

LEIA, nesta ordem: docs/corvo/CODEX_START_HERE.md → docs/corvo/CODEX_BRIEF_COLETA.md (ordem de serviço, regras, tarefas T0 a T12)
→ docs/corvo/HUGIN_MUNIN_TREINO.md (o que é "certo", métricas, escada de níveis) → engine/AGENTS.md (10 regras curtas).

COMO COMEÇAR (Fase 0):
  cd C:\projetos\Pulso
  py scripts/corvo_codex_preflight.py        (precisa dar PRONTO)
  cd engine
  py benchmarks\corvo_budget_check.py data\corvo_corpus\corpus.jsonl     (linha de base do banco, ANTES de mexer)
Registre-se no quadro: py scripts/agentbus.py register codex-noite --role "treino de Hugin e Munin"

CADA RODADA DE TREINO (faça várias; uma por mudança relevante):
  1. MEDIR   - corvo_gate_eval.py (ajuste e lacrado) + corvo_budget_check.py. Anote a linha de base no TREINO_LOG.md.
  2. ENSINAR - escolha UMA alavanca por vez (ruído, peso de tema, corte, léxico ES/FR, dedup, geocódigo, kind). Mude só no que o
               conjunto de AJUSTE mostra.
  3. PROVAR  - rode o conjunto LACRADO uma vez. Melhorou sem piorar outra métrica e com o freio verde? Commit. Se não: reverta e registre.
  4. REGISTRAR - uma linha no TREINO_LOG.md (o que mudou, métricas antes/depois, commit). Pare quando duas rodadas seguidas não
               melhorarem o lacrado (platô): escreva o que falta aprender e deixe pronto para a próxima noite.

PRIORIDADE: T0 (auditar o banco, só com rede), T1 (HOT x BUFFER), T2 (relevância "só mercado"), T3 (dedup), T8 (carga), depois
T12 (Munin), T4, T5, T6, T9, T7. Termine bem o que começar.

PROIBIDO: deploy, wrangler, Turso, gh secret, escrever na API de produção (nada de POST), ler ou imprimir .env, tokens ou a chave do
git-crypt, mudar contrato, editar apps/worker, database, packages/shared e .github/workflows, merge, branch nova, push --force.
Trabalhe local, em --dry-run, só na branch hen. Você pode estar sem rede: trabalhe sobre engine/data/corvo_corpus/corpus.jsonl, pule
T0 e T10 sem rede e registre. Se uma permissão for negada, NÃO contorne: anote e siga. Não olhe os itens do conjunto lacrado para
decidir uma regra.

ENTREGA: docs/corvo/TREINO_LOG.md atualizado e docs/corvo/RELATORIO_NOITE_<data>.md (use RELATORIO_NOITE_MODELO.md), com a saída do
freio de banco ANTES e DEPOIS, métricas nos dois conjuntos, o que piorou ou foi revertido, o nível atual de Hugin e de Munin e as
perguntas para o dono. Commits pequenos, em inglês, git add por nome de arquivo, com a trava do quadro, no nome do dono.
```

## 0. Prontidão e ambiente (leia antes de tudo)
- **Primeiro, leia `CODEX_START_HERE.md`** (uma página): ela traz a **regra de ouro de não estourar o banco** e o **freio de banco** (`engine/benchmarks/corvo_budget_check.py`), que precisa passar antes de **cada** commit.
- **Prontidão:** `cd C:\projetos\Pulso` e `py scripts/corvo_codex_preflight.py`. Ele confere branch, testes, corpus e amostra, reserva as suas pastas no quadro e imprime o prompt acima. Só comece com **PRONTO**. As instruções curtas que o Codex lê sozinho estão em `engine/AGENTS.md`.
- **Você pode estar sem rede (o normal).** O corpus é coletado por **outro processo** (`scripts/corvo_corpus_loop.ps1`, iniciado pelo dono) em `engine/data/corvo_corpus/corpus.jsonl`. Trabalhe sobre esse arquivo. **Só T0 (ler o feed público) e T10 (verificar URLs de fontes novas) precisam de rede**: sem rede, pule, registre no relatório e siga. **Nunca** tente liberar rede, trocar o sandbox nem contornar uma permissão negada.
- **Relatório:** use `docs/corvo/RELATORIO_NOITE_MODELO.md` como esqueleto.

## 1. Missão
Cuidar de **tudo da coleta e do treino do bot** do CORVO:
1. **Coleta:** manter e ampliar a leitura de notícias do mundo (feeds oficiais e de imprensa), com saúde de fontes medida.
2. **Triagem (o portão):** decidir, **antes de salvar qualquer coisa**, se cada notícia vai ou não para o banco, gravando **só o que pode mexer em mercado** (cripto, ações, câmbio, juros, commodities, e o risco geopolítico ou físico que chega a eles).
3. **Destino:** garantir que o que é descartado não deixa texto em lugar nenhum e que o banco fica enxuto.
4. **Prova:** mostrar com números, em dados que o ajuste nunca viu, que o bot decide melhor de manhã do que à noite.

> **Diretriz do dono:** "buscar coisas que mudam o mercado, não algo que não influencie, para não popular tanto o banco." Na dúvida sobre uma notícia **sem efeito plausível em preço**, **descarte**. O banco deve conter pouca coisa e toda ela relevante.

### O que "treinar" significa aqui
**Não é treinar rede neural.** O portão é determinístico (listas de termos, pesos, limiares). Treinar = coletar corpus real, rotular uma amostra, **medir** erros (o que entrou e não devia; o que ficou de fora e devia entrar) e **ajustar regras e limiares** até as métricas melhorarem em dados que o ajuste nunca viu. Sem LLM decidindo em produção, sem probabilidade inventada.

## 2. Contexto do produto (2 minutos)
- **CORVO:** motor preditivo do mundo todo. Nome: Hugin (pensamento: lê, filtra, classifica, localiza) e Munin (memória: guarda, registra previsões, confere, esquece), os corvos de Odin.
- **Arquitetura:** a coleta roda hoje no GitHub Actions (`.github/workflows/collect.yml`, a cada 10 min, **só liga depois do merge na `main`, decisão do dono**) e depois no Oracle (junto do repositório MNEME). Eles empurram lotes para a API `corvo-api` (Cloudflare Worker sobre **Turso**); o painel `corvo-web` só lê.
- **Por que o portão existe:** o banco tem limite (Turso grátis: 10 milhões de escritas por mês; teto de projeto de 300 mil linhas por dia, `DAILY_WRITE_LIMIT`). Cada notícia gravada custa ~2 linhas. **Toda linha gravada precisa merecer.** Mais do que quota, o objetivo é **qualidade**: um painel e, no futuro, previsões alimentados só por sinal.
- Leia também: `docs/corvo/TRATAMENTO_NOTICIAS.md`, `docs/corvo/ARQUITETURA.md`, `docs/COLLECTION_PROTOCOL.md`, `docs/sources/SOURCES.md`, `AGENTS.md`.

## 3. Estado atual (2026-11-07, commit `65fe391` e posteriores)

### 3.1 Produção (você não mexe, só precisa saber)
API e painel no ar sobre Turso. Já houve **duas coletas reais**. A última, com o filtro atual: **818 itens lidos, 52 gravados (6,4%), 53 linhas** de um teto de 300 mil. Painel: https://corvo-web.henriquesouza.workers.dev. Você pode **ler** (somente GET) `https://corvo-api.henriquesouza.workers.dev/api/corvo/feed` para auditar o que foi para o banco (seção 8, T0).

### 3.2 O que já foi feito antes da sua noite (linha de base)
Em uma revisão manual das 818 notícias reais:
- **Relevância é avaliada ANTES da idade.** "stale" agora só marca notícia que importava e ficou velha.
- **Janela de frescor por fonte** (`max_age_h` no `catalog.json`): oficiais 72 h, imprensa 24 h.
- **Léxico v2** (`intake/gate.py`, `TOPICS` e `_NOISE`): termos específicos (commodity só com contexto de preço, "troops" só em deslocamento, política monetária e não rotina de banco central), 11 temas de mercado, incluindo `conflito_chave` (exige região-chave E ação). **O título decide**; tema só no resumo vale 60%.
- **Ruído** (esporte, celebridade, opinião, "price prediction", rotina regulatória, ajuda humanitária).
- Corte BUFFER normal 0,50 e HOT 0,75; pressão aperta (economia 0,60/0,85; crítico 0,95/0,95).

Resultado no corpus do dia 07/11 (818 itens, 24 feeds, 0 falhas), portão v2: **666 `irrelevant`, 71 `stale`, 29 `below_threshold`, 32 HOT, 20 BUFFER**. Com o pré-ajuste v3 (commit desta sessão) a relevância aceita 89 de 816 únicos (só título, sem idade nem duplicata), contra 110 antes.

### 3.3 Problemas conhecidos (comece por aqui, confirme com dados)
1. **HOT generoso demais.** Na revisão só por relevância, ~79% dos aceitos são HOT (70 de 89). HOT deveria ser raro (alvo ≤ 25% dos aceitos). Reavalie pesos e o corte HOT.
2. **Conflito e fala de banco central (pré-ajuste v3 já feito).** O conflito regional deixou de gravar sozinho e a fala de dirigente também; a auditoria dos 52 gravados foi de 35% para 62% de keep (otimista: ajustado olhando esses mesmos itens). **Confirme no conjunto lacrado**; ainda faltam os marginais restantes (banco do Paraguai, balanços, "S&P exposto à IA").
3. **Rotina residual:** "Federal Reserve Board requests public comment... stablecoin" (marginal), "PRA fines HDI Global ..." classificado como `comercio` (investigue qual termo casou), "Air raid alerts and attacks on schools" (UN).
4. **UN News** é quase todo humanitário; meça se a fonte vale a pena (ficha da fonte, T5). **G1 geral** tem pouco rendimento de mercado.
5. **Geocodificador:** vários itens relevantes sem lugar; risco de falso positivo (um item de incêndio local no Brasil apareceu como "Israel/Gaza" por algum termo do resumo: investigue).
6. **Quase-duplicatas:** a mesma notícia (ex.: ataque em Qeshm, MEXC, hack da Binance) aparece em 3 a 6 fontes; o portão só pega parte.
7. **Mundo não anglófono:** o léxico é inglês e português; espanhol e outros passam menos.
8. **Primeiro ciclo é histórico:** lê dias de feed de uma vez; meça o regime normal a partir do 2º ciclo.

## 4. Regras invioláveis
**Git e coordenação** (`AGENTS.md`):
1. Trabalhe só na branch **`hen`**. Nunca na `main`, **nunca crie outras branches**. Antes: `git status`, `git branch --show-current`, `git pull`.
2. Quadro de agentes: `py scripts/agentbus.py register codex-noite --role "coleta e treino do portao CORVO"`; `who`; reserve o que vai editar com `claim`. Para commitar: `py scripts/agentbus.py lock acquire codex-noite --note "..."` e `lock release` ao terminar. `git add` **sempre por nome de arquivo** (nunca `-A` nem `.`). Rode `py scripts/agentbus.py check-staged codex-noite` e `sh scripts/gitcrypt_check.sh` antes de commitar.
3. Commits pequenos, mensagem em inglês `tipo(escopo): resumo`, **no nome do dono do repositório** (use o `git config` existente; não troque `user.name` nem `user.email`). **Nunca `push --force`.** **Nunca merge na `main`** (o PR da `hen` já está aberto; o dono decide o merge).
4. Antes de cada commit: `cd engine && py -m pytest tests/test_intake_gate.py tests/test_oracle_publisher.py tests/test_collect_runner.py tests/test_munin.py tests/test_corvo_bench.py tests/test_corvo_budget.py -q` **e** `py benchmarks\corvo_budget_check.py data\corvo_corpus\corpus.jsonl` (o freio de banco precisa dizer "dentro dos limites seguros"). Se algo seu ficar vermelho, conserte ou reverta; freio vermelho = **não commite**.

**Segredos e produção** (nada disso é seu):
5. **Não rode** `wrangler`, comandos do Turso, `gh secret`, nem `curl` com método diferente de GET na API de produção. **Não leia nem imprima** `deploy/oracle/.env`, `apps/worker/.dev.vars`, `~/corvo-gitcrypt.key` nem tokens. **Não use** `POST /api/corvo/ingest` nem `/api/corvo/purge`. Todo o seu trabalho é **local**, com `--dry-run`.
6. Nunca commite o corpus (`engine/data/corvo_corpus/` está no `.gitignore`: títulos e links de terceiros) nem `*.sqlite`.
7. **Não edite** `.github/workflows/`, `apps/worker/`, `database/`, `packages/shared/` (pertencem a outro agente e/ou mudam contrato). Você só altera `engine/corvo_engine/` (portão, coleta, geocodificador, publicador), seus testes, `engine/benchmarks/` e a documentação em `docs/corvo/`.

**Fontes e coleta** (`docs/COLLECTION_PROTOCOL.md`):
8. Só **RSS/Atom públicos e APIs oficiais**. Nada de raspar HTML, burlar login, captcha, paywall ou limite, nem fingir ser navegador. Mantenha o `User-Agent` identificado do projeto.
9. **Educação com servidores:** no máximo 1 leitura a cada 5 min por feed (o `--interval` impõe mínimo de 300 s) e 2 conexões por servidor. Se um servidor devolver 403/429, **desative aquele feed** (`"enabled": false`) e anote.
10. Antes de **ligar fonte nova**, registre em `docs/sources/SOURCES.md`: acesso, termos de uso, limite, custo, autenticação, licença, retenção e exibição pública. Sem isso, ela entra com `"enabled": false`.
11. O CORVO guarda **título, link e resumo curto** com atribuição. **Nunca o corpo da matéria.** Nunca pessoas, rostos ou perfis individuais.

**Honestidade científica:**
12. **Separe os dados:** ajuste com 70% dos itens rotulados e avalie com os 30% restantes, **que você não olha enquanto ajusta** (semente fixa registrada). Reporte as duas medidas. Melhoria só no conjunto de ajuste não conta.
13. Não esconda resultado ruim; se uma ideia piorou, reverta e registre. Não invente dados, rótulos "oficiais" nem manchetes. Alegação não é fato.
14. **Mudança de contrato** (formato do lote, tabelas): **não faça**; proponha no relatório.

## 5. Mapa do código
| Arquivo | O que faz |
|---|---|
| `engine/corvo_engine/collect/catalog.json` | catálogo de feeds: `id`, `url`, `region`, `kind`, `reliability` 0 a 1, `official`, `max_age_h`, `enabled` |
| `engine/corvo_engine/collect/feeds.py` | lê um feed e devolve `NewsItem` (reusa o leitor endurecido de `collectors/news/rss.py`) |
| `engine/corvo_engine/collect/runner.py` | um ciclo: feeds, descarta já vistos, portão, publica. CLI `python -m corvo_engine.collect` |
| `engine/corvo_engine/intake/gate.py` | **o portão**: `TOPICS`, `_NOISE`, `score()`, `GateConfig`, `IntakeGate._decide()` |
| `engine/corvo_engine/intake/geo.py` | geocodificador por tabela (`_PLACES`) |
| `engine/corvo_engine/intake/store.py` | memória de URLs já vistas (SQLite, 48 h) |
| `engine/corvo_engine/oracle/publisher.py` | monta o lote, `classify_kind`, estatística por execução (delta), `last_decisions` |
| `engine/corvo_engine/munin/` | **Munin** (memória): `scoring` (Brier, taxa-base, skill, ECE), `registry` (validador de previsão), `leakage` (anti-futuro), `retention` (o que se guarda e por quanto tempo). 18 testes |
| `engine/benchmarks/corvo_munin_eval.py` | bancada de prova de Munin (`--synthetic` ou arquivo de resolvidas) |
| `engine/benchmarks/corvo_make_sample.py` | monta a amostra de rotulagem (aceitos + rejeitados, lacre 70/30, pesos) |
| `engine/benchmarks/corvo_label.py` | ajudante de rotulagem: mostra títulos **sem a decisão do portão**, grava K/M/D com estrato, peso e lado (ajuste ou lacrado) |
| `engine/benchmarks/corvo_gate_eval.py` | mede o portão contra os rótulos, **ponderado**, por conjunto |
| `engine/benchmarks/corvo_budget_check.py` | **freio de banco**: projeta linhas/dia do portão atual e falha se passar do limite seguro |
| `scripts/corvo_codex_preflight.py` | confere a prontidão e imprime o prompt de partida |
| `scripts/corvo_corpus_loop.ps1` | laço de coleta do corpus em teste a seco (rodado pelo dono) |
| `engine/benchmarks/corvo_review.py` | **ferramenta de revisão**: recalcula a relevância de um corpus e lista aceitas e rejeitadas (só relevância; ignora idade, duplicata e cota) |
| `engine/tests/test_intake_gate.py`, `test_oracle_publisher.py`, `test_collect_runner.py` | testes que protegem o comportamento |
| `apps/worker/src/routes/corvo.ts` | API (**só leia**): formato do lote, teto de escrita |

Decisões: **HOT** (grava, relevância ≥ corte alto), **BUFFER** (grava, relevância média), **DROP** (não grava; vira contador e hash da URL por 48 h). Motivos: `stale` (relevante e velho), `duplicate_url`, `near_duplicate`, `irrelevant` (relevância 0), `below_threshold` (relevância baixa), `source_quota`, `malformed`.

## 6. Comandos (PowerShell, na pasta `engine`)
```powershell
cd C:\projetos\Pulso\engine
# prontidão (na raiz do repositório): confere tudo e imprime o prompt de partida
py scripts/corvo_codex_preflight.py
# (rodado pelo dono, em outra janela) laço de coleta do corpus: powershell -File scripts\corvo_corpus_loop.ps1 -Hours 6
# um ciclo de teste, mostra os aprovados (nada é enviado)
py -m corvo_engine.collect --once --dry-run
# registra a decisão de CADA item (inclusive descartes) num corpus local
py -m corvo_engine.collect --once --dry-run --quiet --dump data\corvo_corpus\corpus.jsonl
# laço da noite: um ciclo a cada 10 min (use o limite de tempo que preferir)
$fim = (Get-Date).AddHours(6)
while ((Get-Date) -lt $fim) { py -m corvo_engine.collect --once --dry-run --quiet --dump data\corvo_corpus\corpus.jsonl; Start-Sleep -Seconds 600 }
# montar a amostra de rotulagem (divisão 70/30 estável por URL) e rotular sem ver a decisão do portão
py benchmarks\corvo_make_sample.py data\corvo_corpus\corpus.jsonl --n 300
py benchmarks\corvo_label.py status data\corvo_corpus\corpus.sample.jsonl
py benchmarks\corvo_label.py show   data\corvo_corpus\corpus.sample.jsonl --from 0 --count 40
py benchmarks\corvo_label.py apply  data\corvo_corpus\corpus.sample.jsonl --from 0 --codes KMDKKMD...   # K=keep M=marginal D=drop -=pular
# medir o portão contra os rótulos (ponderado, por conjunto)
py benchmarks\corvo_gate_eval.py data\corvo_corpus\corpus.labels.jsonl
py benchmarks\corvo_gate_eval.py data\corvo_corpus\corpus.labels.jsonl --split eval   # lacrado: UMA vez por rodada de ajuste
# revisar o efeito de uma mudança de léxico sem recoletar
py benchmarks\corvo_review.py data\corvo_corpus\corpus.jsonl --rejected --limit 300
# auditar o que foi para o banco (somente leitura)
Invoke-RestMethod https://corvo-api.henriquesouza.workers.dev/api/corvo/feed | ConvertTo-Json -Depth 6 | Out-File data\corvo_corpus\feed_atual.json -Encoding utf8
```
Cada linha do `corpus.jsonl`: `cycle_at, source_id, url, title, published_at, verdict, reason, relevance, topics, region, pressure`. A memória de vistos do teste a seco fica em `corvo_seen_dry.sqlite` (apague para recomeçar). Em scripts novos, configure a saída UTF-8 (o console do Windows não é).

## 7. Plano da noite
**Fase 0 (15 min), preparar.** Registre-se, rode os testes (devem passar), rode um ciclo e confirme que os 24 feeds respondem. Anote hora de início e versões.

**Fase 1 (a noite toda, em segundo plano), coletar o corpus.** O laço é iniciado **pelo dono** (`scripts\corvo_corpus_loop.ps1`); se você tiver rede, pode iniciar o da seção 6 em outra janela. Trabalhe sobre `corpus.jsonl` enquanto ele cresce. Meta: ≥ 30 ciclos cobrindo horários de Ásia, Europa e Américas. O corpus parte de ~800 itens (o histórico dos feeds) e cresce só com o que é NOVO a cada ciclo (estimativa: 30 a 60 itens por ciclo), então espere ~1.800 a 2.500 ao fim de 6 h. Comece a rotular com ≥ 1.500. Registre por ciclo: feeds com falha, tempo, itens novos.

**Fase 2 (≈1 h), rotular.** Com ≥ 1.500 itens, sorteie uma amostra **estratificada por fonte e por decisão atual** de ≥ 400 itens (mínimo 300) e rotule em `engine/data/corvo_corpus/labels.jsonl`: `{"url","label":"keep|marginal|drop","topic","kind":"fato|reportagem|rumor|opiniao|previsao","region"}`.
- **keep:** tem **efeito plausível em preço de ativo** ou em risco que chega a ele. Ex.: decisão de juros ou ata do FOMC; dado de inflação ou emprego; tarifa, sanção, embargo; corte de produção de petróleo; escalada militar em região de energia ou rota de navio; terremoto ou furacão em polo industrial; exploit ou ruína de exchange de cripto; falência, calote ou rebaixamento relevante; queda abrupta de bolsa.
- **marginal:** efeito indireto, lento ou incerto. Ex.: crise política que pode derrubar governo; pesquisa eleitoral em grande economia; balanço de empresa média. **Marginal conta como "não gravar" na precisão do HOT**, mas registre.
- **drop:** **sem efeito previsível em preço.** Ex.: celebridade, esporte, receita, publieditorial, opinião, incêndio ou obra local, crime comum, ajuda humanitária, rotina de órgão regulador (aprovação de aplicação, ata de comitê técnico), "como fazer", previsão de preço de blogueiro.
- Rotule **pelo conteúdo**, nunca pela decisão do portão. Reserve **30% (semente fixa registrada) como conjunto de avaliação lacrado**. Registre as regras de rotulagem e os casos ambíguos no relatório.

**Fase 3 (≈45 min), medir.** **Já existe** `engine/benchmarks/corvo_gate_eval.py` (testado): lê os rótulos e imprime, **por conjunto (ajuste e avaliação)**, o que segue. Rode, confira que bate com a conta que você faria à mão em 5 itens e **estenda** só o que faltar (linhas por dia, cobertura do mapa, acerto de `kind`):
- matriz `label × verdict` (keep/marginal/drop contra hot/buffer/drop);
- **precisão do HOT** (fração de HOT que é keep), **recall do keep** (fração de keep que ficou HOT ou BUFFER), **proporção de HOT entre os aceitos**;
- **taxa de keep descartado** (o pior erro, com o motivo do descarte) e **taxa de drop gravado** (o que polui o banco);
- projeção de **linhas por dia** = aprovados por dia × 2 + estatísticas, extrapolada do ritmo medido;
- cobertura do geocodificador (aprovados com `region`) e acerto do local na amostra;
- acerto do `kind` contra o rótulo.
Salve a linha de base em `docs/corvo/RELATORIO_NOITE_<data>.md` **antes** de mudar qualquer regra.

**Fase 4 (≈2 h), ajustar** na ordem da seção 8. Depois de cada mudança: testes verdes, rodar a avaliação e comparar com a linha de base **nos dois conjuntos**.

**Fase 5 (≈30 min), relatório e entrega** (seção 10).

## 8. Tarefas (por prioridade) e critérios de aceite
| # | Tarefa | Aceite |
|---|---|---|
| T0 | **Auditar o que já foi para o banco.** Leia o feed atual (GET) e classifique cada notícia gravada como keep, marginal ou drop. | Tabela no relatório: quantas das gravadas são keep. Meta ≥ 85% das gravadas como keep. |
| T1 | **Calibrar HOT x BUFFER** (problemas 3.3 itens 1 e 2). HOT deve ser raro e realmente importante. | HOT ≤ 25% dos aceitos; precisão do HOT ≥ 0,85 no conjunto lacrado. |
| T2 | **Relevância "só mercado".** Meça o que o filtro perde (keep descartado) e o que deixa passar (drop gravado). Amplie o léxico (inglês, português, espanhol; bancos centrais, índices, commodities, moedas), refine `TOPICS` e `_NOISE`, reavalie pesos e cortes. Determinístico. | Recall do keep ≥ 0,90 e precisão do HOT ≥ 0,85 **no conjunto lacrado**; taxa de drop gravado cai sem subir o keep descartado. |
| T3 | **Quase-duplicata.** Normalizar títulos (acento, caixa, stopwords, aspas), testar limiares de Jaccard, comparar também com o resumo. Medir **fusões erradas** (dois fatos tratados como um): pior que deixar passar uma cópia. | Fusões erradas ≤ 2% das comparações revisadas; cópias entre fontes reduzidas; testes com pares positivos e negativos. |
| T4 | **Janela de frescor por classe** com dados (mediana e p90 da idade por feed; quantos keeps viram `stale`). Ajustar `max_age_h` no catálogo. | Menos keeps perdidos por `stale`, sem explodir linhas; teste por classe. |
| T5 | **Ficha de cada fonte:** itens por dia, % `irrelevant`, % `stale`, % duplicata, % aprovados, quem publica primeiro. Recomendar `reliability` e quem desativar (UN, G1 geral...). | Tabela no relatório; ajustes de `reliability` no catálogo com evidência; `enabled` só com justificativa. |
| T6 | **Cobertura e acerto do geocodificador.** Adicionar países, capitais e hubs financeiros que aparecem no corpus sem local, **evitando falso positivo** (Georgia, Jordan, Turkey, nomes de empresas); investigar o falso "Israel/Gaza". | Cobertura dos aprovados ≥ 85% e acerto na amostra ≥ 95%; testes de falso positivo. |
| T7 | **Classificação `kind`** (fato, reportagem, rumor, opinião, previsão). Na dúvida, **reportagem**; só fonte oficial vira **fato**. | Acerto ≥ 0,80 e **nenhum rumor ou opinião classificado como fato**. |
| T8 | **Simulação de carga e orçamento.** Simule 24 h com o volume medido e com **5×**, sob pressão normal, economia e crítico. | Projeção ≤ 5 mil linhas/dia no ritmo medido e ≤ 25 mil com 5×; teste automatizado. |
| T9 | **Robustez da coleta.** Feed que muda de formato, devolve HTML, trava, dá 5xx ou 403 não derruba o ciclo. Teste respostas ruins (XML quebrado, vazio, gigante, redirecionamento). | Testes novos; o ciclo sempre termina e registra a falha por fonte. |
| T10 | **Novas fontes candidatas** (só oficiais e RSS/Atom): SEC, CFTC, US Treasury (OFAC), BCE/BoJ/PBoC se houver feed, GDACS, NOAA/NHC, USGS (mais feeds), IMF/WTO/OPEC, agências de Ásia, África e América Latina (espanhol e português). **Verifique cada URL na hora.** | Cada fonte nova com linha em `SOURCES.md`; `enabled: false` se os termos não estiverem claros. Máximo de 15 novas. |
| T12 | **Munin: usar e endurecer a bancada** (`corvo_engine/munin`). Rode `corvo_munin_eval.py --synthetic`, escreva cenários realistas (previsor com viés, com poucos dados, com vazamento) e **mais testes** nos invariantes de M1/M2. Proponha M3 (tabela tema para ativos) e M6 (regra de aprendizado com amostra mínima de 30) **sem mudar contrato**. | Novos testes passando; relatório com a proposta de M3 e M6; nenhuma previsão inventada. |
| T11 | **Agrupamento por acontecimento** (proposta, **sem implementar contrato**): quantos aprovados são o mesmo fato em fontes diferentes e quanto o agrupamento economizaria. | Seção no relatório com números e desenho de contrato para o dono aprovar. |

**Prioridade:** T0, T1, T2, T3, T8 (qualidade e economia do que vai ao banco); depois T12 (Munin), T4, T5, T6, T9, T7; T10 e T11 se sobrar tempo. Termine bem o que começou.

## 9. A regra de decisão que você está calibrando
```
chegou um item
  ├─ URL já vista nas últimas 48 h?        → fora, sem contar (nem aparece em "recebidas")
  ├─ mal formado?                           → DROP malformed
  ├─ relevância < corte BUFFER (pressão)?   → DROP irrelevant / below_threshold
  ├─ velho demais (janela da fonte)?        → DROP stale        (só vale para o que era relevante)
  ├─ mesma URL ou título quase igual?       → DROP duplicate_url / near_duplicate
  ├─ cota por hora da fonte estourada?      → DROP source_quota
  ├─ relevância ≥ corte HOT?                → HOT    (grava)
  └─ senão                                  → BUFFER (grava, entra em lote)
descarte = só contador por motivo + hash da URL (48 h). Nunca o texto.
```
Pressão (lida do Worker): **normal** (<60% do teto diário), **economia** (60 a 85%), **crítico** (>85%). Cortes em `GateConfig`: HOT 0,75 / 0,85 / 0,95; BUFFER 0,50 / 0,60 / 0,95. São palpites a medir.

**Custo dos erros:** deixar passar uma notícia que mexe em mercado (keep descartado) é o pior erro; mas o dono quer banco enxuto, então o drop gravado também é erro e é o que mais polui o painel. Mostre a troca nos números.

## 10. O que entregar de manhã
1. **`docs/corvo/RELATORIO_NOITE_<data>.md`:** (a) resumo de 10 linhas para o dono; (b) tabela antes e depois das métricas, nos dois conjuntos; (c) mudanças, uma por linha, com o commit; (d) fichas das fontes; (e) o que **piorou** ou foi revertido; (f) 10 exemplos reais que o portão ainda erra (título e motivo); (g) fontes sugeridas, ligadas ou não; (h) auditoria do banco (T0); (i) perguntas para o dono; (j) próximos passos.
2. Commits pequenos na `hen`, testes verdes, `lock release` feito.
3. `engine/benchmarks/corvo_gate_eval.py` (já existe) estendido e documentado no topo com o que você acrescentar, para qualquer pessoa repetir a medição.
4. Nada de segredo, corpus ou `.sqlite` no commit (`git diff --cached --name-only` e `sh scripts/gitcrypt_check.sh`).

## 11. Armadilhas já conhecidas
- O console do Windows não é UTF-8: títulos com acento e emoji quebram `print`. O CLI já reconfigura a saída; scripts novos precisam fazer o mesmo.
- O shell do ambiente pode falhar com certos heredocs; para criar arquivos longos use a ferramenta de escrita de arquivos.
- `received` não conta itens já vistos: não compare com o total bruto do feed.
- A ferramenta `corvo_review.py` mede **só relevância** (ignora idade, duplicata e cota) e usa só o título: aceita mais que o portão real (110 contra 52 no corpus de 07/11).
- Datas de feed: futuras são limitadas ao "agora"; item sem data vira "agora" (pode inflar a frescura de feed sem data).
- Palavras ambíguas: "Fed", "SEC", "ETF", "Georgia", "Jordan", "Turkey", "gold", "war", "troops". Teste sempre com contraexemplos.
- Não otimize para o conjunto de ajuste: o conjunto lacrado é o juiz.

## 12. Condições de parada
Pare e escreva no relatório (sem insistir) se: um servidor bloquear o projeto (403/429 repetido); os testes ficarem vermelhos por algo que você não entende; qualquer ação exigir segredo, deploy, escrita na API ou mudança de contrato; o corpus passar de ~200 MB. **Nenhuma ação irreversível.**

## 13. Definição de pronto
- [ ] Corpus ≥ 1.500 itens únicos e ≥ 300 rótulos, com conjunto lacrado e semente registrada.
- [ ] Script de avaliação reproduzível e linha de base salva.
- [ ] Pelo menos T0, T1, T2, T3 e T8 entregues, com métricas antes e depois **no conjunto lacrado**.
- [ ] Testes verdes; nenhum segredo, corpus ou `.sqlite` versionado.
- [ ] Relatório completo e honesto sobre o que não melhorou.
