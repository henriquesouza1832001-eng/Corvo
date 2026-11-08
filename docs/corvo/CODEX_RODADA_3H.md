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
