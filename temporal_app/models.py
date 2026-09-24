from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    ASK_INPUT = "ask_input"
    ASK_CONFIRMATION = "ask_confirmation"
    EXECUTE_TOOL = "execute_tool"
    FINAL_MESSAGE = "final_message"


@dataclass
class NextAction:
    type: str                                  # one of ActionType values
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    message: str
    next_action: NextAction
    # Optional list of short, clickable reply options (max 3) the frontend can
    # render as buttons; only meaningful when next_action.type == "ask_input".
    choices: Optional[List[str]] = None


@dataclass
class ChatMessage:
    role: str    # "system" | "user" | "assistant" | "tool"
    content: str
