import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
from dotenv import load_dotenv
from github import Github
from github import Auth
from langgraph.graph import StateGraph, START, END
from langchain.messages import AnyMessage, AIMessage
from typing_extensions import TypedDict, Annotated
from langchain.agents import create_agent
import json
import operator

load_dotenv()

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


def fetch_pr_files(state: MessageState):
    """
    Fetch the pull request based on repo fullname and PR number, and return the list of diffs object
    """
    auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
    gh = Github(auth=auth)

    repo = gh.get_repo(state["repo_full"])
    pr = repo.get_pull(state["pr_number"])

    diffs = []

    for f in pr.get_files():
        diffs.append({"filename": f.filename, "patch": f.patch})

    return {"diffs": diffs}


def llm_review_node(state: MessageState):
    """
    LLM will review the pull request diff and suggest code improvements, best practices,
    check coding standards, and feedbacks.
    """
    print("LLM Review node - START \n")
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

    agent = create_agent(
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
                        {state['diffs']}
                    """,
                }
            ]
        }
    )

    print("LLM Output: \n")
    for message in result["messages"]:
        message.pretty_print()

    print("LLM Review node - END \n")

    return {"messages": result["messages"], "output": result["messages"][-1]}


def post_review_comment(state: MessageState):
    """
    Post review comments into the github repo
    """
    final_output = state["messages"][-1].content
    convert_to_obj = (
        json.loads(final_output)
        if final_output and isinstance(final_output, str)
        else None
    )

    print("post_review_comment OUTPUT \n\n")
    print(f"{"x"*100}")
    print(convert_to_obj)
    print(f"{"x"*100}")
    auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
    gh = Github(auth=auth)
    repo = gh.get_repo(state["repo_full"])
    pr = repo.get_pull(state["pr_number"])

    comment_body = "### 🤖 AI Code Review\n"

    for issue in convert_to_obj["issues"]:
        comment_body += f"""
            **File:** {issue['file']}
            **Issue:** {issue['message']}
            **Suggestion:** {issue['suggestion']}
            ---
        """
    pr.create_issue_comment(comment_body)

    return {"messages": [AIMessage("Done.")]}


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

    agent_builder = StateGraph(MessageState)

    agent_builder.add_node("fetch_pr_files", fetch_pr_files)
    agent_builder.add_node("llm_review_node", llm_review_node)
    agent_builder.add_node("post_review_comment", post_review_comment)

    agent_builder.add_edge(START, "fetch_pr_files")
    agent_builder.add_edge("fetch_pr_files", "llm_review_node")
    agent_builder.add_edge("llm_review_node", "post_review_comment")
    agent_builder.add_edge("post_review_comment", END)

    graph = agent_builder.compile()

    result = graph.invoke({"repo_full": repo_full, "pr_number": pr_number})

    final_output = result["messages"][-1].content
    print(f"{"x"*100}")
    print(final_output)
    print(f"{"x"*100}")

    return {
        "status": "processing",
        "data": {"repo_full": repo_full, "pr_number": pr_number},
    }
