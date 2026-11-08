# Sensores indiretos

Além de notícias, o CORVO quer medir o **comportamento ao redor de lugares onde decisões acontecem** (bancos centrais, governos, bolsas, bases, portos). Quando uma instituição entra em modo de crise, a rotina ao redor dela muda antes de qualquer comunicado: mais movimento de comida e transporte à noite, mais voos, mais tráfego, quedas de energia ou de internet. Um sinal assim sozinho não prova nada; junto de outros sinais independentes, serve de alerta antecipado.

**Limite honesto.** O vínculo entre esses sinais e uma crise nunca é garantido. No CORVO, **um sensor indireto é sempre hipótese a corroborar com fonte independente**, nunca fato.

## O método
1. **Ponto de observação:** um lugar onde decisões acontecem (coordenadas e raio).
2. **Sensores ao redor:** locais cujo movimento muda quando a rotina do ponto muda (estabelecimentos de comida, hotéis, estações de metrô, vias de acesso).
3. **Linha de base por hora da semana:** o "normal" de uma terça às 22 h é diferente do de um sábado. Compara-se cada leitura só com o mesmo horário das semanas anteriores (mediana e desvio robusto), descontando feriado e evento local.
4. **Desvio:** quanto a leitura está fora do normal.
5. **Concordância:** um sensor sozinho não vale; vários sensores do mesmo ponto subindo juntos, mais um sinal de notícia, é que sobe a confiança.
6. **Medição:** cada alerta vira previsão registrada e depois é pontuada. Sensor que não acerta perde peso (mesmo ciclo do Sentinela: `research/sentinel.py`, `intelligence/sensor_reliability.py`).

## Mapeamento dos locais
| O que mapear | Fonte candidata | Observação |
|---|---|---|
| Estabelecimentos ao redor do ponto | OpenStreetMap via Overpass (`amenity=restaurant`/`fast_food`, `cuisine=pizza`, raio de 1 a 3 km) | licença ODbL: exige atribuição; sem custo |
| Movimento de lojas | "Movimento do momento" do Google Maps | **não tem API oficial**, e raspar fere os termos do Google. Só entra por caminho permitido (parceria ou dado licenciado) |
| Metrô e ônibus | feeds GTFS-realtime e APIs abertas das operadoras (MTA, TfL, Metrô SP etc.) | cada operadora tem termos e limites próprios |
| Trânsito | APIs oficiais de tráfego das cidades; TomTom/HERE em plano gratuito, se os termos permitirem | |
| Voos e navios | OpenSky (ADS-B), AIS agregado | mudanças de rotina em bases, portos e espaço aéreo |
| Internet e energia | Cloudflare Radar, IODA, boletins de operadoras de energia | apagões e quedas por região |
| Atenção pública | Google Trends, visualizações da Wikipedia, GDELT | já existem coletores parciais em `collectors/` |

## Regras antes de ligar qualquer fonte
Seguir `docs/COLLECTION_PROTOCOL.md`: confirmar API oficial, termos de uso, limite, custo, licença, retenção e exibição pública, e registrar em `docs/sources/SOURCES.md`. Nada de contornar login, captcha ou limite. O CORVO mede **locais e atividade agregada**, nunca pessoas, e não usa reconhecimento facial.

## Próximo passo
Catálogo versionado de pontos de observação e sensores (JSON), um mapeador que consulte o Overpass e a linha de base por hora da semana, começando pelos sensores mais fáceis de obter de forma permitida (metrô e voos).
