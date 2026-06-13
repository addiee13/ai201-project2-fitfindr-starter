from utils.data_loader import get_empty_wardrobe, get_example_wardrobe
from tools import create_fit_card, search_listings, suggest_outfit


def test_search_returns_relevant_results():
    results = search_listings("vintage graphic tee", size=None, max_price=30)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["price"] <= 30 for item in results)
    assert results[0]["id"] in {"lst_006", "lst_033", "lst_002", "lst_015"}


def test_search_empty_results_returns_empty_list():
    results = search_listings("designer ballgown", size="XXS", max_price=5)

    assert results == []


def test_search_price_filter_is_inclusive():
    results = search_listings("jacket", size=None, max_price=45)

    assert results
    assert all(item["price"] <= 45 for item in results)


def test_search_size_filter_matches_compound_size():
    results = search_listings("silk slip dress", size="M", max_price=30)

    assert results
    assert results[0]["id"] == "lst_013"


def test_suggest_outfit_with_example_wardrobe_returns_named_advice(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]

    suggestion = suggest_outfit(item, get_example_wardrobe())

    assert isinstance(suggestion, str)
    assert item["title"] in suggestion
    assert "Baggy straight-leg jeans" in suggestion
    assert len(suggestion.strip()) > 60


def test_suggest_outfit_with_empty_wardrobe_returns_general_advice(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]

    suggestion = suggest_outfit(item, get_empty_wardrobe())

    assert isinstance(suggestion, str)
    assert item["title"] in suggestion
    assert "new wardrobe" in suggestion.lower()
    assert len(suggestion.strip()) > 60


def test_create_fit_card_returns_caption_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    outfit = "Wear it with baggy straight-leg jeans and chunky white sneakers."

    caption = create_fit_card(outfit, item)

    assert isinstance(caption, str)
    assert item["title"] in caption
    assert f"${item['price']:.0f}" in caption
    assert item["platform"] in caption


def test_create_fit_card_with_empty_outfit_returns_error_message():
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]

    caption = create_fit_card("   ", item)

    assert caption == "Unable to create a fit card because the outfit suggestion is missing."
