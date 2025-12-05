from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Any


class WebhookPayload(BaseModel):
    action: str
    repository: dict[str, Any]
    pull_request: dict[str, Any]


app = FastAPI()


@app.get("/")
def helloWorld():
    return {"hello": "world"}


@app.post("/webhook/pr")
async def handle_pr(pr: WebhookPayload):
    print(pr)
    if pr.action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored"}

    repo_full = pr.repository["full_name"]
    pr_number = pr.pull_request["number"]

    return {
        "status": "processing",
        "data": {"repo_full": repo_full, "pr_number": pr_number},
        "complete_data": pr,
    }
