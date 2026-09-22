# Temporal-less failure demo

This is a deliberately small, one-shot LLM application with no Temporal dependency.
It demonstrates what happens when an ordinary async application receives an upstream
failure or an invalid LLM response: the operation fails after one attempt, while the
demo server stays available for the frontend.

## Run it

From the repository root:

Start the frontend:

```bash
uv run python temporal_less_demo/app.py
open http://127.0.0.1:8010
```

The page has buttons for the API failure, invalid JSON, and success paths.

For the original terminal-only behavior, use:

```bash
uv run python temporal_less_demo/app.py --cli --scenario api-error
uv run python temporal_less_demo/app.py --cli --scenario invalid-json
uv run python temporal_less_demo/app.py --cli --scenario success
```

The failure scenarios are deterministic and do not need an API key. The application
The CLI failure scenarios exit with status 1. There is no retry loop and no workflow
engine to resume the operation.

Compare that with the Temporal app: its activity retry policy can retry a failed LLM
call and keep the workflow execution durable across worker restarts.
