from agent import run_agent
from utils.data_loader import get_example_wardrobe


def test_run_agent_happy_path_passes_selected_item_through_state(monkeypatch):
    calls = {}

    def fake_suggest_outfit(new_item, wardrobe):
        calls["suggest_item"] = new_item
        calls["wardrobe"] = wardrobe
        return f"Outfit built around {new_item['title']}."

    def fake_create_fit_card(outfit, new_item):
        calls["fit_card_outfit"] = outfit
        calls["fit_card_item"] = new_item
        return f"Caption for {new_item['title']}."

    monkeypatch.setattr("agent.suggest_outfit", fake_suggest_outfit)
    monkeypatch.setattr("agent.create_fit_card", fake_create_fit_card)

    wardrobe = get_example_wardrobe()
    session = run_agent("vintage graphic tee under $30", wardrobe)

    assert session["error"] is None
    assert session["parsed"]["max_price"] == 30.0
    assert session["parsed"]["size"] is None
    assert session["search_results"]
    assert session["selected_item"] is session["search_results"][0]
    assert calls["suggest_item"] is session["selected_item"]
    assert calls["wardrobe"] is wardrobe
    assert calls["fit_card_outfit"] == session["outfit_suggestion"]
    assert calls["fit_card_item"] is session["selected_item"]
    assert session["fit_card"] == f"Caption for {session['selected_item']['title']}."


def test_run_agent_no_results_sets_error_and_stops(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Downstream tool should not be called on no results")

    monkeypatch.setattr("agent.suggest_outfit", fail_if_called)
    monkeypatch.setattr("agent.create_fit_card", fail_if_called)

    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())

    assert session["search_results"] == []
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    assert "No listings matched" in session["error"]


def test_run_agent_parses_size_and_price():
    session = run_agent("90s track jacket in size M under $45", get_example_wardrobe())

    assert session["error"] is None
    assert session["parsed"]["size"] == "M"
    assert session["parsed"]["max_price"] == 45.0
    assert session["selected_item"]["id"] == "lst_004"
