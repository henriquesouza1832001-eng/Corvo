"""Corpus PERMANENTE de hard negatives do Sentinela (RT-003) e de positivos simulados.

Sintético e determinístico: prova mecânica e propriedades, não desempenho real. Cada negativo descreve uma situação em que ABRIR uma
investigação seria falso positivo operacional; os cenários não podem ser alterados para "passar": se um falha, a causa é do motor.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from corvo_engine.baseline import BR_TZ
from corvo_engine.intelligence.context_engine import ContextCalendar, ScheduledEvent
from corvo_engine.models import Signal
from corvo_engine.research.sentinel_eval import CONTRADICTION, NEGATIVE, POSITIVE, Scenario
from corvo_engine.simulation import SCENARIOS

T = datetime(2026, 10, 7, 21, 0, tzinfo=timezone.utc)  # quarta 18:00 em Brasília

SUBJECTS = ["prefeitura", "moradores", "bombeiros", "motoristas", "comerciantes", "estudantes", "pedestres", "ciclistas", "condutores", "vizinhos",
            "passageiros", "feirantes", "turistas", "operários", "professores", "enfermeiros", "taxistas", "síndicos", "ambulantes", "torcedores"]
ACTIONS = ["reclamam da demora", "relatam transtornos", "pedem providências", "comemoram retomada", "aguardam liberação", "improvisam desvios",
           "cobram explicações", "organizam mutirão", "registram imagens", "comentam o ocorrido", "contam a experiência", "avaliam os prejuízos"]
PLACES = ["na zona sul", "no centro", "na região norte", "perto do estádio", "na avenida principal", "no bairro vizinho", "na saída da cidade",
          "junto ao terminal", "na orla", "na praça central"]


def title(i: int, topic: str) -> str:
    """Títulos DISTINTOS por publicação (vocabulário variado), para simular veículos independentes sem virar cascata de cópias."""
    return f"{topic}: {SUBJECTS[i % 20]} {ACTIONS[(i * 7) % 12]} {PLACES[(i * 3) % 10]} ({i})"


def sig(i, minutes_before, source, cls, category, state, text=None, ttl=None, topic="Notícia"):
    ts = T - timedelta(minutes=minutes_before)
    return Signal(signal_id=f"c-{i}", source_id=source, source_class=cls, timestamp=ts, collected_at=ts + timedelta(minutes=1),
                  title=ttl or title(i, topic), text=text, category=category, hash=f"c-{i}", state=state, url=f"https://{source}.invalid/{i}")


def history(scope, category, fn, days=35, source_class="NEWS_REGIONAL"):
    """Observações horárias; `fn(hora_local) -> sinais/hora`."""
    rows, end = [], T.replace(minute=0)
    for h in range(1, 24 * days):
        t = end - timedelta(hours=h)
        n = fn(t.astimezone(BR_TZ))
        if n:
            rows.append({"scope": scope, "category": category, "source_class": source_class, "hour": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "signals": n, "sources": 4, "duplicates": 0})
    return rows


def both(category, fn, state="MG", days=35):
    """Histórico do estado E do Brasil. O nacional agrega ~10 estados ativos: o normal do BR é 10x o do estado (um jogo em MG não é
    atividade nacional anormal)."""
    return history("BR", category, lambda l: fn(l) * 10, days) + history(f"UF:{state}", category, fn, days)


def spread(n, first, last, make):
    step = (first - last) / max(1, n - 1)
    return [make(i, first - i * step) for i in range(n)]


CLASSES = ["NEWS_HIGH", "NEWS_REGIONAL", "SOCIAL", "NEWS_REGIONAL"]


def sc(name, kind, signals, rows, note, calendar=None, minutes=180, t0=None, **kw):
    """Volumes dos cenários seguem a TAXA do normal (sinais/hora x horas): um negativo com volume acima do normal não é negativo."""
    return Scenario(name, kind, signals, rows, T - timedelta(minutes=minutes), T, t0, calendar, note, tick_min=10, **kw)


# ----------------------------------------------------------------------------------------------- negativos
def normal_day():
    s = spread(8, 170, 5, lambda i, m: sig(i, m, f"fonte{i % 4}", CLASSES[i % 4], "WEATHER", "MG", topic="Previsão do tempo"))
    return sc("NORMAL_DAY", NEGATIVE, s, both("WEATHER", lambda l: 3), "volume e diversidade normais")


def normal_rain():
    s = spread(40, 175, 5, lambda i, m: sig(100 + i, m, f"chuva{i % 9}", CLASSES[i % 4], "WEATHER", "MG", topic="Chuva moderada"))
    return sc("NORMAL_RAIN", NEGATIVE, s, both("WEATHER", lambda l: 20), "estação chuvosa: 20/h é o normal desta hora")


def rush_hour():
    s = spread(18, 55, 2, lambda i, m: sig(200 + i, m, f"via{i % 9}", CLASSES[i % 4], "TRAFFIC", "SP", topic="Trânsito intenso"))
    return sc("RUSH_HOUR", NEGATIVE, s, both("TRAFFIC", lambda l: 20 if (l.weekday() < 5 and l.hour in (17, 18, 19)) else 4, "SP"), "pico de fim de tarde de dia útil (20/h, o normal das 17h-19h)", minutes=58)


def _football_calendar(scope="UF:MG", cats=("TRAFFIC", "EVENT"), mult=6.0, label="jogo no estádio"):
    return ContextCalendar(events=(ScheduledEvent(label, T - timedelta(hours=4), T + timedelta(hours=2), scope, frozenset(cats), mult),))


def football():
    s = spread(90, 175, 5, lambda i, m: sig(300 + i, m, f"jogo{i % 12}", CLASSES[i % 4], "TRAFFIC", "MG", topic="Movimento no estádio"))
    return sc("FOOTBALL", NEGATIVE, s, both("TRAFFIC", lambda l: 5), "jogo programado: trânsito/atividade esperados", calendar=_football_calendar())


def concert():
    s = spread(90, 175, 5, lambda i, m: sig(500 + i, m, f"show{i % 12}", CLASSES[i % 4], "TRAFFIC", "SP", topic="Chegada ao show"))
    return sc("CONCERT", NEGATIVE, s, both("TRAFFIC", lambda l: 5, "SP"), "show programado",
              calendar=_football_calendar("UF:SP", label="show no Allianz Parque"))


def scheduled_event():
    s = spread(120, 175, 5, lambda i, m: sig(700 + i, m, f"desfile{i % 12}", CLASSES[i % 4], "EVENT", "RJ", topic="Desfile e blocos"))
    return sc("SCHEDULED_EVENT", NEGATIVE, s, both("EVENT", lambda l: 5, "RJ"), "operação/evento programado de grande porte",
              calendar=_football_calendar("UF:RJ", ("EVENT", "TRAFFIC"), 8.0, "desfile de carnaval"))


HOLIDAY_DAY = T.astimezone(BR_TZ).date()  # a quarta-feira do teste vira feriado


def holiday():
    s = spread(75, 175, 5, lambda i, m: sig(900 + i, m, f"praia{i % 12}", CLASSES[i % 4], "TRAFFIC", "RJ", topic="Estrada para o litoral"))
    hol = lambda l: 25 if (l.weekday() == 6 or l.date() == HOLIDAY_DAY) else 5  # noqa: E731 - feriado/domingo: litoral lotado
    cal = ContextCalendar(holidays={HOLIDAY_DAY: "feriado nacional"})
    # o histórico trata o feriado de hoje como dia comum de baixa: a calendário é o que reconhece que é "dia de domingo"
    rows = both("TRAFFIC", lambda l: 25 if l.weekday() == 6 else 5, "RJ")
    del hol
    return sc("HOLIDAY", NEGATIVE, s, rows, "feriado com volume de domingo", calendar=cal)


def news_burst():
    wire = "Alagamento deixa três bairros sem energia e interdita pontes na região metropolitana segundo a Agência Brasil"
    s = spread(40, 20, 3, lambda i, m: sig(1100 + i, m, f"portal{i}", "NEWS_REGIONAL", "WEATHER", "MG", ttl=("URGENTE: " if i % 3 == 0 else "") + wire,
                                           text="Equipes trabalham no local. Agência Brasil"))
    return sc("NEWS_BURST", NEGATIVE, s, both("WEATHER", lambda l: 3), "40 veículos replicam UMA matéria de agência em 15 min")


def social_burst():
    s = spread(300, 20, 3, lambda i, m: sig(1300 + i, m, f"user{i}", "SOCIAL", "WEATHER", "MG", ttl=title(i, "post") + " alagou aqui"))
    return sc("SOCIAL_BURST", NEGATIVE, s, both("WEATHER", lambda l: 3), "300 posts de usuários, nenhum outro sensor")


def stale_sensor():
    s = spread(6, 600, 400, lambda i, m: sig(1700 + i, m, "feedparado", "NEWS_REGIONAL", "WEATHER", "MG", topic="Notícia antiga"))
    return sc("STALE_SENSOR", NEGATIVE, s, both("WEATHER", lambda l: 3), "fonte parada: nada novo há horas; ausência não é evento")


def api_outage():
    return sc("API_OUTAGE", NEGATIVE, [], both("WEATHER", lambda l: 3), "todas as fontes caídas: sem sinais; ausência não é evento")


def duplicate_storm():
    base = "Prefeitura anuncia interdição de ponte por risco estrutural e desvia o trânsito na região central da cidade"
    s = spread(200, 25, 2, lambda i, m: sig(1800 + i, m, f"copia{i % 40}", "NEWS_REGIONAL", "INFRASTRUCTURE", "SP", ttl=base, text="Texto idêntico da assessoria."))
    return sc("DUPLICATE_STORM", NEGATIVE, s, both("INFRASTRUCTURE", lambda l: 3, "SP"), "200 cópias da mesma matéria por 40 veículos")


def geo_ambiguity():
    states = ["ES", "BA", "PE"]
    s = spread(9, 40, 5, lambda i, m: sig(2100 + i, m, f"vit{i}", CLASSES[i % 4], "WEATHER", states[i % 3], topic="Chuva em Vitória"))
    rows = [r for st in states for r in both("WEATHER", lambda l: 6, st)]
    return sc("GEO_AMBIGUITY", NEGATIVE, s, rows, "'Vitória' (ES), 'Vitória da Conquista' (BA) e 'Vitória de Santo Antão' (PE): volume normal por UF")


def viral_repost():
    s = spread(300, 20, 3, lambda i, m: sig(2300 + i, m, f"rt{i}", "SOCIAL", "WEATHER", "MG", ttl="RT @alguem: ALAGAMENTO gravíssimo na avenida, compartilhe!"))
    return sc("VIRAL_REPOST", NEGATIVE, s, both("WEATHER", lambda l: 3), "um post repostado 300 vezes")


def old_news_resurface():
    old = "Barragem passa por vistoria e moradores seguem em alerta após rompimento de 2019 na região mineradora de Minas Gerais"
    s = spread(30, 25, 2, lambda i, m: sig(2700 + i, m, f"ressurge{i}", "NEWS_REGIONAL", "INFRASTRUCTURE", "MG", ttl=old, text="Reportagem publicada originalmente em 2019."))
    return sc("OLD_NEWS_RESURFACE", NEGATIVE, s, both("INFRASTRUCTURE", lambda l: 3), "matéria antiga republicada por 30 veículos")


# ----------------------------------------------------------------------------------------------- contradições (investigar é aceitável)
def official_denial():
    rumor = spread(18, 30, 6, lambda i, m: sig(3000 + i, m, f"imp{i}", CLASSES[i % 4], "INFRASTRUCTURE", "MG", topic="Rumor de rompimento de barragem"))
    denial = [sig(3100, 4, "defesa-civil-mg", "OFFICIAL", "INFRASTRUCTURE", "MG", ttl="Defesa Civil nega rompimento de barragem: sem risco, não há evacuação",
                  text="Defesa Civil: não há rompimento, situação normal.")]
    return sc("OFFICIAL_DENIAL", CONTRADICTION, rumor + denial, both("INFRASTRUCTURE", lambda l: 2), "boato de rompimento e negativa oficial")


def contradictory_sensors():
    a = sig(3200, 20, "radarmet", "OFFICIAL", "WEATHER", "MG", ttl="Radar não indica chuva sobre a capital nas próximas horas", text="Sem precipitação.")
    social = spread(20, 25, 5, lambda i, m: sig(3300 + i, m, f"user{i}", "SOCIAL", "WEATHER", "MG", ttl=title(i, "post") + " chuva forte alagando"))
    return sc("CONTRADICTORY_SENSORS", CONTRADICTION, [a] + social, both("WEATHER", lambda l: 3), "radar sem chuva x relatos de chuva forte")


# ----------------------------------------------------------------------------------------------- positivos
def positives():
    out = []
    for name, f in SCENARIOS.items():
        if name == "normal_day":
            continue
        s = f()
        out.append(Scenario(name.upper(), POSITIVE, s.signals, s.obs_rows, s.t0 - timedelta(minutes=120), s.t0 + timedelta(minutes=30), s.t0, None, s.note, tick_min=10))
    return out


def football_with_real_incident():
    """Jogo programado MAIS um colapso real: o excesso sobre o normal ajustado ainda é detectado (contexto explica, não esconde)."""
    s = spread(700, 25, 2, lambda i, m: sig(4000 + i, m, f"colapso{i % 40}", CLASSES[i % 4], "TRAFFIC", "MG", topic="Colapso no entorno do estádio"))
    return Scenario("FOOTBALL_REAL_INCIDENT", POSITIVE, s, both("TRAFFIC", lambda l: 5), T - timedelta(minutes=60), T, T - timedelta(minutes=2), _football_calendar(),
                    "evento programado + volume muito acima do esperado do evento", tick_min=10)


NEGATIVES = [normal_day, normal_rain, rush_hour, football, concert, holiday, news_burst, social_burst, stale_sensor, api_outage, duplicate_storm,
             geo_ambiguity, scheduled_event, viral_repost, old_news_resurface]
CONTRADICTIONS = [official_denial, contradictory_sensors]
