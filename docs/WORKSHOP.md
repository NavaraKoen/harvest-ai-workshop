# Harvest AI Workshop — 4-Hour Session Guide

Audience: experienced engineers, new to AI-assisted / agentic apps and Temporal.
Format: short intro talk per block, then hands-on exercises in pairs.

---

## Block 1 (45 min) — Orientation + Prompt Engineering Warm-up

### Talk (15 min)

- Walk through the architecture in the root `README.md`.
- Open `temporal_app/activities/llm_activities.py` and read `_SYSTEM_PROMPT_TEMPLATE` together.
- Explain the JSON action contract: every LLM reply must contain `message` + `next_action.type`,
  and `type` drives what the workflow does next (`ask_input`, `ask_confirmation`, `execute_tool`, `end_chat`).

### Exercise 1.1 — Reskin the prompt (30 min)

Goal: prove they understand the contract, not the code.

1. Copy `_SYSTEM_PROMPT_TEMPLATE` to a scratch file.
2. Rewrite it for a new domain, keeping the exact same JSON contract and action types:
   - Pizza ordering bot (size, toppings, delivery address → `place_order` tool)
   - IT helpdesk bot (issue category, device → `create_ticket` tool)
   - Restaurant reservation bot (date, time, party size → `book_table` tool)
3. Paste the new prompt into `_SYSTEM_PROMPT_TEMPLATE` (temporarily) and chat with it via the frontend.
   No new tools needed yet — if the model calls a tool that doesn't exist, that's fine, just observe.

**Checkpoint:** each pair demos one exchange and explains which part of their prompt controls
the flow ordering (see the numbered "Conversation flow you MUST follow" section).

---

## Block 2 (60 min) — The JSON Reliability Problem

### Talk + live demo (15 min)

- Send 5-10 chat turns back to back and point out the "LLM Log" tab in the frontend.
- Deliberately provoke a bad reply (short/ambiguous user input, or a smaller/quantized model) and show
  `_extract_json` / `_parse_llm_response` in `llm_activities.py` throwing `ValueError` → wrapped in
  `ApplicationError(non_retryable=False)` → Temporal auto-retries the activity.
- Key teaching point: **the LLM is unreliable, the system around it should not be.**

### Exercise 2.1 — Force `format: "json"` (15 min)

1. Open `llm/ollama_llm.py`.
2. Add `"format": "json"` to the `payload` dict sent to `/api/chat`.
3. Restart the worker, chat for a few turns, and note whether malformed replies still happen
   (structurally valid JSON, but can still violate your schema, e.g. wrong `type` value).

### Exercise 2.2 — Retry-with-repair loop (20 min)

Goal: when parsing fails, don't just retry blindly — tell the model what it did wrong.

1. In `propose_next_action` (`llm_activities.py`), catch the `ValueError` from `_parse_llm_response`.
2. Instead of immediately raising `ApplicationError`, append a corrective message to the local
   `messages` list, e.g.:
   ```python
   messages.append(Message(role="user", content=f"Your last reply was not valid JSON ({exc}). Reply again with ONLY the JSON object."))
   raw = await llm.chat(messages)
   response = _parse_llm_response(raw)  # retry once before giving up
   ```
3. Only raise `ApplicationError` (letting Temporal retry the whole activity) if the repair attempt also fails.

### Exercise 2.3 — Measure it (10 min)

1. Add a counter/log line whenever `_extract_json` needed a fallback path (fences stripped, or
   regex `{...}` extraction) vs. the fast path.
2. Run 10 identical conversations and compare failure rates before/after 2.1 and 2.2.
3. Discuss: what would you do differently in a paid/production model (OpenAI structured outputs,
   function calling, JSON schema validation) vs. a local quantized model?

**Checkpoint:** each pair reports their failure-rate delta and one trade-off they noticed
(latency, cost of repair round-trip, false confidence from `format: json`).

---

## Block 3 (75 min) — Temporal Concepts via This App

### Talk (15 min)

- Explain workflow-as-state-machine using `ChatWorkflow`: signals (`send_user_input`,
  `send_confirmation`), queries (`get_history`, `get_state`, `get_llm_log`), and the
  `while True` loop as durable orchestration.
- Emphasize: workflow code is replayed, so it must stay deterministic — all "risky" work
  (LLM calls, HTTP calls) lives in activities, not in the workflow function.

