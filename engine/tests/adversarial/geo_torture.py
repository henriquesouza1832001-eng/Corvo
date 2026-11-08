"""Geo torture suite: casos adversariais com verdade de terreno. `false_precision_rate` é a métrica principal:
estado correto é melhor do que cidade inventada. Corpus editorial/sintético (mede mecânica; não é desempenho histórico)."""
from __future__ import annotations

CITY, STATE, NONE = "CITY", "STATE", "NONE"

# (id, manchete-base, precisão esperada, uf, cidade, grupo)
BASE = [
    ("sp-city", "Chuva forte alaga ruas em São Paulo", CITY, "SP", "São Paulo", "capital"),
    ("sampa-alias", "Sampa tem trânsito parado na Marginal", CITY, "SP", "São Paulo", "alias"),
    ("bh-alias", "BH registra temporais e queda de árvores", CITY, "MG", "Belo Horizonte", "alias"),
    ("rmbh", "Região Metropolitana de Belo Horizonte tem alerta de chuva", STATE, "MG", None, "regiao-metropolitana"),
    ("vitoria-es", "Prefeitura de Vitória decreta emergência após deslizamentos", CITY, "ES", "Vitória", "homonimo"),
    ("vitoria-conquista", "Vitória da Conquista tem chuva forte e ruas alagadas", CITY, "BA", "Vitória da Conquista", "homonimo"),
    ("vitoria-santo-antao", "Vitória de Santo Antão registra alagamento no centro", CITY, "PE", "Vitória de Santo Antão", "homonimo"),
    ("vitoria-word", "Flamengo comemora vitória sobre o rival no Maracanã", NONE, None, None, "palavra-comum"),
    ("rio-city", "Chuva forte no Rio de Janeiro causa alagamentos", CITY, "RJ", "Rio de Janeiro", "capital"),
    ("rio-grande-sul", "Rio Grande do Sul enfrenta enchente e evacuação", STATE, "RS", None, "estado"),
    ("rio-grande-city", "Cidade de Rio Grande tem ressaca e interdição do cais", CITY, "RS", "Rio Grande", "homonimo"),
    ("rio-branco", "Rio Branco registra queimadas e fumaça", CITY, "AC", "Rio Branco", "capital"),
    ("santos-port", "Porto de Santos opera com atraso por causa do nevoeiro", CITY, "SP", "Santos", "porto"),
    ("santos-club", "Santos vence o Corinthians na Vila Belmiro e sobe na tabela", NONE, None, None, "clube"),
    ("amazonas-state", "Amazonas decreta emergência por causa da seca severa", STATE, "AM", None, "estado"),
    ("amazonas-river", "Navegação no rio Amazonas é suspensa por banco de areia", NONE, None, None, "rio"),
    ("parana-state", "Paraná decreta alerta máximo para tempestades", STATE, "PR", None, "estado"),
    ("parana-river", "Nível do rio Paraná sobe e preocupa ribeirinhos", NONE, None, None, "rio"),
    ("airport-gru", "Aeroporto de Guarulhos cancela voos por causa da neblina", CITY, "SP", "Guarulhos", "aeroporto"),
    ("stadium", "Mineirão recebe jogo decisivo com ingressos esgotados", CITY, "MG", "Belo Horizonte", "estadio"),
    ("dam", "Barragem em Brumadinho tem alerta de risco e sirenes tocam", CITY, "MG", "Brumadinho", "barragem"),
    ("university", "USP cancela aulas após ameaça de bomba no campus", NONE, None, None, "universidade"),
    ("santa-maria", "Santa Maria tem chuva forte e ruas alagadas", NONE, None, None, "homonimo-ambiguo"),
    ("sao-jose", "São José registra apagão e moradores ficam sem energia", NONE, None, None, "homonimo-ambiguo"),
    ("campinas", "Campinas tem tempestade com ventos de 90 km/h", CITY, "SP", "Campinas", "cidade-sem-estado"),
    ("uberlandia", "Uberlândia registra calor recorde e baixa umidade", CITY, "MG", "Uberlândia", "cidade-sem-estado"),
    ("interior-mg", "Interior de Minas Gerais tem estradas bloqueadas por deslizamentos", STATE, "MG", None, "estado"),
    ("bairro-bh", "Moradores do bairro Venda Nova, em Belo Horizonte, ficam sem água", CITY, "MG", "Belo Horizonte", "bairro"),
    ("bairro-ambiguo", "Moradores da Boa Viagem relatam falta de luz há horas", NONE, None, None, "bairro-ambiguo"),
    ("highway", "BR-381 é interditada por acidente e fila passa de 10 km", NONE, None, None, "rodovia"),
    ("highway-city", "BR-116 é bloqueada em Guarulhos após acidente com caminhão", CITY, "SP", "Guarulhos", "rodovia"),
    ("river-name", "Rio Doce tem nível de contaminação analisado por técnicos", NONE, None, None, "rio"),
    ("salvador-city", "Salvador tem chuva intensa e deslizamentos em encostas", CITY, "BA", "Salvador", "capital"),
    ("salvador-word", "Governo promete salvador da pátria em campanha eleitoral", NONE, None, None, "palavra-comum"),
    ("palmas-word", "Plateia aplaude de pé com palmas ao final do espetáculo", NONE, None, None, "palavra-comum"),
    ("uf-suffix", "Incêndio atinge depósito em Ariquemes, RO, e bombeiros agem", CITY, "RO", "Ariquemes", "sigla-uf"),
    ("uf-only", "Operação policial termina em tiroteio (SP) segundo a PM", STATE, "SP", None, "sigla-uf"),
    ("foreign-valencia", "Valência, na Espanha, enfrenta enchente histórica", NONE, None, None, "exterior"),
    ("foreign-santarem", "Santarém, em Portugal, registra incêndio florestal", NONE, None, None, "exterior"),
    ("foreign-ap", "WASHINGTON (AP) — Governo anuncia nova rodada de sanções", NONE, None, None, "exterior"),
    ("country", "Brasil tem queda recorde de desemprego no trimestre", NONE, None, None, "pais"),
]
CONTEXTS = ["{}", "URGENTE: {}", "{} — veja imagens", "Moradores relatam: {}"]


