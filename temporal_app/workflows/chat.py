from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal_app.activities.llm_activities import execute_tool, propose_next_action
    from temporal_app.models import ActionType


@workflow.defn
class ChatWorkflow:
    def __init__(self) -> None:
        self._history: List[Dict] = []
        self._llm_log: List[Dict] = []
        self._state: str = "starting"
        self._pending_input: Optional[str] = None
        self._pending_confirmation: Optional[bool] = None
        self._pending_tool_name: Optional[str] = None
        self._pending_tool_args: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    @workflow.signal
    async def send_user_input(self, message: str) -> None:
        self._pending_input = message

    @workflow.signal
    async def send_confirmation(self, confirmed: bool) -> None:
        self._pending_confirmation = confirmed

    # ------------------------------------------------------------------
    # Query handlers
    # ------------------------------------------------------------------

    @workflow.query
    def get_history(self) -> List[Dict]:
        return self._history

    @workflow.query
    def get_llm_log(self) -> List[Dict]:
        return self._llm_log

    @workflow.query
    def get_state(self) -> Dict:
        return {
            "state": self._state,
            "pending_tool": self._pending_tool_name,
            "pending_tool_args": self._pending_tool_args,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _append(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    @workflow.run
    async def run(self, kickoff_message: str = "[CHAT_START]", require_confirmation: bool = True) -> str:
        retry = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2))

        # Seed the conversation so the LLM always has something to respond to
        self._append("user", kickoff_message)
        self._state = "running"

        while True:
            # Ask the LLM what to do next
            response_dict = await workflow.execute_activity(
                propose_next_action,
                args=[self._history],
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=retry,
            )

            # Store LLM I/O for the debug log before consuming the response
            self._llm_log.append({
                "call": len(self._llm_log) + 1,
                "input": response_dict.pop("_llm_input", []),
                "raw_output": response_dict.pop("_llm_raw_output", ""),
                "action_type": response_dict.get("next_action", {}).get("type", ""),
            })

            message: str = response_dict["message"]
            action: Dict = response_dict["next_action"]
            action_type: str = action["type"]

            self._append("assistant", message)

            # ---- ask_input: wait for the user to type something -----------
            if action_type == ActionType.ASK_INPUT.value:
                self._state = "waiting_input"
                await workflow.wait_condition(lambda: self._pending_input is not None)
                user_text = self._pending_input
                self._pending_input = None
                self._append("user", user_text)
                self._state = "running"

            # ---- ask_confirmation / execute_tool: both require user approval ----
            elif action_type in (
                ActionType.ASK_CONFIRMATION.value,
                ActionType.EXECUTE_TOOL.value,
            ):
                tool_name = action.get("tool_name") or ""
                tool_args = action.get("tool_args") or {}
                self._pending_tool_name = tool_name
                self._pending_tool_args = tool_args
                self._state = "waiting_confirmation"

                if require_confirmation:
                    await workflow.wait_condition(lambda: self._pending_confirmation is not None)
                    confirmed = self._pending_confirmation
                    self._pending_confirmation = None
                else:
                    confirmed = True  # auto-approve when CONFIRMATION=false

                if confirmed:
                    result = await workflow.execute_activity(
                        execute_tool,
                        args=[tool_name, tool_args],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=retry,
                    )
                    # role "tool" — kept for LLM context but hidden from the UI
                    self._append("tool", f"Tool '{tool_name}' returned: {result}")
                else:
                    self._append("tool", f"User declined to run tool '{tool_name}'.")

                self._pending_tool_name = None
                self._pending_tool_args = None
                self._state = "running"

            # ---- end_chat: exit the loop ---------------------------------
            elif action_type == ActionType.END_CHAT.value:
                self._state = "ended"
                break

            # Safety: unknown action type — treat as ask_input
            else:
                workflow.logger.warning("Unknown action_type %r, falling back to ask_input", action_type)
                self._state = "waiting_input"
                await workflow.wait_condition(lambda: self._pending_input is not None)
                user_text = self._pending_input
                self._pending_input = None
                self._append("user", user_text)
                self._state = "running"

        return "Chat session ended"
