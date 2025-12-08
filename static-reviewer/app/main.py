from fastapi import FastAPI
from pydantic import BaseModel
from ruff_runner import run_ruff_on_code  # type: ignore

app = FastAPI()


class File(BaseModel):
    filename: str
    content: str


class RuffRequest(BaseModel):
    files: list[File]


@app.post("/analyze")
def analyze(req: RuffRequest):
    print(req.files)
    issues = run_ruff_on_code([f.dict() for f in req.files])
    return {"tool": "ruff", "issues": issues}
