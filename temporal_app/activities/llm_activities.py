import json
import os
import re
from dataclasses import asdict
from typing import Any, Dict, List

from temporalio import activity
from temporalio.exceptions import ApplicationError

from llm import Message, create_llm
from temporal_app.models import ActionType, LLMResponse, NextAction

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are TravelBot, an expert AI travel agent. Your job is to help users plan and book a trip \
in a friendly, step-by-step conversation.

CRITICAL: You MUST respond with ONLY a single valid JSON object — no markdown fences, \
no prose before or after.

Required JSON format:
{{
  "message": "<your conversational reply to show the user>",
  "next_action": {{
    "type": "<action_type>",
    "tool_name": null,
    "tool_args": null
  }}
}}

Allowed values for "type":
- "ask_input"        — ask the user to reply (use this for normal conversation). This should always end with a question.
- "ask_confirmation" — you want to run a tool but need the user's approval first; \
set tool_name and tool_args
- "execute_tool"     — run the tool immediately (no confirmation needed); \
set tool_name and tool_args
- "end_chat"         — the booking is complete and the conversation should end

Available tools:
{tools}

When using "ask_confirmation" or "execute_tool" you MUST supply:
- "tool_name": exact name from the tool list
- "tool_args": object with ALL required parameters for that tool

Conversation flow you MUST follow:
1. Greet the user warmly as TravelBot and ask which city they want to travel to and in which month.
2. Once you have destination and month, also ask for the departure city if not yet known.
3. Use execute_tool with search_flights to find available flights; present the top 3 options clearly.
4. Ask the user which flight they prefer (ask_input).
5. Use execute_tool with select_hotel to find hotels; present the top 3 options.
6. Ask the user which hotel they prefer and for their full name for the booking (ask_input).
7. Use ask_confirmation with book_flight to confirm all details before booking.
8. After booking, congratulate the user and use end_chat.

Examples
--------
First message (history is empty — always start here):
{{"message": "✈ Welcome to TravelBot! I\'m here to help you plan your perfect trip. \
Where would you like to travel, and which month are you thinking of?", \
"next_action": {{"type": "ask_input", "tool_name": null, "tool_args": null}}}}

Asking confirmation before booking:
{{"message": "Ready to book! Flight KL423 (€189) + Hotel Barcelona Central (€120/night) \
for Anna Smith. Shall I confirm?", \
"next_action": {{"type": "ask_confirmation", "tool_name": "book_flight", \
"tool_args": {{"flight_id": "KL423", "passenger_name": "Anna Smith", \
"origin": "Amsterdam", "destination": "Barcelona", "month": "July", \
"hotel_name": "Hotel Barcelona Central"}}}}}}

Ending after booking:
{{"message": "🎉 All booked! Have an amazing trip to Barcelona! Goodbye.", \
"next_action": {{"type": "end_chat", "tool_name": null, "tool_args": null}}}}

Rules:
1. ONLY output valid JSON — nothing else, no markdown, no extra text.
2. ALWAYS follow the booking flow above in order.
3. When history contains a [CHAT_START] marker, respond with the greeting in example 1.
4. Keep "message" friendly, helpful and concise.
5. Always present tool results in a readable way before asking the next question.
"""


def _build_tools_description() -> str:
    from config.tools import TOOLS

    if not TOOLS:
        return "No tools are currently configured."

    lines: List[str] = []
    for tool in TOOLS.values():
        params = ", ".join(
            f"{k} ({v.get('type', 'string')}): {v.get('description', '')}"
            for k, v in tool.parameters.items()
        )
        confirmation = " [requires user confirmation]" if tool.require_confirmation else ""
        lines.append(f"- {tool.name}({params}): {tool.description}{confirmation}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON extraction / validation
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """Extract a JSON object from an LLM reply that may contain extra text."""
    text = text.strip()

    # Fast path: entire response is JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Grab the outermost {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in LLM response: {text[:300]!r}")


def _parse_llm_response(raw: str) -> LLMResponse:
    data = _extract_json(raw)

    if "message" not in data:
        raise ValueError("LLM JSON missing required 'message' field")
    if "next_action" not in data:
        raise ValueError("LLM JSON missing required 'next_action' field")

    action_data = data["next_action"]
    raw_type = action_data.get("type", "")
    valid_types = {a.value for a in ActionType}
    if raw_type not in valid_types:
        raise ValueError(
            f"Invalid next_action.type {raw_type!r}. Must be one of {sorted(valid_types)}"
        )

    return LLMResponse(
        message=data["message"],
        next_action=NextAction(
            type=raw_type,
            tool_name=action_data.get("tool_name") or None,
            tool_args=action_data.get("tool_args") or None,
        ),
    )


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

@activity.defn
async def propose_next_action(history: List[Dict]) -> Dict:
    """Ask the LLM what to do next and return a validated LLMResponse dict."""
    llm = create_llm()

    system_content = _SYSTEM_PROMPT_TEMPLATE.format(tools=_build_tools_description())
    messages = [Message(role="system", content=system_content)]

    for entry in history:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        # "tool" is not a universal role; map it to "user" with a prefix
        if role == "tool":
            role = "user"
            content = f"[Tool result] {content}"
        if role == "system":
            continue  # skip stored system entries; we inject our own above
        messages.append(Message(role=role, content=content))

    raw = await llm.chat(messages)

    if os.getenv("LOG_LLM_CALLS", "false").lower() == "true":
        activity.logger.info("LLM INPUT:\n%s", json.dumps([{"role": m.role, "content": m.content} for m in messages], indent=2))
        activity.logger.info("LLM OUTPUT:\n%s", raw)

    try:
        response = _parse_llm_response(raw)
    except (ValueError, KeyError) as exc:
        raise ApplicationError(
            f"LLM returned invalid JSON: {exc}",
            type="InvalidLLMResponse",
            non_retryable=False,  # allow retry — the model may do better next time
        ) from exc

    result = asdict(response)
    # Always include I/O so the frontend LLM Log tab can display them
    result["_llm_input"] = [{"role": m.role, "content": m.content} for m in messages]
    result["_llm_raw_output"] = raw
    return result


@activity.defn
async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Run a registered tool and return its string result."""
    from config.tools import TOOLS

    tool = TOOLS.get(tool_name)
    if tool is None:
        raise ApplicationError(
            f"Unknown tool: {tool_name!r}",
            type="UnknownTool",
            non_retryable=True,
        )
    if tool.handler is None:
        raise ApplicationError(
            f"Tool {tool_name!r} has no handler configured",
            type="NoToolHandler",
            non_retryable=True,
        )

    try:
        import inspect
        result = tool.handler(**(tool_args or {}))
        if inspect.isawaitable(result):
            result = await result
        return str(result)
    except ApplicationError:
        raise
    except Exception as exc:
        raise ApplicationError(
            f"Tool {tool_name!r} raised an error: {exc}",
            type="ToolExecutionError",
            non_retryable=False,
        ) from exc
