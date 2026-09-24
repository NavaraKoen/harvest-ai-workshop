from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    ASK_INPUT = "ask_input"
    ASK_CHOICE = "ask_choice"
    ASK_CONFIRMATION = "ask_confirmation"
    EXECUTE_TOOL = "execute_tool"
    FINAL_MESSAGE = "final_message"


@dataclass
class NextAction:
    type: str                                  # one of ActionType values
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    # Short list of clickable reply options (max 3); only used/required when
    # type == "ask_choice".
    options: Optional[List[str]] = None


@dataclass
class LLMResponse:
    message: str
    next_action: NextAction


@dataclass
class ChatMessage:
    role: str    # "system" | "user" | "assistant" | "tool"
    content: str
