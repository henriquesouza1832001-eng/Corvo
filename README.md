# CORVO

**CORVO coleta as notícias do mundo, separa o que pode mexer em mercado e aprende a prever o que vem depois.** O nome vem de Hugin (pensamento) e Munin (memória), os corvos de Odin que sobrevoam os nove reinos todos os dias e voltam para contar o que viram.

- **Hugin** lê, filtra, classifica e localiza. Decide, antes de gravar qualquer coisa, se uma notícia pode mexer em cripto, ações, câmbio, juros ou commodities.
- **Munin** guarda o que importa, esquece no prazo, registra cada previsão com probabilidade, incerteza, evidências e método, e confere o resultado para saber em que tipo de previsão acerta.

O CORVO é um sistema independente: coleta, analisa e prevê. Não envia ordens e não é recomendação de investimento.

## O que ele faz hoje

1. **Lê o mundo:** 24 feeds públicos (bancos centrais, agências, imprensa, mercados e cripto) a cada 10 minutos.
2. **Filtra antes de gravar:** um portão descarta o que já viu, o que é velho, repetido ou fora do assunto. Hoje sobram cerca de 4% do que chega.
3. **Separa fato de rumor:** na dúvida é "reportagem"; só fonte oficial vira "fato".
4. **Localiza no mapa-múndi** e mostra num painel, atualizado a cada 30 segundos.
5. **Protege o banco:** o que é descartado vira só um contador e um código curto da URL (48 h); o que é gravado tem prazo (30 dias).

## O que vem a seguir: virar preditivo

As previsões ainda **não** estão publicadas. O caminho está descrito em [docs/corvo/PREDITIVO.md](docs/corvo/PREDITIVO.md): notícia, evento, hipótese de impacto, previsão pela taxa-base, conferência com o preço real e calibração. Sem amostra suficiente, o CORVO responde "dados insuficientes".

## Arquitetura

```text
 feeds públicos ──▶ coletor Python ──▶ portão (Hugin) ──▶ API (Cloudflare Worker) ──▶ Turso ──▶ painel
                    a cada 10 min      só o que importa    POST /api/corvo/ingest      banco     GET /api/corvo/feed
                                                                                    (+ cache KV)
```

Detalhes, rotas e limites de escrita: [docs/corvo/ARQUITETURA.md](docs/corvo/ARQUITETURA.md). Como o CORVO trata e guarda a notícia: [docs/corvo/TRATAMENTO_NOTICIAS.md](docs/corvo/TRATAMENTO_NOTICIAS.md). Como rodar a coleta: [docs/corvo/IMPLANTACAO.md](docs/corvo/IMPLANTACAO.md).

## Peças do repositório

| Peça | Pasta | Tecnologia |
|---|---|---|
| Painel | [apps/web](apps/web) | React + TypeScript + Vite |
| API | [apps/worker](apps/worker) | Cloudflare Worker + Hono + zod, banco Turso e cache KV |
| Motor | [engine](engine) | Python (`corvo_engine`): coleta, portão (Hugin), Munin, publicador |
| Contratos | [packages/shared](packages/shared) | TypeScript (espelho em `engine/corvo_engine/models.py`) |
| Banco | [database](database) | migrations SQL |
| Implantação | [deploy/oracle](deploy/oracle) | Docker Compose para rodar a coleta num servidor |

## O que o CORVO nunca faz

- Reconhecimento facial, rastreamento de pessoas ou perfil individual.
- Tratar alegação política como fato, recomendar voto ou prever vencedor de eleição como certeza.
- Burlar login, captcha, limites ou termos de uso de qualquer fonte.
- Publicar previsão sem probabilidade, incerteza, evidências e método.
- Enviar ordens de compra ou venda.

## Estado hoje (novembro de 2026)

- **Pronto:** coleta de 24 feeds, portão calibrado com testes, API e painel no ar sobre o Turso, bancada de prova do Munin (contas honestas, registro validado, anti-vazamento).
- **Em construção:** eventos (juntar o mesmo fato de várias fontes), hipóteses de impacto por ativo e a previsão pela taxa-base.
- **Falta:** fonte de preços para conferir previsões, sensores indiretos (movimento ao redor de lugares onde decisões acontecem) e o histórico para calibrar.
- **Herdado do projeto anterior:** parte do motor foi feita para o Brasil (estados, INMET, IBGE) e ainda precisa ser generalizada para o mundo.

## Quem contribui

[AGENTS.md](AGENTS.md) (regras para agentes e pessoas), [CONTRIBUTING.md](CONTRIBUTING.md), [CORVO_OVERVIEW.md](CORVO_OVERVIEW.md) e o treino de Hugin e Munin em [docs/corvo/HUGIN_MUNIN_TREINO.md](docs/corvo/HUGIN_MUNIN_TREINO.md).
