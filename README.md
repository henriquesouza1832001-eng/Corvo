# CORVO

**CORVO é um motor preditivo para o mundo todo.** O nome vem de Hugin (pensamento) e Munin (memória), os corvos de Odin que sobrevoam os nove reinos todos os dias e voltam para contar o que viram. Aqui, eles leem o planeta e voltam com previsões.

A ideia é prever **quase qualquer coisa que se possa medir**: política, catástrofes, conflitos, economia, câmbio, ações, cripto, commodities, energia e o que mais tiver sinal. Toda previsão sai com **probabilidade, incerteza, evidências e método**, e depois é conferida contra o que aconteceu de verdade.

> O CORVO usa notícias como um sensor entre muitos, ao lado de metrô, trânsito, voos, energia, internet e atenção pública: sinais indiretos que mudam **antes** da manchete. Como isso funciona e seus limites: [docs/corvo/SENSORES.md](docs/corvo/SENSORES.md). Como a notícia é tratada e armazenada: [docs/corvo/TRATAMENTO_NOTICIAS.md](docs/corvo/TRATAMENTO_NOTICIAS.md).

## O que o CORVO faz

1. **Lê o mundo:** notícias de todos os países, comunicados oficiais, calendários econômicos e sensores indiretos.
2. **Filtra antes de gravar:** um portão de admissão descarta duplicata, notícia velha, assunto irrelevante e excesso por fonte, para proteger o banco e deixar só o que importa.
3. **Separa fato de rumor:** na dúvida é "reportagem"; só fonte oficial vira "fato". Alegação não é fato.
4. **Descobre o que o acontecimento toca:** juntar as matérias do mesmo fato e ligar a ativos (BTC, dólar, ouro, petróleo, índices).
5. **Prevê com honestidade:** sem histórico suficiente, diz que não sabe. Toda previsão é registrada e pontuada (Brier), e o histórico de acertos calibra as próximas.
6. **Mostra num painel:** feed tratado, funil do portão e previsões, atualizado a cada 30 segundos.

O CORVO **não envia ordens de compra ou venda** e não é recomendação de investimento. As decisões de trade ficam com o [MNEME](https://github.com/th1agx/MNEME), que mede cada resultado em simulado antes de qualquer dinheiro real.

## Arquitetura

```text
 MNEME / coletores            ORACLE (base e cérebro)                   CLOUDFLARE (só o painel)
 notícias, sensores  ───────▶ portão de admissão → motor de previsão ──▶ corvo-api (D1 + KV) ──▶ corvo-web
                              histórico grande, calibração              POST /api/corvo/ingest    GET /api/corvo/feed
```

- **Oracle:** coleta, decide e guarda o histórico (roda ao lado do MNEME, [docs/corvo/MNEME_INTEGRACAO.md](docs/corvo/MNEME_INTEGRACAO.md)).
- **Cloudflare:** guarda e exibe só o que o painel precisa, no plano gratuito (D1 de 100 mil linhas por dia, KV de cache).
- Detalhes e rotas: [docs/corvo/ARQUITETURA.md](docs/corvo/ARQUITETURA.md).

## Peças do repositório

| Peça | Pasta | Tecnologia |
|---|---|---|
| Painel | [apps/web](apps/web) | React + TypeScript + Vite |
| API | [apps/worker](apps/worker) | Cloudflare Worker + Hono + zod, D1 e KV |
| Motor | [engine](engine) | Python (`corvo_engine`): portão, publicador, sentinela, previsão |
| Contratos | [packages/shared](packages/shared) | TypeScript (espelho em `engine/corvo_engine/models.py`) |
| Banco | [database](database) | migrations SQL do D1 |
| Implantação no Oracle | [deploy/oracle](deploy/oracle) | Docker Compose |

## O que o CORVO nunca faz

- Reconhecimento facial, rastreamento de pessoas ou perfil individual.
- Tratar alegação política como fato, recomendar voto ou prever vencedor de eleição como certeza.
- Burlar login, captcha, limites ou termos de uso de qualquer fonte.
- Publicar previsão sem probabilidade, incerteza, evidências e método.

## Estado hoje (novembro de 2026)

- **Pronto:** coleta global de 24 feeds (agências, bancos centrais, mercados, cripto), portão de admissão com testes, API `corvo-api` e painel `corvo-web` no ar, publicador do lado do Oracle, arquivos de implantação.
- **Painel:** mostra dados de demonstração (avisa na tela) até chegar o primeiro lote real do Oracle.
- **Herdado do Pulso:** o motor de eventos, anomalia, Sentinela e previsão foi feito para o Brasil (UFs, INMET, IBGE). A generalização para o mundo é o próximo grande passo.
- **Falta:** fontes globais documentadas, impacto por ativo, previsões reais publicadas, catálogo de âncoras e sensores indiretos, e o adaptador do lado do MNEME.

Documentação para quem contribui: [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CORVO_OVERVIEW.md](CORVO_OVERVIEW.md).
