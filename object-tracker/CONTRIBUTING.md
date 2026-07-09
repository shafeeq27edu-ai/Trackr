# Contributing to Trackr

We love your input! We want to make contributing to this project as easy and transparent as possible.

## Pull Requests

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes (`pytest`).
4. Ensure your code passes the linter (`ruff check .`).
5. Ensure your Docker images build correctly.

## Development Environment Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run database migrations: `alembic upgrade head`
3. Start backend: `uvicorn api.main:app --reload`
4. Start frontend: `streamlit run frontend/app.py`
