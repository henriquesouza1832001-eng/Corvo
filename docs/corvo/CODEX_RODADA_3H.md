# Rodada de 3 horas do Codex: auditoria e plano

> **Natureza do CORVO (ordem do dono):** é um **robô de regras e estatística**, **não** uma IA generativa. Nada de modelo de linguagem decidindo, resumindo, classificando ou prevendo em produção. Tudo o que o Hugin e o Munin fazem tem de ser **determinístico, auditável e refeito por qualquer pessoa com lápis**. O Codex usa a própria inteligência só como **ferramenta de trabalho** (escrever regras, testes e rótulos de avaliação), nunca como componente do produto.

## 1. O que a auditoria da primeira noite achou
| Fato | Evidência |
|---|---|
| Código e testes estão sãos | 1046 testes passam, 6 esperados falhando (`xfail`); freio de banco verde (cerca de 470 linhas/dia) |
| Entregou pouco da lista | feitas: T1 (corte HOT), T8 (carga), T12 (cenários do Munin); parciais: T0, T3. **Não tocadas:** T2, T4, T5, T6, T7, T9, T10, T11 |
| Metade dos commits é ruído | 7 de 14 commits só dizem "coletei mais N itens" |
| O freio de qualidade é o lacre pequeno | só **15 casos "keep"** no lacre; todas as métricas ficaram "instáveis", e por isso quase nada foi promovido |
| Esperou dado em vez de trocar de tarefa | o diário diz "esperar mais dados" enquanto T5, T6, T7 e T9 **não dependem de rótulos novos** |
| Rótulos são do agente | quem rotula é o próprio Codex; o dono só confirmou 14 casos marginais. Rótulo de máquina pode repetir o viés da regra |
| A coleta contínua parou | o laço do corpus morreu; o corpus oficial tem só 906 linhas |

## 2. Regras novas para a próxima rodada
1. **Plataforma de dados primeiro (30 min).** Rodar `py scripts/corvo_codex_preflight.py`; **depois** de renovar o corpus, tirar um **lacre novo** de pelo menos **40 casos keep** no lado de avaliação. Sem isso, nenhuma regra de relevância é promovida.
2. **Nunca esperar dado.** Se uma tarefa trava por falta de amostra, **registre em uma linha e passe para a próxima da fila**. Duas rodadas sem melhorar = trocar de tarefa (já está no placar).
3. **Um commit por bloco de trabalho**, não por hora. Os batimentos ficam **só** em `TREINO_LOG.md` (uma linha por hora) e entram no commit seguinte que tiver conteúdo.
4. **Preferir tarefas que produzem código testável sem rótulos:** T6, T9, T7, T5 e T11.
5. **Auditoria dos próprios rótulos:** separar 40 itens já rotulados e **reler às cegas** (sem ver o rótulo antigo). Se a concordância ficar abaixo de 90%, a régua de "keep" está vaga: reescrever o critério antes de medir qualquer coisa.
6. **Sem IA generativa no produto:** nenhuma chamada a API de modelo, nenhuma dependência de LLM, nenhum texto de notícia enviado a serviço externo.

## 3. Plano de 3 horas

| Tempo | Tarefa | Entrega verificável |
|---|---|---|
| 0:00–0:30 | Preflight, renovar corpus (um ciclo manual, `--dry-run`), freio verde, novo lacre com 40+ casos keep | arquivo de amostra, contagem por conjunto |
| 0:30–1:15 | **T6 geolocalização:** cobertura dos aprovados e falsos positivos (Georgia, Jordan, Turkey, "Israel/Gaza") | testes novos de falso positivo; cobertura ≥ 85% |
| 1:15–1:50 | **T9 robustez:** XML quebrado, vazio, gigante, HTML no lugar de feed, 5xx, 403, redirecionamento | testes novos; o ciclo sempre termina e registra a falha por fonte |
| 1:50–2:20 | **T5 ficha por fonte** (itens/dia, % irrelevante, % velho, % duplicata, % aprovado) | tabela no relatório; `reliability` ajustado com evidência |
| 2:20–2:50 | **T2 com o lacre novo:** uma única hipótese (ex.: o termo `Aramco` em energia), definida **antes** de abrir o lacre | métrica antes e depois no lacre; promover só se o freio continuar verde |
| 2:50–3:00 | Relatório, `TREINO_LOG.md`, freio ANTES e DEPOIS, pergunta ao dono | um commit final; PR da hen vai à main com `ship.sh` pelo dono |

