# AI PR Assist

An intelligent code review system that leverages AI to automatically review GitHub pull requests with static analysis and LLM-powered feedback.

## Features

- **Automated PR Analysis**: Integrates with GitHub to analyze pull requests via webhooks
- **Static Code Analysis**: Runs Ruff for linting and code quality checks
- **AI-Powered Reviews**: Uses OpenAI GPT models to provide intelligent code review feedback
- **Graph-Based Processing**: Built with LangGraph for structured multi-step analysis workflows
- **Microservices Architecture**: Separate services for main application and static analysis

## Tech Stack

- **Backend**: FastAPI, LangChain, LangGraph
- **AI/ML**: OpenAI API, LangChain-OpenAI
- **Code Analysis**: Ruff, PyGithub
- **Containerization**: Docker, Docker Compose
- **Runtime**: Python 3.13

## System Architecture
<img width="3318" height="1602" alt="image" src="https://github.com/user-attachments/assets/401ed7ee-5c2e-462c-ad45-c9f30f25623f" />


## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose (optional)
- GitHub token
- OpenAI API key

### Environment Setup

Create a `.env` file with:

```env
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4o-mini
LOG_LEVEL=INFO
DEBUG=false
```

### Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Run with Docker

```bash
docker-compose up
```

This starts:
- **Main App** on `http://localhost:8000`
- **Static Reviewer** on `http://localhost:8080`

## API Endpoints

- `POST /` - Webhook endpoint for GitHub PR events
- `POST /analyze` (Static Reviewer) - Analyze files with Ruff

## Project Structure

```
.
├── main.py                 # Main FastAPI application
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Main app container
└── static-reviewer/        # Static analysis microservice
    └── app/
        ├── main.py         # Ruff analysis service
        ├── ruff_runner.py  # Ruff integration
        └── requirements.txt
```

## How It Works

1. GitHub sends PR webhook events to the main application
2. Main app fetches PR files and diffs
3. Static reviewer analyzes code with Ruff
4. LLM generates detailed code review feedback
5. Results are processed and returned

## License

MIT
