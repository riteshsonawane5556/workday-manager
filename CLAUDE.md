# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Workday Manager** is a Personal Chief of Staff Agent — a FastAPI-based service that uses a pydantic-ai Agent to help manage a user's inbox via the Nylas email API. The project is currently in Phase 1 (foundation).

## Package Management

This project uses `uv` (not pip or poetry). All dependency and environment commands go through `uv`:

```bash
uv sync                        # install dependencies from pyproject.toml
uv add <package>               # add a dependency
uv run main.py                 # run the app entry point
uv run uvicorn main:app --reload   # run the FastAPI dev server
```

## Running & Testing

```bash
uv run uvicorn main:app --reload        # dev server on http://localhost:8000
```

## Pydantic Ai
Please read pydantic ai related docs here https://pydantic.dev/docs/ai/llms.txt while building and integrating anything related to Ai.