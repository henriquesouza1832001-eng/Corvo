# ADR 0008 — Contexto de mercado no painel do CORVO

- **Estado:** proposto e implementado na branch `hen`; precisa de validação automatizada antes do merge.
- **Data:** 2026-11-11

## Contexto

O painel não recebia a série de preços do Engine. Isso deixava notícias e previsões sem uma visão imediata dos ativos observados, enquanto probabilidades fictícias de demonstração apareciam quando não havia feed real.

## Decisão

Adicionar `GET /api/corvo/markets` como contexto público, sem persistência: variação móvel de 24 h de BTC, ETH, SOL, BNB e XRP via Binance Spot, e variação diária entre as duas últimas observações disponíveis de USD/EUR, USD/BRL, USD/JPY, USD/GBP e USD/CNY via Frankfurter/ECB. O Worker usa o KV por cinco minutos; uma fonte indisponível não remove os dados da outra. A interface atribui as fontes e separa explicitamente cotação observada de previsão.

As probabilidades demonstrativas deixam de ser exibidas quando não há previsões reais. O painel não declara suportar índices acionários ainda. WTO e Eurostat entram no catálogo de notícias no tier 2; nenhum deles afeta a coleta padrão até validação operacional.

## Consequências e limites

- Os dados do endpoint ainda não entram no Munin nem no backtest. A coleta histórica para resolução continua no Engine.
- Câmbio é referência diária, não cotação intradiária; cripto é observação 24 h da Binance, não preço universal.
- O cache é transitório e pode responder sem dados se os provedores estiverem indisponíveis.
- O Eurostat fornece Atom; o parser real precisa de um smoke test antes de habilitar `CORVO_TIER=2`.
- Esta implementação não afirma acurácia do modelo. O Motor preditivo permanece dependente de amostra histórica e avaliação walk-forward.

## Referências

- [Binance Spot Market Data](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md)
- [Frankfurter](https://www.frankfurter.dev/)
- [WTO RSS](https://www.wto.org/english/res_e/webcas_e/rss_e.htm)
- [Eurostat RSS](https://ec.europa.eu/eurostat/en/web/rss/)
