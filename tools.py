"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "i",
    "im",
    "in",
    "it",
    "looking",
    "mostly",
    "out",
    "the",
    "there",
    "to",
    "under",
    "wear",
    "what",
    "whats",
    "with",
    "would",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _chat_completion(messages: list[dict], temperature: float = 0.7) -> str | None:
    """Return Groq text, or None if the call cannot complete locally."""
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=temperature,
            max_tokens=300,
        )
        content = response.choices[0].message.content
    except Exception:
        return None

    if not content or not content.strip():
        return None
    return content.strip()


def _normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _keyword_tokens(description: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", description.lower())
    return [token for token in tokens if token not in _STOP_WORDS and len(token) > 1]


def _listing_search_text(listing: dict) -> str:
    parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        listing.get("size", ""),
        listing.get("condition", ""),
        listing.get("brand") or "",
        listing.get("platform", ""),
        " ".join(listing.get("style_tags", [])),
        " ".join(listing.get("colors", [])),
    ]
    return _normalize_text(" ".join(parts))


def _size_matches(listing_size: str, requested_size: str | None) -> bool:
    if not requested_size:
        return True

    requested = _normalize_text(requested_size)
    available = _normalize_text(listing_size)
    if requested == available or requested in available:
        return True

    requested_tokens = set(requested.split())
    available_tokens = set(available.split())
    return bool(requested_tokens & available_tokens)


def _score_listing(listing: dict, description: str) -> int:
    search_text = _listing_search_text(listing)
    normalized_description = _normalize_text(description)
    tokens = _keyword_tokens(description)
    score = 0

    if normalized_description and normalized_description in search_text:
        score += 6

    title_text = _normalize_text(listing.get("title", ""))
    tag_text = _normalize_text(" ".join(listing.get("style_tags", [])))
    color_text = _normalize_text(" ".join(listing.get("colors", [])))

    for token in tokens:
        if token in search_text:
            score += 1
        if token in title_text:
            score += 2
        if token in tag_text:
            score += 2
        if token in color_text:
            score += 1

    return score


def _format_item_summary(item: dict) -> str:
    brand = item.get("brand") or "unbranded"
    tags = ", ".join(item.get("style_tags", [])[:4])
    colors = ", ".join(item.get("colors", []))
    return (
        f"{item.get('title')} ({brand}) - {item.get('category')}, "
        f"size {item.get('size')}, ${item.get('price'):.0f} on "
        f"{item.get('platform')}; colors: {colors}; tags: {tags}"
    )


def _fallback_outfit(new_item: dict, wardrobe: dict) -> str:
    title = new_item.get("title", "this find")
    colors = ", ".join(new_item.get("colors", [])) or "its main colors"
    tags = ", ".join(new_item.get("style_tags", [])[:3]) or "secondhand"
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []

    if not wardrobe_items:
        return (
            f"For a new wardrobe, build around {title} by pairing the {colors} tones "
            f"with relaxed denim or simple trousers, then add sneakers or boots that "
            f"match the {tags} vibe. Keep accessories simple so the thrifted piece "
            "stays the focus."
        )

    bottoms = [item for item in wardrobe_items if item.get("category") == "bottoms"]
    shoes = [item for item in wardrobe_items if item.get("category") == "shoes"]
    outerwear = [item for item in wardrobe_items if item.get("category") == "outerwear"]
    accessories = [
        item for item in wardrobe_items if item.get("category") == "accessories"
    ]

    bottom = bottoms[0]["name"] if bottoms else "your most relaxed bottoms"
    shoe = shoes[0]["name"] if shoes else "a comfortable everyday shoe"
    layer = outerwear[0]["name"] if outerwear else "a light layer"
    accessory = accessories[0]["name"] if accessories else "a simple bag or belt"

    return (
        f"Style {title} with {bottom} and {shoe} for an easy {tags} outfit. "
        f"Add {layer} if you want more shape, then finish with {accessory}. "
        "Keep the proportions relaxed: let one piece fit oversized and keep the "
        "rest clean so the look feels intentional."
    )


def _fallback_fit_card(outfit: str, new_item: dict) -> str:
    title = new_item.get("title", "this thrifted piece")
    price = new_item.get("price", 0)
    platform = new_item.get("platform", "a resale app")
    vibe = ", ".join(new_item.get("style_tags", [])[:2]) or "secondhand"
    return (
        f"Found {title} on {platform} for ${price:.0f}, and it pulls the whole "
        f"{vibe} mood together. {outfit.strip()} Easy thrift win with enough "
        "texture to look styled without trying too hard."
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    scored_results: list[tuple[int, dict]] = []

    for listing in listings:
        if max_price is not None and float(listing.get("price", 0)) > max_price:
            continue
        if not _size_matches(str(listing.get("size", "")), size):
            continue

        score = _score_listing(listing, description)
        if score > 0:
            scored_results.append((score, listing))

    scored_results.sort(key=lambda result: (-result[0], result[1].get("price", 0)))
    return [listing for _, listing in scored_results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    item_summary = _format_item_summary(new_item)

    if wardrobe_items:
        wardrobe_summary = "\n".join(
            f"- {item['name']} ({item['category']}; "
            f"colors: {', '.join(item.get('colors', []))}; "
            f"tags: {', '.join(item.get('style_tags', []))}; "
            f"notes: {item.get('notes') or 'none'})"
            for item in wardrobe_items
        )
        user_prompt = (
            "Suggest one complete outfit using this thrift listing and named "
            "pieces from the wardrobe.\n\n"
            f"New item: {item_summary}\n\n"
            f"Wardrobe:\n{wardrobe_summary}\n\n"
            "Return 3-5 practical sentences. Name the exact wardrobe pieces."
        )
    else:
        user_prompt = (
            "The user has a new or empty wardrobe. Suggest general styling "
            "ideas for this thrift listing without pretending they own items.\n\n"
            f"New item: {item_summary}\n\n"
            "Return 3-5 practical sentences with item types to pair it with."
        )

    content = _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a practical secondhand fashion stylist. "
                    "Be specific, concise, and wearable."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
    )
    return content or _fallback_outfit(new_item, wardrobe)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Unable to create a fit card because the outfit suggestion is missing."

    item_summary = _format_item_summary(new_item)
    content = _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You write casual social captions for thrifted outfits. "
                    "Do not sound like a product listing."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write a 2-4 sentence fit card caption. Mention the item "
                    "title, price, and platform naturally once each. Capture "
                    "the outfit vibe in specific terms.\n\n"
                    f"New item: {item_summary}\n\n"
                    f"Outfit: {outfit.strip()}"
                ),
            },
        ],
        temperature=0.9,
    )
    return content or _fallback_fit_card(outfit, new_item)
