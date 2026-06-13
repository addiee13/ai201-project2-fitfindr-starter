# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset for listings that match the user's item description, optional size, and optional maximum price. It uses deterministic filtering and keyword relevance scoring so it can be tested without an LLM.

**Input parameters:**
- `description` (str): Free-text keywords describing the desired item, such as `"vintage graphic tee"` or `"black combat boots"`.
- `size` (str | None): Optional size filter from the user, such as `"M"`, `"US 8"`, or `"W28"`. If `None`, the search does not filter by size.
- `max_price` (float | None): Optional inclusive price ceiling. If `None`, the search does not filter by price.

**What it returns:**
A `list[dict]` of listing dictionaries sorted by relevance score from best to worst. Each listing contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. The function returns an empty list `[]` if no listing passes the filters and relevance check.

**What happens if it fails or returns nothing:**
The tool returns `[]` and does not raise an exception. The planning loop stores the empty result, sets `session["error"]` to a message explaining that no matching listings were found, suggests loosening size/price/style terms, and returns early before calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
Given the selected thrift listing and a wardrobe, suggests one or two complete outfit combinations. When a wardrobe has items, the suggestion should name usable wardrobe pieces; when the wardrobe is empty, it should give general styling advice for the new item instead of crashing.

**Input parameters:**
- `new_item` (dict): The listing dictionary selected from `search_listings`, including fields like `title`, `category`, `style_tags`, `colors`, `price`, and `platform`.
- `wardrobe` (dict): A wardrobe object with an `items` key containing a list of wardrobe item dictionaries. Each wardrobe item can include `id`, `name`, `category`, `colors`, `style_tags`, and `notes`.

**What it returns:**
A non-empty `str` with practical styling advice. In the normal case, it should suggest a complete outfit using the new item plus available wardrobe pieces such as bottoms, shoes, accessories, or layers. In the empty wardrobe case, it should recommend item types and styling choices the user could look for or already own.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the tool still returns useful general advice. If the LLM call fails or returns blank text, the tool returns a deterministic fallback suggestion based on the item category, style tags, and colors.

---

### Tool 3: create_fit_card

**What it does:**
Creates a short shareable caption for the selected listing and outfit idea. The result should read like a social outfit post, not a generic product description.

**Input parameters:**
- `outfit` (str): The outfit suggestion returned by `suggest_outfit`.
- `new_item` (dict): The selected listing dictionary returned by `search_listings`.

**What it returns:**
A non-empty `str` containing a 2-4 sentence fit-card caption. The caption should mention the item title, price, and platform naturally once, and should describe the outfit vibe in specific terms. Different valid inputs should produce different captions because the item details and outfit context change.

**What happens if it fails or returns nothing:**
If `outfit` is empty, whitespace-only, or missing, the tool returns the message `"Unable to create a fit card because the outfit suggestion is missing."` If the LLM call fails or returns blank text, the tool returns a deterministic fallback caption using the selected item title, price, platform, and outfit text.

---

### Additional Tools (if any)

No stretch tools are planned for the required submission. The architecture leaves room for a future price comparison tool after the required workflow is complete.

---

## Planning Loop

**How does your agent decide which tool to call next?**
The agent starts each user request by creating a fresh session dictionary. It parses the query locally with regular expressions and simple cleanup: `max_price` comes from phrases like `under $30`, `size` comes from phrases like `size M`, `in size M`, `US 8`, or waist sizes like `W28`, and `description` is the remaining cleaned query text.

Conditional flow:
1. Initialize `session = _new_session(query, wardrobe)`.
2. Parse the query into `{"description": str, "size": str | None, "max_price": float | None}` and store it in `session["parsed"]`.
3. Call `search_listings(description, size, max_price)` and store the returned list in `session["search_results"]`.
4. If `session["search_results"]` is empty, set `session["error"]` to a helpful no-results message and return the session immediately. The loop stops here and does not call `suggest_outfit` or `create_fit_card`.
5. If results exist, set `session["selected_item"] = session["search_results"][0]`.
6. Call `suggest_outfit(session["selected_item"], session["wardrobe"])` and store the returned string in `session["outfit_suggestion"]`.
7. If the outfit suggestion is blank after stripping whitespace, set `session["error"]` to a helpful message and return early.
8. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])` and store the returned string in `session["fit_card"]`.
9. Return the final session.

The loop is not a fixed unconditional sequence because the no-results branch terminates before outfit and fit-card generation. The downstream tools run only when earlier state contains the required data.

---

## State Management

**How does information from one tool get passed to the next?**
State lives in a single session dictionary created per request. The session stores the original `query`, parsed search parameters in `parsed`, the full `search_results` list, the top result in `selected_item`, the user's `wardrobe`, the generated `outfit_suggestion`, the generated `fit_card`, and any terminating `error`.

The selected item is not re-entered by the user and is not hardcoded. The exact dictionary from `session["search_results"][0]` is assigned to `session["selected_item"]`, passed into `suggest_outfit`, and then passed again into `create_fit_card`. The outfit text returned from `suggest_outfit` is stored in `session["outfit_suggestion"]` and passed directly into `create_fit_card`.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Store `[]` in `session["search_results"]`, set `session["error"]` to `"No listings matched your search. Try loosening the size, raising the max price, or using broader style terms."`, and return early without calling downstream tools. |
| suggest_outfit | Wardrobe is empty | Return general styling advice for the selected item, including suggested bottoms, shoes, layers, and accessories. The agent continues to fit-card generation using this general advice. |
| create_fit_card | Outfit input is missing or incomplete | Return `"Unable to create a fit card because the outfit suggestion is missing."` instead of raising an exception. If this occurs inside the agent, the message is stored in `session["fit_card"]` so the UI can display the failure clearly. |

---

## Architecture

```text
User query + wardrobe choice
        |
        v
