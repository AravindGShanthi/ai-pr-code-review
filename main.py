import json
import operator
from typing import Annotated, Any

from config import get_github_token, init_settings  # type: ignore
from dotenv import load_dotenv
from fastapi import FastAPI
from github import Auth, Github
from langchain.agents import create_agent
from langchain.messages import AIMessage, AnyMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

load_dotenv()

# Initialize settings at startup
init_settings()

app = FastAPI()


class WebhookPayload(BaseModel):
    action: str
    repository: dict[str, Any]
    pull_request: dict[str, Any]


class MessageState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    diffs: list[dict[str, str]] | None
    output: Any | None
    repo_full: str | None
    pr_number: int | None


def fetch_pr_files(state: MessageState) -> dict[str, list[dict[str, str]]]:
    """Fetch the pull request based on repo fullname and PR number, and return the list of diffs object."""
    auth = Auth.Token(get_github_token())
    gh = Github(auth=auth)

    repo_full = state["repo_full"]
    pr_number = state["pr_number"]

    if repo_full is None:
        raise ValueError("repo_full is required")
    if pr_number is None:
        raise ValueError("pr_number is required")

    repo = gh.get_repo(repo_full)
    pr = repo.get_pull(pr_number)

    diffs: list[dict[str, str]] = []

    for f in pr.get_files():
        diffs.append(
            {
                "filename": f.filename,
                "patch": f.patch if f.patch else "",
            }
        )

    return {"diffs": diffs}


