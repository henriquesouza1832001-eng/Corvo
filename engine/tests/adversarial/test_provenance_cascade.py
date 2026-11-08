"""RT-008: cascatas de republicação. Uma origem factual não pode virar N confirmações; duas origens independentes não podem se fundir."""
import random
import time
from datetime import datetime, timedelta, timezone

import pytest

from pulso_engine.models import Signal
from pulso_engine.research.provenance import origin_groups, provenance

NOW = datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc)
TITLE = "Chuva forte causa alagamento e interdita a Avenida Cristiano Machado em Belo Horizonte"
SUMMARY = ("Moradores relatam água acima de um metro na região de Venda Nova, a Defesa Civil acompanha a situação e equipes da prefeitura "
           "fazem limpeza de bueiros. O trânsito segue bloqueado nos dois sentidos desde o início da tarde.")
URL = "https://jornalalfa.com.br/cidades/2026/10/04/chuva-alagamento-cristiano-machado"


def sig(i, title=TITLE, text=SUMMARY, url=None, source=None, cls="NEWS_REGIONAL", minutes=0, state="MG"):
    ts = NOW - timedelta(minutes=minutes)
    return Signal(signal_id=str(i), source_id=source or f"veiculo{i}", source_class=cls, timestamp=ts, collected_at=ts, title=title, text=text,
                  url=url, category="WEATHER", hash=f"h{i}", state=state)


def original():
    return sig(0, source="jornalalfa", url=URL, cls="NEWS_HIGH", minutes=60)


def reorder(text, rnd):
    parts = text.split(". ")
    rnd.shuffle(parts)
    return ". ".join(parts)


def mild_variant(i, rnd):
    """Variações que um republicador comum faz: prefixo, caixa, pontuação, ordem das frases, URL com rastreio ou de outro domínio."""
    title = rnd.choice([TITLE, "URGENTE: " + TITLE, TITLE.upper(), TITLE + "!", "Veja: " + TITLE + " - veja fotos",
                        "Em Belo Horizonte, chuva forte causa alagamento e interdita a Avenida Cristiano Machado"])
    text = rnd.choice([SUMMARY, reorder(SUMMARY, rnd), SUMMARY + " Leia mais no site.", SUMMARY.replace("segue bloqueado", "continua bloqueado")])
    url = rnd.choice([URL + "?utm_source=wa&utm_medium=share", URL + f"?fbclid=abc{i}", f"https://portal{i}.com.br/n/{i}-chuva-alagamento", None])
    return sig(i, title, text, url, source=f"portal{i}", minutes=rnd.randint(0, 50))


@pytest.mark.parametrize("n", [1, 5, 10, 50, 100, 1000])
def test_mild_cascade_from_one_origin_stays_one_origin(n):
    rnd = random.Random(7)
    sigs = [original()] + [mild_variant(i, rnd) for i in range(1, n + 1)]
    t0 = time.perf_counter()
    p = provenance(sigs)
    elapsed = time.perf_counter() - t0
    assert p["origin_count"] == 1 and p["independent_origin_count"] == 1
    assert p["publisher_count"] >= min(n, 2) and p["signal_count"] == n + 1
    assert p["duplicate_origin_ratio"] == round(1 - 1 / (n + 1), 4)
    assert elapsed < 20, f"{n}: {elapsed:.1f}s"  # sem explosão quadrática com 1000


def test_agency_republication_with_reworded_titles_is_one_origin():
    a = sig(1, "Alagamento interdita Avenida Cristiano Machado após chuva em BH", "Chuva forte. (Agência Brasil)", source="g1", cls="NEWS_HIGH")
    b = sig(2, "Chuva alaga Venda Nova e interdita a Cristiano Machado em BH", "Defesa Civil acompanha. Fonte: Agência Brasil", source="otempo")
    c = sig(3, "Cristiano Machado fica interditada com alagamento causado pela chuva em Belo Horizonte", "Com informações da Agência Brasil", source="uai")
    assert len(origin_groups([a, b, c])) == 1


