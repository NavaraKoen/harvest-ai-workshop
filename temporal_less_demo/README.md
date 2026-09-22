# Temporal-less failure demo

This is a deliberately small, one-shot LLM application with no Temporal dependency.
It demonstrates what happens when an ordinary async application receives an upstream
failure or an invalid LLM response: the exception reaches the caller and the process
exits after one attempt.

## Run it

From the repository root:

```bash
uv run python temporal_less_demo/app.py --scenario api-error
uv run python temporal_less_demo/app.py --scenario invalid-json
uv run python temporal_less_demo/app.py --scenario success
```

The failure scenarios are deterministic and do not need an API key. The application
prints `FAILED after 1 attempt` and exits with status 1. There is no retry loop and no
workflow engine to resume the operation.

Compare that with the Temporal app: its activity retry policy can retry a failed LLM
call and keep the workflow execution durable across worker restarts.
