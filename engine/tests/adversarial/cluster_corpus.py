"""Corpus de clusterização com verdade de terreno: acontecimentos reais com relatos de redações DIFERENTES, mais pares parecidos mas
DISTINTOS (outro lugar, outro dia, assunto relacionado). Sintético: mede mecânica, não desempenho real."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from corvo_engine.models import Signal

T = datetime(2026, 10, 7, 20, 0, tzinfo=timezone.utc)

# (modelos de título; {p} = lugar principal, {r} = rua/ponto, {c} = cidade); cada relato de um acontecimento usa um modelo diferente
FLOOD = ["Chuva forte alaga {r} e interdita a via em {c}", "Temporal deixa motoristas ilhados na {r}, {c}", "{c}: água toma {r} e Defesa Civil monitora risco",
         "Moradores da {r} relatam casas invadidas pela enchente em {c}", "Bombeiros resgatam famílias na {r} após chuva intensa", "Alagamento na {r} paralisa trânsito de {c}"]
ACCIDENT = ["Acidente grave na {r} em {c} deixa feridos", "Colisão entre caminhão e carro interdita a {r}, em {c}", "Batida na {r} causa congestionamento de horas em {c}",
            "{c}: capotamento na {r} mobiliza bombeiros e SAMU", "Motorista fica ferido em engavetamento na {r}", "Trânsito parado na {r} depois de acidente em {c}"]
BLACKOUT = ["Apagão atinge bairros de {c} e deixa milhares sem luz", "Moradores de {c} ficam sem energia elétrica desde a tarde", "Falha em subestação causa blecaute na {r}, em {c}",
            "Concessionária investiga queda de energia em {c}", "{c} tem semáforos apagados e comércio fechado por falta de luz", "Sem energia, hospitais de {c} acionam geradores"]
PROTEST = ["Manifestantes ocupam a {r} em {c} contra o aumento da tarifa", "Protesto na {r} bloqueia faixas e atrasa ônibus em {c}", "Ato de estudantes reúne milhares em {c}",
           "{c}: polícia acompanha passeata na {r}", "Trabalhadores fazem greve e marcham pela {r}", "Marcha toma a {r} e interdita o trânsito de {c}"]
BROAD = ["Pesquisa Datafolha mostra empate técnico no segundo turno", "Candidatos intensificam agenda no fim da campanha eleitoral", "Eleitores indecisos podem decidir o segundo turno, dizem analistas",
         "Debate na TV movimenta redes sociais antes da votação", "TSE reforça segurança das urnas para o segundo turno", "Campanha na reta final: o que esperar da apuração"]


def make(templates, ev, p, r, c, state, hours_ago, n=6, cat="WEATHER"):
    out = []
    for i in range(n):
        ts = T - timedelta(hours=hours_ago) + timedelta(minutes=7 * i)
        out.append((Signal(signal_id=f"{ev}-{i}", source_id=f"veic{(hash(ev) + i) % 97}-{i}", source_class="NEWS_REGIONAL", timestamp=ts, collected_at=ts,
                           title=templates[i % len(templates)].format(p=p, r=r, c=c), category=cat, hash=f"{ev}-{i}", state=state, city=c, geo_confidence=70), ev))
    return out


def corpus():
    pairs = []
    pairs += make(FLOOD, "flood_bh", "", "Avenida Cristiano Machado", "Belo Horizonte", "MG", 3)
    pairs += make(FLOOD, "flood_recife", "", "Avenida Boa Viagem", "Recife", "PE", 3)  # mesmo modelo, outro lugar
    pairs += make(FLOOD, "flood_bh_next_day", "", "Avenida Cristiano Machado", "Belo Horizonte", "MG", 3 + 26)  # mesmo lugar, outro dia (>12 h)
    pairs += make(ACCIDENT, "acc_betim_1", "", "BR-381", "Betim", "MG", 6)
    pairs += make(ACCIDENT, "acc_betim_2", "", "BR-381", "Betim", "MG", 1)  # mesmo lugar, mesmo dia, outro acidente (4+ h depois)
    pairs += make(BLACKOUT, "blackout_sp", "", "Zona Sul", "São Paulo", "SP", 4, cat="INFRASTRUCTURE")
    pairs += make(BLACKOUT, "blackout_campinas", "", "Centro", "Campinas", "SP", 4, cat="INFRASTRUCTURE")  # outro lugar, mesmo estado
    pairs += make(PROTEST, "protest_paulista", "", "Avenida Paulista", "São Paulo", "SP", 5, cat="PROTEST")
    pairs += make(BROAD, "elections_a", "", "", "", None, 4, cat="POLITICS")  # pauta ampla: vários relatos do MESMO assunto
    for s, _ in pairs:
        if not s.state:
            pass
    truth = {s.hash: ev for s, ev in pairs}
    signals = [s for s, _ in pairs]
    kinds = {
        tuple(sorted(("flood_bh", "flood_recife"))): "cross_location", tuple(sorted(("flood_bh", "flood_bh_next_day"))): "cross_time",
        tuple(sorted(("acc_betim_1", "acc_betim_2"))): "related_distinct", tuple(sorted(("blackout_sp", "blackout_campinas"))): "cross_location",
        tuple(sorted(("flood_bh_next_day", "flood_recife"))): "cross_location",
    }
    return signals, truth, kinds