Gradio handle_query()
        |
        v
run_agent(query, wardrobe)
        |
        v
Session initialized:
query, wardrobe, parsed={}, search_results=[],
selected_item=None, outfit_suggestion=None, fit_card=None, error=None
        |
        v
Parse query -> description, size, max_price
        |
        v
search_listings(description, size, max_price)
        |
        +-- results == []
        |       |
        |       v
        |   session.error = helpful no-results message
        |       |
        |       v
        |   return session early
        |
        +-- results contain listings
                |
                v
        session.search_results = results
        session.selected_item = results[0]
                |
                v
suggest_outfit(session.selected_item, session.wardrobe)
                |
                v
        session.outfit_suggestion = outfit text
                |
                v
create_fit_card(session.outfit_suggestion, session.selected_item)
                |
                v
        session.fit_card = caption
                |
                v
        return completed session
                |
                v
Gradio panels:
top listing, outfit idea, fit card
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
I will give ChatGPT/Codex the Tool 1, Tool 2, Tool 3, and Error Handling sections from this `planning.md`, plus the relevant docstrings from `tools.py`. I expect it to produce implementations for one tool at a time using the existing function signatures and `load_listings()` helper. Before trusting the output, I will inspect that `search_listings` filters by price and size before scoring, returns `[]` on no results, and does not load data manually; I will inspect that `suggest_outfit` handles empty wardrobe and LLM failure; I will inspect that `create_fit_card` guards blank outfit text. I will verify the implementations with pytest tests and direct terminal calls for each failure mode.

**Milestone 4 — Planning loop and state management:**
I will give ChatGPT/Codex the Planning Loop, State Management, Error Handling, and Architecture sections from this `planning.md`, plus the TODO comments from `agent.py` and `app.py`. I expect it to produce a `run_agent()` implementation that stores parsed values, branches after search, and passes the exact selected item and outfit suggestion through session state. I will verify the output by reading for the no-results early return, by testing that `fit_card` remains `None` on no-results queries, and by testing that the selected item is populated on successful queries. I will also verify `handle_query()` maps session fields to the three Gradio panels and handles empty user queries.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent creates a new session and parses the query. It extracts `max_price=30.0`, `size=None`, and `description="vintage graphic tee mostly wear baggy jeans chunky sneakers whats out there how would i style it"` after removing price language and filler punctuation. It calls `search_listings(description, size=None, max_price=30.0)`.

**Step 2:**
`search_listings` filters out listings above `$30`, scores the remaining listings by overlap with words and tags like `vintage`, `graphic`, and `tee`, and returns matching items sorted by relevance. A likely top result is `"Graphic Tee — 2003 Tour Bootleg Style"` or `"Vintage Band Tee — Faded Grey"`. The agent stores the full result list in `session["search_results"]` and stores the top listing dictionary in `session["selected_item"]`.

**Step 3:**
The agent calls `suggest_outfit(session["selected_item"], session["wardrobe"])`. With the example wardrobe, the tool can suggest pairing the tee with baggy straight-leg jeans, chunky white sneakers or black combat boots, and a black crossbody bag or denim jacket depending on the selected tee's vibe. The returned text is stored in `session["outfit_suggestion"]`.

**Step 4:**
The agent calls `create_fit_card(session["outfit_suggestion"], session["selected_item"])`. The tool generates a short caption that mentions the selected item, price, platform, and the outfit vibe. The returned caption is stored in `session["fit_card"]`.

**Final output to user:**
The user sees three panels: the top listing details, a complete outfit idea using the selected item and wardrobe context, and a shareable fit-card caption. If Step 1 had returned no listings, the user would instead see a no-results message explaining how to loosen the search, and the outfit and fit-card panels would stay blank.