### Exercise 3.1 — Kill and resurrect the worker (15 min)

1. Start a chat, get to the "waiting for input" state.
2. Stop the worker process (`Ctrl+C` on `uv run worker`).
3. Confirm in the Temporal Web UI (http://localhost:8233) that the workflow is still "Running".
4. Restart the worker (`uv run worker`) and continue the chat from the frontend — it resumes
   exactly where it left off, no state lost.

**Checkpoint:** ask them to explain _why_ this works without looking at the code (event history replay).

### Exercise 3.2 — Add a `cancel_chat` signal (20 min)

1. Add `send_cancel` signal handler to `ChatWorkflow` that sets a `self._cancelled` flag.
2. In the main loop, check `self._cancelled` at the top of each iteration; if set, append a
   closing message and `break`.
3. Wire a "Cancel" button in `frontend/index.html` that calls the new signal via the API
   (add a matching endpoint in `api/main.py` if one doesn't already forward signals generically).
4. Test: start a chat, cancel mid-flow, confirm workflow state shows `ended`.

### Exercise 3.3 — Add a new action type: `ask_choice` (30 min)

Goal: extend the protocol end-to-end (prompt → models → workflow → frontend).

1. `temporal_app/models.py`: add `ASK_CHOICE = "ask_choice"` to `ActionType`.
2. `llm_activities.py`: update the system prompt to document `ask_choice` and require an
   `"options": ["...", "..."]` field alongside `tool_name`/`tool_args` (or a new field).
3. `chat.py` (workflow): handle `ActionType.ASK_CHOICE.value` similarly to `ask_input`, but
   store the offered options in workflow state so the frontend can render buttons.
4. `frontend/index.html`: render option buttons when `action_type == "ask_choice"`, and on click,
   send the choice back via the existing `send_user_input` signal (reuse it — no new signal needed).
5. Update the prompt's flow instructions to use `ask_choice` for "which flight/hotel do you prefer".

**Checkpoint:** demo a full conversation where flight/hotel selection uses buttons instead of free text.

## Block 4 (60 min) — Build Your Own Chatbot

### Setup (5 min)

Each person/pair picks a domain (reuse their Block 1 prompt if they liked it, or pick a new one):
library book reservation, expense approval, onboarding checklist bot, etc.

### Exercise 4.1 — Add a real tool (30 min)

1. Add a new endpoint in `api/services.py` (e.g. `POST /services/create-ticket`) with a fake
   in-memory implementation (mirror `search_flights`/`book_flight` patterns).
2. Add a matching `ToolDefinition` + async handler in `config/tools.py`, wired to the new endpoint.
3. Write/update the system prompt to reference the new tool by exact name and required args.
4. Set `require_confirmation=True` for anything "write"/irreversible, `False` for read-only lookups.

### Exercise 4.2 — End-to-end demo (20 min)

1. Restart worker + API, start a new chat in the frontend.
2. Walk through the full flow: greeting → info gathering → tool call → confirmation → booking/end.
3. Use the LLM Log tab to show a teammate exactly what was sent/received at each step.

### Stretch goal (if time remains)

- Pull 2-3 different local models ahead of time (e.g. `ollama pull llama3.2`, `ollama pull qwen2.5:7b`,
  `ollama pull phi3`). Keep `LLM_PROVIDER=ollama` and just change `OLLAMA_MODEL` in `.env` between runs.
- Re-run the _same_ conversation script against each model (same user inputs, same order) and compare:
  - JSON reliability (how often Block 2's repair path triggers)
  - Response quality / adherence to the flow steps in the prompt
  - Latency per turn
- Discuss: prompt engineering that works well for one model may not transfer to another —
  this is why the JSON contract + repair loop from Block 2 matters more than picking "the right model".

**Wrap-up (5 min):** each pair shows their bot for 2 minutes; discuss one prompt-engineering
lesson and one Temporal lesson they'd apply to a real production chatbot.

---

## Facilitator Notes

- Pre-pull the model on all machines beforehand: `ollama pull mistral` (large download, do this before the session).
- Have `temporal server start-dev` and the Temporal Web UI (`:8233`) open on a shared screen for Block 3 demos.
- Keep a known-good git branch/tag to reset to between exercises if someone breaks their local copy.
- Block 2 works best on a slightly weaker/quantized model — if `mistral` is too reliable, try
  a smaller model to reproduce JSON failures on demand.