def llm_review_node(state: MessageState) -> dict[str, Any]:
    """LLM will review the pull request diff and suggest code improvements, best practices, check coding standards, and feedbacks."""
    system_prompt = """You are a helpful coding assistant tasked with reviewing pull request diffs and suggesting code improvements, best practices, and coding standards feedback.

    Return your response as valid JSON with this exact format:
    {
        "summary": "brief summary of the review",
        "issues": [
            {
                "file": "filename.py",
                "line": 45,
                "type": "security|bug|style|improvement",
                "severity": "high|medium|low",
                "message": "description of the issue",
                "suggestion": "suggested fix or improvement"
            }
        ],
        "suggested_patch": "optional suggested code changes"
    }

    Review the provided diff and identify:
    1. Bugs or logical errors
    2. Violations of coding standards
    3. Security issues
    4. Suggestions for improvement

    EXAMPLES:

    Example 1 (Simple - Style Issue):
    Diff: @@ -5,3 +5,3 @@ x=1 y = 2
    Output:
    {
        "summary": "Minor style inconsistency found",
        "issues": [
            {
                "file": "script.py",
                "line": 5,
                "type": "style",
                "severity": "low",
                "message": "Inconsistent spacing around assignment operators",
                "suggestion": "Use consistent spacing: x = 1, y = 2"
            }
        ],
        "suggested_patch": "x = 1\\ny = 2"
    }

    Example 2 (Medium - Bug):
    Diff: @@ -10,5 +10,5 @@ def divide(a, b): return a / b
    Output:
    {
        "summary": "Missing error handling for division operation",
        "issues": [
            {
                "file": "utils.py",
                "line": 11,
                "type": "bug",
                "severity": "high",
                "message": "Division by zero not handled - will crash if b=0",
                "suggestion": "Add check: if b == 0: raise ValueError('Cannot divide by zero')"
            }
        ],
        "suggested_patch": "def divide(a, b):\\n    if b == 0:\\n        raise ValueError('Cannot divide by zero')\\n    return a / b"
    }

    Example 3 (Medium - Security):
    Diff: @@ -20,2 +20,2 @@ query = "SELECT * FROM users WHERE id=" + user_input
    Output:
    {
        "summary": "SQL injection vulnerability detected",
        "issues": [
            {
                "file": "database.py",
                "line": 21,
                "type": "security",
                "severity": "high",
                "message": "SQL injection risk: string concatenation with user input",
                "suggestion": "Use parameterized queries with placeholders"
            }
        ],
        "suggested_patch": "query = 'SELECT * FROM users WHERE id=?'\\ncursor.execute(query, (user_input,))"
    }

    Example 4 (Complex - Multiple Issues):
    Diff: @@ -15,8 +15,8 @@ def process_file(filename): f = open(filename) data = f.read() return data.split(',')
    Output:
    {
        "summary": "Multiple issues: resource leak, missing error handling, and type inconsistency",
        "issues": [
            {
                "file": "processor.py",
                "line": 16,
                "type": "bug",
                "severity": "high",
                "message": "File handle not closed - resource leak",
                "suggestion": "Use context manager: with open(filename) as f:"
            },
            {
                "file": "processor.py",
                "line": 17,
                "type": "bug",
                "severity": "high",
                "message": "No error handling for file not found",
                "suggestion": "Add try-except for FileNotFoundError"
            },
            {
                "file": "processor.py",
                "line": 18,
                "type": "improvement",
                "severity": "medium",
                "message": "No type hints provided",
                "suggestion": "Add type hints: def process_file(filename: str) -> list[str]:"
            }
        ],
        "suggested_patch": "def process_file(filename: str) -> list[str]:\\n    try:\\n        with open(filename) as f:\\n            data = f.read()\\n            return data.split(',')\\n    except FileNotFoundError:\\n        raise FileNotFoundError(f'File {filename} not found')"
    }
    """

    agent: Any = create_agent(
        model="gpt-4o-mini",
        system_prompt=system_prompt,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                        Review this PR diff and point out
                        1. Bugs
                        2. Violations of coding standards
                        3. Security issues
                        4. Suggestions for improvement

                        Diff:
                        {state["diffs"]}
                    """,
                },
            ],
        },
    )

    return {"messages": result["messages"], "output": result["messages"][-1]}


def post_review_comment(state: MessageState) -> dict[str, list[AIMessage]]:
    """Post review comments into the github repo."""
    final_output = state["messages"][-1].content
    convert_to_obj = (
        json.loads(final_output)
        if final_output and isinstance(final_output, str)
        else None
    )
    auth = Auth.Token(get_github_token())
    gh = Github(auth=auth)

    repo_full = state["repo_full"]
    pr_number = state["pr_number"]

    if repo_full is None:
        raise ValueError("repo_full is required")
    if pr_number is None:
        raise ValueError("pr_number is required")

    repo = gh.get_repo(repo_full)
    pr = repo.get_pull(pr_number)

    comment_body = "### 🤖 AI Code Review\n"

    if convert_to_obj and "issues" in convert_to_obj:
        for issue in convert_to_obj["issues"]:
            comment_body += f"""
            **File:** {issue["file"]}
            **Issue:** {issue["message"]}
            **Suggestion:** {issue["suggestion"]}
            ---
        """
    pr.create_issue_comment(comment_body)

    return {"messages": [AIMessage("Done.")]}


@app.get("/")
def hello_world():
    return {"hello": "world"}


@app.post("/webhook/pr")
async def handle_pr(pr: WebhookPayload):
    if pr.action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored"}

    repo_full = pr.repository["full_name"]
    pr_number = pr.pull_request["number"]

    agent_builder = StateGraph(MessageState)

    agent_builder.add_node("fetch_pr_files", fetch_pr_files)
    agent_builder.add_node("llm_review_node", llm_review_node)
    agent_builder.add_node("post_review_comment", post_review_comment)

    agent_builder.add_edge(START, "fetch_pr_files")
    agent_builder.add_edge("fetch_pr_files", "llm_review_node")
    agent_builder.add_edge("llm_review_node", "post_review_comment")
    agent_builder.add_edge("post_review_comment", END)

    graph = agent_builder.compile()

    initial_state: MessageState = {
        "messages": [],
        "diffs": None,
        "output": None,
        "repo_full": repo_full,
        "pr_number": pr_number,
    }
    result = graph.invoke(initial_state)  # type: ignore[arg-type]

    final_output = (
        result["messages"][-1].content if result["messages"] else "No review generated"
    )

    return {
        "status": "processing",
        "data": {"repo_full": repo_full, "pr_number": pr_number},
        "output": final_output,
    }