def cases():
    out = []
    for cid, text, prec, uf, city, group in BASE:
        for k, ctx in enumerate(CONTEXTS):
            out.append({"id": f"{cid}#{k}", "base": cid, "text": ctx.format(text), "precision": prec, "uf": uf, "city": city, "group": group})
    return out


def _norm(x):
    return None if x is None else x.lower().replace("ã", "a").replace("á", "a").replace("â", "a").replace("é", "e").replace("ê", "e").replace("í", "i").replace("ó", "o").replace("ô", "o").replace("ú", "u").replace("ç", "c")


def metrics(resolver) -> dict:
    """`resolver(text) -> (uf, city) | None`. false_precision = informou CIDADE quando o certo era estado/nada, ou cidade ERRADA."""
    cs = cases()
    reported_city = fp = city_ok = state_ok = abstain = wrong_state = 0
    by_group: dict[str, dict] = {}
    bad: list[str] = []
    for c in cs:
        got = resolver(c["text"])
        g = by_group.setdefault(c["group"], {"n": 0, "false_precision": 0})
        g["n"] += 1
        if got is None:
            abstain += 1
            continue
        uf, city = got
        if city:
            reported_city += 1
            right = c["precision"] == CITY and _norm(city) == _norm(c["city"]) and uf == c["uf"]
            if right:
                city_ok += 1
            else:
                fp += 1
                g["false_precision"] += 1
                bad.append(c["id"])
        if c["precision"] in (CITY, STATE) and uf == c["uf"]:
            state_ok += 1
        elif uf and (c["precision"] == NONE or uf != c["uf"]):
            wrong_state += 1
    n = len(cs)
    return {"n": n, "city_correct": city_ok, "state_correct": state_ok, "abstentions": abstain, "reported_city": reported_city, "false_precision": fp,
            "false_precision_rate": round(fp / n, 4), "false_precision_rate_of_reported": round(fp / reported_city, 4) if reported_city else 0.0,
            "wrong_or_invented_state": wrong_state, "abstention_rate": round(abstain / n, 4), "by_group": by_group, "false_precision_ids": bad}
