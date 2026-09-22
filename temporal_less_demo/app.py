"""A deliberately non-durable, one-shot LLM application for comparison demos."""

import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any


class DemoAPIError(RuntimeError):
    """A simulated upstream API failure."""


@dataclass
class DemoLLMClient:
    scenario: str

    async def chat(self, prompt: str) -> str:
        if self.scenario == "api-error":
            raise DemoAPIError("upstream LLM API returned HTTP 503 Service Unavailable")
        if self.scenario == "invalid-json":
            return "I can help plan that trip, but I need your destination first."
        return json.dumps(
            {
                "message": "Where would you like to travel?",
                "next_action": {
                    "type": "ask_input",
                    "tool_name": None,
                    "tool_args": None,
                },
            }
        )


def parse_response(raw: str) -> dict[str, Any]:
    """Parse the strict response expected by the application."""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")
    if "message" not in data or "next_action" not in data:
        raise ValueError("LLM JSON must contain message and next_action")
    return data


async def run_once(scenario: str) -> int:
    client = DemoLLMClient(scenario)
    print(f"Scenario: {scenario}")
    print("Calling the LLM once...")

    try:
        raw = await client.chat("Help me plan a trip.")
        response = parse_response(raw)
    except Exception as exc:
        print(f"FAILED after 1 attempt: {type(exc).__name__}: {exc}")
        print("No retry occurred: this application has no Temporal workflow around the call.")
        return 1

    print("SUCCESS after 1 attempt:")
    print(json.dumps(response, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=("api-error", "invalid-json", "success"),
        default="invalid-json",
        help="Failure or success path to demonstrate.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run_once(args.scenario)))


if __name__ == "__main__":
    main()