## 4. Critério de sucesso da rodada
- Pelo menos **uma** tarefa nova fechada com testes (T6 ou T9).
- Lacre novo com **40+ keep** e métricas estáveis (intervalo de confiança relatado).
- **Zero** commits de simples batimento.
- Freio de banco verde nas três pressões; nenhum contrato alterado.

## 5. O que o dono decide antes de começar
1. Reativar o laço de coleta do corpus (`scripts/corvo_corpus_loop.ps1`) por 3 horas, para o Codex ter dado fresco e rede.
2. Conferir 40 rótulos do Codex (a auditoria da regra 5 pede ajuda humana se a concordância ficar baixa).
3. Registrar os dois `gh secret set` para a coleta automática do GitHub alimentar o painel.

## 6. Achados da paridade de fontes (2026-11-08)
Foram acrescentadas ao catálogo `bea-releases` (dados oficiais dos EUA), `bloomberg-markets` e `ft-home`, para o CORVO cobrir o que o bot de mercado já lê. Em um ciclo de teste (27 feeds, 898 itens):
- **BEA:** 48 itens, todos descartados: 34 `below_threshold`, 13 `irrelevant`, 1 `stale` (o PIB de 29/10, passou da janela de 7 dias, o que está correto).
- **Lacuna de léxico para o Codex avaliar (T2, com lacre, uma hipótese por rodada):** "Personal Income and Outlays" (traz o PCE, a inflação que o Fed acompanha) e "International Trade in Goods and Services" ficam em **0,44**, abaixo do corte BUFFER de 0,50. São dados macro oficiais que mexem em mercado. Testar se termos como `personal income and outlays` e `international trade in goods` em `dados_macro` melhoram o recall sem subir o volume (freio verde).
- **FT:** 9 itens, todos `irrelevant` (política e opinião). Custo baixo, nada a fazer.
- **Bloomberg Markets:** 20 itens, 2 aprovados (1 HOT, 1 BUFFER).

## 7. Achados da auditoria da caixa (2026-11-09, 852 decisões da caixa em 3 h)
Mecânica correta: nenhuma URL duplicada no corpus nem no banco, todo item decidido em modo envio chegou ao banco (5 de 5), estatísticas por hora coerentes, 0 falhas de fonte em 25 ciclos. **Qualidade do portão (Hugin H2): lacunas de recall**, com exemplos reais para o T2 (uma hipótese por rodada, provada no lacre, freio verde):
| Descartado como | Título (fonte) | Provável causa |
|---|---|---|
| `irrelevant` | "Global stocks fall amid big worries over AI after Democrats' midterms triumph" (guardian-world) | queda de bolsas sem o verbo/termo do tema `mercado` |
| `irrelevant` | "Gnosis Pay breach exposes card numbers... linked crypto wallets" (coindesk) | `breach` não casa com cripto (só `hack` e `exploit`) |
| `irrelevant` | "Greece approves 10% tax on crypto gains and 15% levy on DeFi income" (coindesk) | tributação e regulação de cripto fora do léxico |
| `irrelevant` | "ECB wage tracker...", "ECB Survey of Professional Forecasters" (ecb-press) | dados macro oficiais do BCE (salários, expectativas) fora de `dados_macro` |
| `below_threshold` 0,45 | "Production suspended at Iraq's Khor Mor gas field after drone attack" (straits-times) | interrupção de produção de gás: `energia` não casa com "gas field" |
| `below_threshold` 0,48 a 0,49 | "Houthi attack damages Aramco building in Riyadh's financial district" (scmp, straits-times) | quase no corte; o evento acabou coberto por outra fonte |
Estimativa: 45 dos 718 `irrelevant` (6%) têm palavra de mercado no título; a maioria é ruído legítimo (esporte, cultura, "gold" de medalha), então o ganho é cirúrgico, não em massa.

Sem defeito do portão, mas a conhecer: 5 manchetes do mesmo acontecimento (Irã) entram como itens separados, porque o agrupamento em eventos (P1) ainda não está no banco; e 10 itens aprovados no primeiro ciclo em modo seco da caixa nunca foram enviados (efeito único da fase de testes).

