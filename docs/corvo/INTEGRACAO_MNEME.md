# Integração do CORVO ao MNEME: contrato de dados

**Estado:** análise estática dos repositórios em 11/11/2026. Esta proposta não implementa transporte, não grava no MNEME e não habilita coletores.

## Decisão de arquitetura

O CORVO entra **dentro do fluxo Python do MNEME**, como camada de curadoria/verificação e estudo de eventos. Não deve manter uma segunda API de produto nem escrever no Worker/D1 do próprio CORVO para alimentar o MNEME. A persistência de eventos do MNEME hoje é `ArmazemEventos` em Parquet; Turso, Cloudflare e D1 não fazem parte desta integração.

O MNEME já contém `noticias.py` (RSS, parsing, classificação inicial e atributos de atenção) e `inteligencia.py` (ciclo de coleta a cada cinco minutos, deduplicação por ID e gravação). Portanto, o primeiro encaixe é um adaptador interno chamado pelo serviço existente, não outro daemon nem um segundo coletor independente.

## Contrato que o MNEME já consome

`ArmazemEventos.gravar("noticias", "GLOBAL", linhas)` persiste registros tabulares em `robo/mneme/dados/eventos.py`. A chave de deduplicação de notícia é `id`; o leitor filtra point-in-time por `recebido_em`. O código de `noticias.py` produz hoje estes campos principais:

| Campo | Uso observado | Cuidado para integração |
|---|---|---|
| `id` | SHA-256 curto do link, chave de dedup | Guardar também ID estável do evento agrupado; artigo não é evento |
| `fonte`, `categoria`, `confiabilidade` | Proveniência e classe inicial da fonte | Confiabilidade atual é rótulo estático, não acurácia histórica medida |
| `titulo`, `resumo`, `url` | Conteúdo e referência | Texto externo é dado não confiável; preservar link e hash do conteúdo normalizado |
| `ocorrido_em` | Hoje recebe a data de publicação; se ausente/futura, usa hora de coleta | Não equivale sempre ao momento em que o fato ocorreu; separar publicação e ocorrência antes de estudo de evento |
| `recebido_em` | Hora da coleta local | É o corte point-in-time primário: nada pode aparecer antes dela |
| `tipo`, `ativos`, `temas`, `sentimento`, `relevante`, `suspeito` | Classificação heurística | Não são confirmação nem previsão; não substituir sem versão e comparação |

`com_noticias()` transforma notícias em atributos `n_*` por vela fechada: menções, anomalia, sentimento, número de fontes, concentração e fração de rumor. O início do histórico limita cobertura; ausência anterior à coleta é `NaN`, não zero. A camada CORVO deve acrescentar sinais versionados e não alterar silenciosamente a semântica desses atributos.

## Pontos de risco encontrados

1. **Campo temporal ambíguo:** `ler_feed()` grava publicação em `ocorrido_em`, e usa chegada como fallback. A arquitetura do MNEME define `ocorrido_em` como hora do fato e `publicado_em` separadamente. Antes de resolver reação a preço, o esquema precisa distinguir `publicado_em`, `recebido_em` e `ocorrido_em` (quando identificável), sem inferir hora de evento pelo título.
2. **Fonte oficial não confirma automaticamente toda afirmação:** hoje `classificar()` marca qualquer item da categoria `oficial` como `fato`. Um comunicado confirma que a instituição publicou aquela declaração; não confirma toda previsão, opinião ou alegação citada nela. A ingestão do CORVO deve preservar `reportagem`/`interpretação` e registrar que tipo de alegação a fonte sustenta.
3. **Atenção não é confirmação:** `medidas_de_atencao()` pode contar matérias distintas sobre o mesmo evento. Isso é útil para volume, mas não deve ser usado como número de fontes independentes sem deduplicar evento e sindicação.
4. **Escopo atual estreito:** o coletor de notícias do MNEME tem dez feeds definidos; o protocolo/fontes do CORVO contém mais fontes e metadados. Incorporar fonte exige idempotência, termos/licença, categoria, frescor, limites e avaliação de falsos positivos/negativos; não basta copiar URLs.
5. **Coleta e previsão já têm donos:** `inteligencia.py` coleta e armazena; `previsor.py` consome as notícias via `com_noticias()`. O CORVO não deve produzir direção/ordem nem fazer o caminho em tempo real esperar LLM/RAG. Ele pode produzir evidência curada e atributos assíncronos point-in-time para ML quantitativo validar.

## Inventário inicial de fontes para o fluxo global

Comparação documental dos registros em `robo/mneme/noticias.py` e `docs/sources/SOURCES.md`/`CATALOGO_FONTES.md` do CORVO. “Disponível” significa status descrito no repositório, não revalidado nesta rodada.

