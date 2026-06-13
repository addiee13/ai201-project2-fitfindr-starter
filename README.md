# FitFindr

FitFindr is a multi-tool AI agent for secondhand shopping. A user describes the thrifted piece they want, the agent searches a mock listing dataset, styles the selected listing with the user's wardrobe, and creates a short shareable fit-card caption.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```env
GROQ_API_KEY=your_key_here
```

Run tests:

```bash
pytest
```

Run the app:

```bash
python3 app.py
```

Then open the local URL printed by Gradio.

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`

Purpose: searches `data/listings.json` for secondhand listings matching the user's item description, optional size, and optional price ceiling.

Inputs:
- `description` (str): item keywords such as `"vintage graphic tee"` or `"black combat boots"`.
- `size` (str | None): optional filter such as `"M"`, `"US 8"`, or `"W28"`.
- `max_price` (float | None): optional inclusive maximum price.

Output: a relevance-sorted list of listing dictionaries. Each dictionary includes `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. If nothing matches, it returns `[]`.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Purpose: suggests an outfit using the selected listing and the user's wardrobe. It calls Groq when available and falls back to deterministic styling text if the API key is unavailable or the call fails.

Inputs:
- `new_item` (dict): the listing selected from `search_listings`.
- `wardrobe` (dict): a wardrobe object with an `items` list.

Output: a non-empty styling suggestion string. If the wardrobe is empty, the output gives general styling advice for a new user instead of assuming closet items exist.

### `create_fit_card(outfit: str, new_item: dict) -> str`

Purpose: turns the outfit suggestion and selected listing into a short social caption.

Inputs:
- `outfit` (str): output from `suggest_outfit`.
- `new_item` (dict): the selected listing.

Output: a 2-4 sentence caption string that mentions the item, price, platform, and outfit vibe. If `outfit` is blank, it returns `"Unable to create a fit card because the outfit suggestion is missing."`

## Planning Loop

`run_agent(query, wardrobe)` creates one session dictionary for the full interaction. It parses the query locally with regular expressions to extract:
- `description`
- `size`
- `max_price`

The loop then branches:

1. Call `search_listings(description, size, max_price)`.
2. Store results in `session["search_results"]`.
3. If results are empty, set `session["error"]` to a no-results message and return early.
4. If results exist, set `session["selected_item"] = session["search_results"][0]`.
5. Call `suggest_outfit(session["selected_item"], session["wardrobe"])`.
6. Store the styling text in `session["outfit_suggestion"]`.
7. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
8. Store the caption in `session["fit_card"]` and return the completed session.

The agent does not call all tools unconditionally. A failed search stops the workflow before styling or caption generation.

## State Management

State is carried through a single session dictionary:

```python
{
    "query": query,
    "parsed": {"description": ..., "size": ..., "max_price": ...},
    "search_results": [...],
    "selected_item": {...},
    "wardrobe": wardrobe,
    "outfit_suggestion": "...",
    "fit_card": "...",
    "error": None,
}
```

The exact selected listing dictionary from `search_results[0]` is passed into `suggest_outfit`, then passed again into `create_fit_card`. The user does not need to re-enter the listing between steps.

## Error Handling

`search_listings`: an impossible query such as `designer ballgown size XXS under $5` returns `[]`. The full agent responds with: `No listings matched your search. Try loosening the size, raising the max price, or using broader style terms.`

`suggest_outfit`: an empty wardrobe still returns a useful string with general advice for a new wardrobe. It does not crash or return an empty string.

`create_fit_card`: a blank outfit string returns: `Unable to create a fit card because the outfit suggestion is missing.`

Groq failures: both LLM-backed tools fall back to deterministic local text so the app remains usable during API-key, network, or provider failures.

## AI Usage

1. I used Codex with the Tool 1, Tool 2, Tool 3, and Error Handling sections from `planning.md` to implement `tools.py`. I reviewed the generated direction against the required function signatures, kept the existing `load_listings()` helper, and added local fallback behavior so tests do not require a live Groq call.

2. I used Codex with the Planning Loop, State Management, and Architecture sections from `planning.md` to implement `run_agent()` and `handle_query()`. I revised the implementation to keep the no-results branch as an early return and added tests proving downstream tools are not called when search returns no results.

## Spec Reflection

The planning spec helped most by forcing the no-results branch to be explicit before implementation. That made it clear that `suggest_outfit` should never receive an empty search result.

One implementation detail diverged from the simplest interpretation of the spec: the LLM-backed tools include deterministic fallback text. The assignment recommends Groq, and the code uses Groq when available, but the fallback makes the agent testable and usable when the local environment has no key or the provider call fails.

## Demo Checklist

For the demo video, show:
- A complete query such as `vintage graphic tee under $30`.
- The top listing panel, outfit panel, and fit-card panel filling in.
- Narration that `selected_item` is stored in session and passed into the outfit and fit-card steps.
- A failure query such as `designer ballgown size XXS under $5` showing the graceful no-results message.
