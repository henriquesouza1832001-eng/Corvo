from corvo_engine.intake.geo import locate


def test_locate_prefers_action_location_then_earliest_explicit_mention():
    cases = [
        ("Latvian farmers protest over blood grain trade with Russia", "Letônia"),
        ("Manila weighs a South China Sea case against Beijing", "Filipinas"),
        ("Canadian firms sanctioned over Iran ties", "Canadá"),
        ("Syrian troops may deploy to Yemen and Saudi Arabia", "Iêmen"),
        ("Yemen reports strikes near Sanaa", "Iêmen"),
        ("Yemeni forces advance as Houthis report casualties", "Iêmen"),
        ("Russia strikes Ukraine's power network", "Ucrânia"),
        ("Russia launches a massive strike on Kyiv", "Ucrânia"),
        ("United States carried out strikes on Iran", "Irã"),
        ("Ukraine reports damage after Russian strikes", "Ucrânia"),
        ("Japan earthquake injures people near Tokyo", "Japão"),
        ("China weighs response to Taiwan proposal", "China"),
        ("Taiwan responds to China proposal", "Taiwan"),
        ("Iran sanctions target Canadian exchange firms", "Irã"),
        ("United States blocks a cargo ship in the Gulf of Oman", "Golfo de Omã"),
        ("Cargo ship struck in the Black Sea near Ukraine", "Mar Negro"),
        ("Yemen ceasefire talks resume in Riyadh", "Iêmen"),
        ("Sanaa market hit in Yemen strikes", "Iêmen"),
        ("Riga farmers protest Russia grain trade", "Letônia"),
        ("Ankara announces new policy", "Turquia"),
        ("Türkiye central bank changes rates", "Turquia"),
        ("United Kingdom raises bank rate", "Reino Unido"),
    ]

    for title, expected in cases:
        result = locate(title)
        assert result is not None, title
        assert result[0] == expected, title


def test_locate_ignores_common_noun_turkey():
    assert locate("Turkey sandwich prices rise before Thanksgiving") is None


def test_locate_does_not_guess_ambiguous_names_or_company_headquarters():
    for title in (
        "Georgia Bulldogs report earnings after the game",
        "Jordan brand sales rise before the holidays",
        "Acme Inc. expands its office footprint",
    ):
        assert locate(title) is None, title


def test_locate_uses_body_only_when_title_has_no_match():
    assert locate("Markets digest", "Iran and Canada discuss trade") == (
        "Irã",
        35.69,
        51.39,
    )


def test_locate_prefers_title_over_body_even_if_body_mentions_earlier_table_entry():
    assert locate("Canada announces sanctions", "Iran responds to the announcement")[0] == "Canadá"
