# Relatório da noite — AAAA-MM-DD

> Copie este arquivo para `RELATORIO_NOITE_<data>.md` e preencha. Seja honesto: o que não melhorou vale tanto quanto o que melhorou.

**Agente:** codex-noite · **Início:** __:__ · **Fim:** __:__ · **Commit inicial:** `________` · **Commit final:** `________`

## 1. Resumo para o dono (no máximo 10 linhas)
-
-

## 2. Condições da noite
| Item | Valor |
|---|---|
| Rede disponível? (T0 e T10 dependem dela) | sim / não |
| Ciclos de coleta no corpus | |
| Itens únicos no corpus / fontes | / |
| Rótulos feitos (ajuste / lacrado) | / |
| Semente da amostra | 20261108 |
| Feeds com falha no período | |

## 3. Hugin
### 3.1 Métricas, antes e depois (ponderadas)
| Métrica | Meta | Antes (ajuste) | Antes (**lacrado**) | Depois (ajuste) | Depois (**lacrado**) |
|---|---|---|---|---|---|
| Precisão do HOT | ≥ 0,85 | | | | |
| Recall do keep | ≥ 0,90 | | | | |
| Keep descartado (pior erro) | mínimo | | | | |
| Drop gravado | mínimo | | | | |
| Keep entre as gravadas | ≥ 0,85 | | | | |
| HOT entre os aceitos | ≤ 0,25 | | | | |
| Fusões erradas (dedup) | ≤ 2% | | | | |
| Cobertura do mapa / acerto do local | ≥ 85% / ≥ 95% | | | | |
| Rumor ou opinião marcados como fato | 0 | | | | |
| Linhas de banco por dia (projeção; com 5× volume) | ≤ 5 mil; ≤ 25 mil | | | | |

### 3.2 Mudanças (uma por linha)
| # | Tarefa | O que mudou | Efeito no lacrado | Commit |
|---|---|---|---|---|
| 1 | | | | |

### 3.3 O que piorou ou foi revertido
-

### 3.4 Dez exemplos que o portão ainda erra
| # | Título | Rótulo | O que o portão fez | Por quê |
|---|---|---|---|---|
| 1 | | | | |

### 3.5 Auditoria do que já está no banco (T0)
| Rótulo | Qtde | % |
|---|---|---|
| keep | | |
| marginal | | |
| drop | | |

### 3.6 Fichas das fontes (T5)
| Fonte | Itens/dia | % irrelevante | % velho | % duplicata | % aprovado | Publica primeiro (%) | Recomendação |
|---|---|---|---|---|---|---|---|

## 4. Munin
### 4.1 Invariantes e bancada
- Testes novos e o que cobrem:
- Cenários simulados rodados (`corvo_munin_eval.py`):
### 4.2 Propostas para aprovação do dono (sem mudar contrato)
- **M3 — tema para ativos** (tabela proposta):
- **M6 — regra de aprendizado** (amostra mínima, correção de múltiplos testes, divisão temporal):

## 5. Fontes
| Fonte candidata | URL verificada? | Termos | Ligada? (`enabled`) | Linha em SOURCES.md |
|---|---|---|---|---|

## 6. Proposta de agrupamento por acontecimento (T11, só desenho)
- Quantos aprovados são o mesmo fato em fontes diferentes:
- Economia estimada de linhas:
- Desenho de contrato (para o dono decidir):

## 7. Perguntas para o dono
1.

## 8. Próximos passos sugeridos
1.

## 9. Conferência final
- [ ] Testes verdes (`tests/test_intake_gate.py`, `test_oracle_publisher.py`, `test_collect_runner.py`, `test_munin.py`, `test_corvo_bench.py`)
- [ ] `sh scripts/gitcrypt_check.sh` ok; nenhum corpus, rótulo, `.sqlite` ou segredo no commit
- [ ] Trava do quadro liberada (`lock release`) e reservas liberadas (`unclaim`)
- [ ] Nada fora das pastas permitidas foi editado
