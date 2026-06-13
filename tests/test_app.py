from app import handle_query


def test_handle_query_empty_query_returns_panel_error():
    listing, outfit, fit_card = handle_query("   ", "Example wardrobe")

    assert "Tell me what" in listing
    assert outfit == ""
    assert fit_card == ""


def test_handle_query_success_formats_three_panels(monkeypatch):
    def fake_run_agent(query, wardrobe):
        return {
            "query": query,
            "parsed": {"description": "vintage graphic tee"},
            "search_results": [],
            "selected_item": {
                "title": "Vintage Band Tee",
                "price": 19.0,
                "platform": "depop",
                "condition": "good",
                "size": "L",
                "brand": None,
                "colors": ["grey"],
                "style_tags": ["vintage", "grunge"],
            },
            "wardrobe": wardrobe,
            "outfit_suggestion": "Pair it with baggy jeans.",
            "fit_card": "Found this tee on depop.",
            "error": None,
        }

    monkeypatch.setattr("app.run_agent", fake_run_agent)

    listing, outfit, fit_card = handle_query("vintage graphic tee", "Example wardrobe")

    assert "Vintage Band Tee" in listing
    assert "$19" in listing
    assert "depop" in listing
    assert outfit == "Pair it with baggy jeans."
    assert fit_card == "Found this tee on depop."


def test_handle_query_no_results_maps_error_to_first_panel(monkeypatch):
    def fake_run_agent(query, wardrobe):
        return {
            "query": query,
            "parsed": {},
            "search_results": [],
            "selected_item": None,
            "wardrobe": wardrobe,
            "outfit_suggestion": None,
            "fit_card": None,
            "error": "No listings matched your search.",
        }

    monkeypatch.setattr("app.run_agent", fake_run_agent)

    listing, outfit, fit_card = handle_query(
        "designer ballgown size XXS under $5",
        "Empty wardrobe (new user)",
    )

    assert listing == "No listings matched your search."
    assert outfit == ""
    assert fit_card == ""
