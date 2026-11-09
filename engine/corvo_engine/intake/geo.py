"""Geocodificador mínimo do CORVO: acha o país/hub mencionado no título e devolve um ponto para o mapa.

Propositalmente simples (tabela fixa, sem rede, sem LLM): é só para posicionar a notícia no mapa-múndi. Sem correspondência, devolve None
e a notícia não aparece no mapa (nunca se inventa localização). Vence a menção textual mais cedo no título.
"""
from __future__ import annotations

import re

# (rótulo, latitude, longitude, padrão)
_PLACES: tuple[tuple[str, float, float, str], ...] = (
    ("Letônia", 56.95, 24.11, r"latvia|latvian|riga|let[oô]nia"),
    ("Iêmen", 15.37, 44.19, r"yemen|yemeni|sanaa|sana'a|taiz|i[eê]men"),
    ("Mar Negro", 43.00, 34.00, r"black sea|mar negro"),
    ("Golfo de Omã", 23.50, 60.00, r"gulf of oman|golfo de om[aã]"),
    # Approximate regional point; this is not a city or company headquarters.
    ("Europa", 50.00, 15.00, r"\beurope\b|european countries|european markets|european union|uni[aã]o europeia"),
    ("Ucrânia", 50.45, 30.52, r"ukrain|kyiv|kiev|ucr[aâ]nia"),
    ("Rússia", 55.75, 37.62, r"russia|moscow|kremlin|putin|r[uú]ssia|moscou"),
    ("Israel/Gaza", 31.77, 35.21, r"israel|gaza|tel aviv|jerusalem|hamas|hezbollah"),
    ("Irã", 35.69, 51.39, r"\biran\b|tehran|\birã\b"),
    ("China", 39.90, 116.40, r"\bchina\b|beijing|pequim|chinese"),
    ("Taiwan", 25.03, 121.57, r"taiwan|taipei"),
    ("Coreia do Norte", 39.02, 125.75, r"north korea|pyongyang|coreia do norte"),
    ("Coreia do Sul", 37.57, 126.98, r"south korea|seoul|coreia do sul"),
    ("Japão", 35.68, 139.69, r"japan|tokyo|jap[aã]o|t[oó]quio|bank of japan|boj"),
    ("Índia", 28.61, 77.21, r"\bindia\b|new delhi|mumbai|[ií]ndia"),
    ("Paquistão", 33.69, 73.05, r"pakistan|islamabad|paquist[aã]o"),
    ("Arábia Saudita", 24.71, 46.68, r"saudi|riyadh|opec|ar[aá]bia saudita"),
    ("Turquia", 39.93, 32.86, r"\bt[uü]rkiye\b|\bankara\b|\bturquia\b"),
    ("Egito", 30.04, 31.24, r"egypt|cairo|egito"),
    ("Nigéria", 6.52, 3.38, r"nigeria|lagos|nig[eé]ria"),
    ("África do Sul", -25.75, 28.19, r"south africa|pretoria|johannesburg|[aá]frica do sul"),
    ("Venezuela", 10.48, -66.90, r"venezuela|caracas"),
    ("Argentina", -34.60, -58.38, r"argentin|buenos aires"),
    ("México", 19.43, -99.13, r"mexic|m[eé]xico"),
    ("Canadá", 45.42, -75.70, r"canada|canadian|ottawa|canad[aá]"),
    ("Brasil", -15.79, -47.88, r"brazil|brasil|bras[ií]lia|s[aã]o paulo|copom|bcb\b|planalto"),
    ("Reino Unido", 51.51, -0.13, r"\buk\b|united kingdom|britain|british|london|bank of england|londres|reino unido"),
    ("Zona do Euro", 50.11, 8.68, r"\becb\b|euro ?zone|frankfurt|lagarde|zona do euro"),
    ("Alemanha", 52.52, 13.40, r"german|berlin|alemanha|berlim"),
    ("França", 48.86, 2.35, r"france|french|paris|fran[cç]a"),
    ("Suíça", 46.95, 7.45, r"switzerland|swiss|zurich|su[ií][cç]a"),
    ("Austrália", -35.28, 149.13, r"australia|canberra|sydney|austr[aá]lia"),
    ("Cingapura", 1.35, 103.82, r"singapore|cingapura"),
    ("Hong Kong", 22.32, 114.17, r"hong kong"),
    ("Nova Zelândia", -41.29, 174.78, r"new zealand|wellington|auckland|nova zel[aâ]ndia"),
    ("Paraguai", -25.26, -57.58, r"paraguay|asunci[oó]n|paraguai"),
    ("Peru", -12.05, -77.04, r"\bperu\b|lima\b"),
    ("Chile", -33.45, -70.67, r"\bchile\b|santiago"),
    ("Colômbia", 4.71, -74.07, r"colombia|bogot[aá]|col[oô]mbia"),
    ("Cuba", 23.11, -82.37, r"\bcuba\b|havana"),
    ("Espanha", 40.42, -3.70, r"\bspain\b|madrid|espanha"),
    ("Itália", 41.90, 12.50, r"\bitaly\b|rome\b|it[aá]lia"),
    ("Polônia", 52.23, 21.01, r"poland|warsaw|pol[oô]nia"),
    ("Síria", 33.51, 36.29, r"\bsyria\b|syrian|damascus|s[ií]ria"),
    ("Líbano", 33.89, 35.50, r"lebanon|beirut|l[ií]bano"),
    ("Iraque", 33.31, 44.37, r"\biraq\b|baghdad|iraque"),
    ("Afeganistão", 34.53, 69.17, r"afghanistan|kabul|afeganist[aã]o"),
    ("Sudão", 15.50, 32.56, r"\bsudan\b|khartoum|sud[aã]o"),
    ("Etiópia", 9.03, 38.74, r"ethiopia|addis ababa|eti[oó]pia"),
    ("Indonésia", -6.21, 106.85, r"indonesia|jakarta|indon[eé]sia"),
    ("Filipinas", 14.60, 120.98, r"philippines|manila|filipinas"),
    ("Tailândia", 13.76, 100.50, r"thailand|bangkok|tail[aâ]ndia"),
    ("Vietnã", 21.03, 105.85, r"vietnam|hanoi|vietn[aã]"),
    ("Noruega", 59.91, 10.75, r"norway|oslo|noruega"),
    ("Estados Unidos", 38.90, -77.04, r"(?-i:\bUS\b)|u\.s\.|united states|washington|wall street|federal reserve|\bfed\b|pentagon|white house|nasdaq|s&p ?500|\bfomc\b|estados unidos|casa branca"),
)
_COMPILED = tuple((label, lat, lon, re.compile(pat, re.I)) for label, lat, lon, pat in _PLACES)
_EVENT_LOCATION_CUE = re.compile(
    r"\b(?:strike|attack|hit|damage|bomb|shell|fire|kill|wound|injur|pound|disable|block|deploy|send|move)"
    r"\w*\b.{0,50}\b(?:in|on|near|around|at|to)\s+(?:(?:the|a|an|de|do|da)\s+)?$",
    re.I,
)
_DIRECT_EVENT_LOCATION_CUE = re.compile(
    r"\b(?:strike|attack|hit|damage|bomb|shell|fire|kill|wound|injur|disable|block)\w*\s*$",
    re.I,
)


def _first_location(blob: str) -> tuple[int, str, float, float] | None:
    found = []
    for label, lat, lon, rx in _COMPILED:
        match = rx.search(blob)
        if match:
            found.append((match.start(), label, lat, lon, match))
    if not found:
        return None

    # When the headline names an action and its place ("strikes on Iran"),
    # prefer that place to an actor mentioned earlier ("US strikes on Iran").
    cued = [
        item
        for item in found
        if _EVENT_LOCATION_CUE.search(blob[: item[0]])
        or _DIRECT_EVENT_LOCATION_CUE.search(blob[: item[0]])
    ]
    choices = cued or found
    start, label, lat, lon, _ = min(choices, key=lambda item: item[0])
    return start, label, lat, lon


def locate(title: str, text: str = "") -> tuple[str, float, float] | None:
    """(rótulo, lat, lon) do local explícito da ação, ou da primeira menção; texto é fallback."""
    for blob in (title, text[:300]):
        first = _first_location(blob)
        if first is not None:
            _, label, lat, lon = first
            return label, lat, lon
    return None