| Fonte/família | MNEME hoje | CORVO hoje | O que acrescenta ao MNEME | Decisão inicial |
|---|---|---|---|---|
| Fed, ECB, BEA | RSS de releases/comunicados | RSS Fed e feeds/candidatos do catálogo | Fato institucional sobre política e dados macro; publicações/revisões e hora de divulgação | Reusar um único conector por feed e preservar release vs opinião; não contar duas cópias como confirmação |
| Bloomberg, FT, CNBC | RSS configurado | Catálogo RSS inclui imprensa, status/termos por fonte | Contexto e rapidez de cobertura; fonte secundária | Não duplicar feed sem ganho de cobertura/latência medido; separar notícia original de republicação |
| CoinDesk, The Block, Decrypt, Cointelegraph | Quatro RSS cripto | Catálogo RSS tem fontes cripto adicionais/candidatas | Eventos de protocolo, exchanges, ETF e incidentes de cripto | Comparar itens únicos, sindicância e termos; manter tipo `reportagem` até confirmação |
| Eurostat, WTO | Não aparecem no conjunto inicial de notícias | Candidatas tier 2; Eurostat precisa smoke test, WTO tem feed oficial | Dados/release estatístico europeu e avisos de comércio internacional | Bons candidatos globais após teste do parser, direito de uso e cadência; ficam desligados até aprovação |
| GDELT | Não listado como coletor principal | API registrada, desligada por 429 persistente/resultado vazio | Descoberta ampla de cobertura jornalística global, sem substituir fonte primária | Não ativar no estado atual; só reavaliar com teste permitido e orçamento de chamadas |
| USGS | Não listado | Feed sísmico significativo ativo; código atual limita coordenadas ao Brasil | Evento físico objetivo fora dos temas macro/cripto, com magnitude/local/hora | Para MNEME, primeiro rever escopo internacional e coordenadas antes de reutilizar; não é fonte de impacto financeiro por si só |
| BCB PTAX, Frankfurter, Binance | MNEME tem macro e preços próprios; notícias não substituem séries | PTAX/Binance/Frankfurter aparecem como contexto do painel; CORVO também tem arquivos locais de resolução | Cross-check de preço/referência; calendários/séries oficiais são mais adequados para ML | Não tratar snapshot de 24 h ou câmbio diário como preço de resolução intradiária; manter preço no pipeline de market data |
| Reddit, X, Mastodon, Bluesky, Google Trends | X existe atrás de credencial e teto de gasto | Reddit/X desativados; Mastodon desligado por baixa atividade; Bluesky sem conta validada; Trends com termos pendentes | Atenção social e detecção precoce, com risco alto de spam, concentração e manipulação | Não incluir no primeiro lote. Cada rede exige autorização/termos, custo, remoções, dedup de repost e atributo de concentração |
| Senado, Câmara, INMET, INPE, Defesa Civil, InfoDengue, ONS | Não aparecem no coletor de notícias global | Fontes nacionais oficiais/objetivas, várias ativas no CORVO | Contexto brasileiro de políticas, clima, fogo, saúde e infraestrutura | Só entram no MNEME quando evento/região tiver vínculo explícito com mercado/ativo; evitar inundar o modelo global com sinais sem relação demonstrada |

O inventário mostra dois grupos distintos: fontes que complementam o contexto financeiro internacional e fontes de inteligência situacional brasileira. “Mais fontes” não significa “mais independência”: antes de medir confirmação, normalizar domínio/autor, identificar sindicação e comparar horário de primeira publicação com `recebido_em`.

## Saída aditiva proposta para o CORVO

Uma evidência por artigo e um registro separado por evento, ligados sem confundir as duas identidades:

```text
artigo: id, fonte, url, hash_conteudo, publicado_em, recebido_em,
        idioma, titulo, resumo, tipo_evidencia, temas, ativos_candidatos,
        suspeito, versao_coletor, versao_filtro

evento: event_id, artigo_ids[], first_received_at, available_at,
        fontes_independentes[], temas, ativos_candidatos,
        estado_confirmacao, versao_clusterizador
```

`available_at` é o instante em que a última evidência incluída para a confirmação já tinha chegado. Não substituir por data de publicação. Rumor, opinião e interpretação são tipos distintos e não viram fato por volume de fontes. A lista de fontes independentes precisa descontar republicações/sindicação e guardar a regra que decidiu a independência.

Depois de um evento, o módulo de estudo pode propor hipóteses (tema, ativo, alvo, horizonte e regra de preço), sem emitir sinal operacional. A resolução usa somente séries compatíveis e dados disponíveis no instante; saída registrada como snapshot imutável mais resolução separada. O modelo do MNEME decide se atributos agregados têm valor em walk-forward, com comparação contra baseline e custo. RAG ajuda a formular/explicar hipóteses; não é rótulo de treino nem fonte de verdade para retorno.

## Etapas sem Python

1. Manter a coleta e publicação desligadas; não alterar Worker ou banco MNEME.
2. Aprovar os significados de `publicado_em`, `recebido_em`, `ocorrido_em`, `available_at`, `event_id` e da independência de fonte.
3. Fazer inventário comparativo de fontes MNEME/CORVO com termos, endpoint, cobertura, cadência, limite e campo único que cada uma entrega.
4. Definir tabela de quarentena/rejeição e motivos auditáveis: duplicada, sem data confiável, irrelevante, suspeita/injeção, fonte não licenciada, conteúdo incompleto.
5. Planejar migração aditiva de esquema e feature flags OFF por padrão; preservar atributos atuais e caminho rápido.
6. Só com Python disponível: implementar adaptador integrado a `Inteligencia.ciclo()`, testes de idempotência/PIT/clusterização, simular coleta sem envio e validar corpus rotulado separado no tempo.
7. Só após inspeção da saída e aprovação do dono, ligar armazenamento ampliado; manter qualquer influência preditiva em shadow até medir contra a baseline.

## Referências MNEME lidas

- `robo/mneme/noticias.py` — feeds, parse, classificação e atributos `n_*`.
- `robo/mneme/inteligencia.py` — periodicidade, dedup por artigo, gravação e serviço externo.
- `robo/mneme/dados/eventos.py` — Parquet, chave de dedup e filtro `como_de`.
- `robo/mneme/previsor.py` — consumo dos atributos de notícia no snapshot de previsão.
- `docs/PRODUCT_CHARTER.md` — separação entre ML, LLM/RAG, quantitativo e Risk Engine.
- `docs/architecture/MARKET_DATA_ENGINE.md` — point-in-time e timestamps.
- `docs/architecture/KNOWLEDGE_ENGINE.md` — separação entre RAG lento e notícias datadas.
- `docs/architecture/MACHINE_LEARNING_ARCHITECTURE.md` — baseline, validação temporal, calibração e promoção.
