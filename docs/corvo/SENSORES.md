# Sensores indiretos: como funciona o Pizza Index e como o CORVO aprende com ele

## O que o Pizza Index realmente é
Uma ideia de inteligência de fontes abertas: quando uma instituição entra em modo de crise, o comportamento ao redor dela muda antes de qualquer comunicado. No caso clássico, funcionários do Pentágono trabalham até tarde e pedem comida, e as pizzarias próximas ficam mais movimentadas do que o normal para aquele dia e hora. Os painéis atuais, como o [PizzINT](https://www.pizzint.watch/about), acompanham a movimentação de pizzarias perto do Pentágono em tempo real.

O dado vem do "movimento do momento" (Popular Times / Live Visit) do Google Maps para um punhado de estabelecimentos ([Modern Diplomacy](https://moderndiplomacy.eu/2025/07/23/the-pentagon-pizza-index-as-a-case-study-in-low%e2%80%91tech-osint/), [Gigazine](https://wbgsv0a.gigazine.net/gsc_news/en/20250801-pentagon-pizza-index)). Não encontrei fórmula pública do placar nem a lista exata de locais do PizzINT, então o CORVO não vai copiar fórmula: vai aplicar o método geral e medir.

**Limites honestos.** O vínculo entre pizza e crise nunca foi provado; os críticos apontam duas suposições frágeis (que o pessoal pede pizza em crises e que o pico nas lojas vem disso) e o Pentágono nega relação. Origens históricas contadas por aí são pouco documentadas. Por isso, no CORVO, **um sensor indireto é sempre hipótese a corroborar com fonte independente**, nunca fato.

## O método, em passos que o CORVO pode repetir
1. **Âncora:** um lugar onde decisões acontecem (Pentágono, Casa Branca, Planalto, Fed, B3, Wall Street, Kremlin, parlamentos, grandes portos e aeroportos).
2. **Sensores ao redor:** locais que mudam de movimento quando a âncora muda de rotina (comida de entrega, hotéis, estações de metrô, estacionamentos, vias de acesso).
3. **Linha de base por hora da semana:** o "normal" de uma terça às 22 h é diferente do de um sábado. Compara-se cada leitura só com o mesmo horário das semanas anteriores (mediana e desvio robusto), nunca com a média geral.
4. **Desvio:** quanto a leitura está fora do normal (z robusto), com feriado e evento local descontados.
5. **Concordância:** um sensor sozinho não vale; vários sensores da mesma âncora subindo juntos, mais um sinal de notícia, é que sobe a confiança.
6. **Medição:** cada alerta vira previsão registrada ("há mudança de rotina em X") e depois é pontuada. Sensor que não acerta perde peso. É o mesmo ciclo do Sentinela já existente (`research/sentinel.py`, `intelligence/sensor_reliability.py`).

## Mapeamento dos locais (pizzarias, trânsito, metrô e afins)
| O que mapear | Fonte candidata | Observação |
|---|---|---|
| Estabelecimentos ao redor da âncora | OpenStreetMap via Overpass (`amenity=restaurant`/`fast_food`, `cuisine=pizza`, raio de 1 a 3 km) | licença ODbL: exige atribuição; sem custo |
| Movimento de lojas | Google Popular Times | **não tem API oficial**, e raspar fere os termos do Google. Só entra se houver caminho permitido (parceria ou dado licenciado). Alternativas: dados de delivery se houver API aberta, ou ficar sem esse sensor |
| Metrô e ônibus | feeds GTFS-realtime e APIs abertas das operadoras (MTA, TfL, Metrô SP etc.) | cada operadora tem termos e limites próprios; documentar em `docs/sources/SOURCES.md` |
| Trânsito | APIs oficiais de tráfego das cidades; TomTom/HERE em plano gratuito, se os termos permitirem | |
| Voos e navios | OpenSky (ADS-B), AIS agregado | mudanças de rotina em bases, portos e espaço aéreo |
| Internet e energia | Cloudflare Radar, IODA, boletins de operadoras de energia | apagões e quedas por região |
| Atenção pública | Google Trends, visualizações da Wikipedia, GDELT | já existem coletores parciais em `collectors/` |

## Regras antes de ligar qualquer fonte
Seguir `docs/COLLECTION_PROTOCOL.md`: confirmar API oficial, termos de uso, limite, custo, licença, retenção e exibição pública, e registrar em `docs/sources/SOURCES.md`. Nada de contornar login, captcha ou limite. O CORVO mede **locais e atividade agregada**, nunca pessoas, e não usa reconhecimento facial.

## Primeiro passo prático (sem depender de Google)
Montar o **catálogo de âncoras e sensores** em JSON (âncora, coordenadas, raio, lista de sensores com a fonte permitida) e um mapeador que consulte o Overpass, grave o catálogo versionado e calcule a linha de base por hora da semana assim que existir série temporal de algum sensor permitido (metrô e voos são os mais fáceis de começar).