def test_blog_copying_newspaper_and_social_copying_blog_and_social():
    paper = sig(1, TITLE, SUMMARY, URL, source="jornalalfa", cls="NEWS_HIGH", minutes=50)
    blog = sig(2, "Alagamento na Cristiano Machado: via fechada", "Segundo o JornalAlfa, a avenida está bloqueada em Belo Horizonte após a chuva forte",
               source="blogbh", minutes=40)
    social_link = sig(3, "olha isso", f"alagamento horrível {URL}", source="u1", cls="SOCIAL", minutes=30)
    social_title = sig(4, "post", "Chuva forte causa alagamento e interdita a Avenida Cristiano Machado em Belo Horizonte, olha", source="u2",
                       cls="SOCIAL", minutes=20)
    social_rt = sig(5, "RT @u2: Chuva forte causa alagamento e interdita a Avenida Cristiano Machado", "", source="u3", cls="SOCIAL", minutes=10)
    p = provenance([paper, blog, social_link, social_title, social_rt])
    assert p["origin_count"] == 1 and p["independent_origin_count"] == 1 and p["publisher_count"] == 5


def test_two_independent_reports_of_the_same_event_stay_independent():
    a = sig(1, "Alagamento na Cristiano Machado interdita a via nos dois sentidos",
            "Água cobriu a pista após a chuva da tarde e o trânsito parou, relatou a equipe do jornal.", source="jornalalfa", cls="NEWS_HIGH")
    b = sig(2, "Temporal deixa Venda Nova com ruas tomadas pela água",
            "Bombeiros atenderam chamados de moradores ilhados em Belo Horizonte; ninguém ficou ferido, segundo a corporação.", source="radiobeta")
    c = sig(3, "BH tem avenida bloqueada e bairros alagados depois de chuva intensa",
            "A prefeitura mobilizou equipes; previsão é de novas pancadas durante a noite na capital mineira.", source="portalgama")
    p = provenance([a, b, c])
    assert p["origin_count"] == 3 and p["independent_origin_count"] == 3


def test_same_title_template_for_different_places_is_not_a_copy():
    a = sig(1, "Acidente grave na BR-381 em Betim deixa dois feridos e interdita a pista", "Colisão entre carro e caminhão.", source="a", state="MG")
    b = sig(2, "Acidente grave na BR-116 em Guarulhos deixa dois feridos e interdita a pista", "Colisão entre carro e caminhão.", source="b", state="SP")
    assert len(origin_groups([a, b])) == 2


def test_same_subject_different_events_are_not_merged():
    a = sig(1, "Chuva forte causa alagamento em Belo Horizonte nesta segunda", "x", source="a")
    b = sig(2, "Prefeitura anuncia plano de drenagem para evitar alagamento no próximo verão", "y", source="b")
    assert len(origin_groups([a, b])) == 2


def test_social_origins_do_not_count_as_independent_confirmation():
    words = ["rua", "avenida", "esquina", "ponte", "viaduto", "praça", "bairro", "escola", "mercado", "posto"]
    posts = [sig(i, f"{words[i % 10]} {i} tomada pela água, vizinhos {i * 3} pedem socorro e carro {i * 7} boiando", "", source=f"user{i}", cls="SOCIAL")
             for i in range(1, 30)]
    p = provenance(posts)
    assert p["independent_origin_count"] == 0 and p["social_origin_count"] == p["origin_count"] and p["publisher_count"] == 29


def test_identical_bot_posts_collapse_to_one_origin():
    bots = [sig(i, "ATENÇÃO alagamento gravíssimo na Cristiano Machado compartilhe", "", source=f"bot{i}", cls="SOCIAL") for i in range(1, 200)]
    p = provenance(bots)
    assert p["origin_count"] == 1 and p["publisher_count"] == 199 and p["independent_origin_count"] == 0


def test_updated_article_and_changed_url_remain_one_origin():
    v1 = sig(1, TITLE, SUMMARY, URL, source="jornalalfa", minutes=90)
    v2 = sig(2, TITLE + " (atualizada)", SUMMARY + " Duas pessoas foram resgatadas.", URL + "?utm_source=x", source="jornalalfa", minutes=20)
    assert len(origin_groups([v1, v2])) == 1


def test_old_news_resurfacing_is_one_origin_not_a_new_confirmation():
    old = sig(1, TITLE, SUMMARY, URL, source="jornalalfa", minutes=60 * 24 * 40)
    again = sig(2, TITLE, SUMMARY, URL, source="blogzeta", minutes=5)
    assert len(origin_groups([old, again])) == 1  # a idade do original continua visível para quem usa o frescor


def test_provenance_of_empty_input():
    assert provenance([])["origin_count"] == 0
