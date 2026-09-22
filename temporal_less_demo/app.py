"""A deliberately non-durable, one-shot LLM application for comparison demos."""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn


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


class RunRequest(BaseModel):
    scenario: str


async def run_once(scenario: str) -> dict[str, Any]:
    client = DemoLLMClient(scenario)

    try:
        raw = await client.chat("Help me plan a trip.")
        response = parse_response(raw)
    except Exception as exc:
        return {
            "status": "failed",
            "attempts": 1,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "message": "No retry occurred: this application has no Temporal workflow around the call.",
        }

    return {"status": "success", "attempts": 1, "response": response}


app = FastAPI(title="Temporal-less failure demo")
DEMO_DIR = Path(__file__).parent


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(DEMO_DIR / "index.html")


@app.post("/api/run")
async def run_demo(request: RunRequest) -> dict[str, Any]:
    if request.scenario not in {"api-error", "invalid-json", "success"}:
        return {"status": "failed", "attempts": 0, "error": "Unknown scenario"}
    return await run_once(request.scenario)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run one scenario in the terminal instead of starting the frontend server.",
    )
    parser.add_argument("--scenario", choices=("api-error", "invalid-json", "success"), default="invalid-json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    if args.cli:
        import asyncio

        result = asyncio.run(run_once(args.scenario))
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["status"] == "success" else 1)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
