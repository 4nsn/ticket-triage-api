# Ticket Triage API

A small REST API that receives support tickets, automatically assigns a **category** and a **priority**, stores them, and reports simple statistics. It is built to show clean API design, automated testing and CI, with an optional LLM-based classifier that safely falls back to rules.

![CI](https://github.com/<your-username>/ticket-triage-api/actions/workflows/ci.yml/badge.svg)

## Features

- `POST /tickets` creates a ticket and classifies it automatically
- `GET /tickets` lists tickets, with optional `category`, `priority` and `status` filters
- `GET /tickets/{id}` fetches one ticket
- `PATCH /tickets/{id}/status` moves a ticket between `open`, `in_progress` and `resolved`
- `GET /stats` returns counts by category, priority and status (simple KPIs)
- `GET /health` for health checks
- Input validation with clear `422` errors; `404` for unknown tickets
- Interactive API docs at `/docs` once the server is running

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs, or try it from the terminal:

```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"title": "Refund please", "body": "I was charged twice for my subscription"}'

curl "http://127.0.0.1:8000/tickets?category=billing"
curl http://127.0.0.1:8000/stats
```

## Running the tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```

The tests cover the classifier rules, the LLM classifier's fallback behaviour (using a fake client, so no network or API key is needed), and every API endpoint, including validation and error cases. GitHub Actions runs them on every push and pull request (`.github/workflows/ci.yml`).

## How classification works

| Classifier | When it is used | Behaviour |
|---|---|---|
| `RuleBasedClassifier` (default) | Always available, no network | Counts keyword matches per category; priority is raised by words like "outage" or "charged twice" |
| `LLMClassifier` | `CLASSIFIER=llm` | Asks an LLM for a JSON category and priority; **falls back to the rules** on any error or invalid answer |

To try the LLM classifier:

```bash
pip install -r requirements-llm.txt
export ANTHROPIC_API_KEY=your-key
CLASSIFIER=llm uvicorn app.main:app
```

## Design decisions

- **Application factory (`create_app`)**: lets tests inject an in-memory database and a fake classifier, so tests are fast and deterministic.
- **One interface, two classifiers**: the API depends on `classify(title, body)`, not on a specific implementation, so classifiers can be swapped without touching the endpoints.
- **Fail safe**: a failing LLM call must never stop a ticket being created, so the LLM classifier logs a warning and uses the rules instead.
- **Small storage layer**: all SQL lives in `app/storage.py`, so moving from SQLite to PostgreSQL only changes that file.

## Project layout

```
app/
  main.py         FastAPI app and endpoints
  models.py       Pydantic models and enums
  classifier.py   Rule-based and LLM classifiers
  storage.py      SQLite repository
tests/
  test_api.py         Endpoint tests
  test_classifier.py  Classifier tests
```

## Limitations and next steps

- The keyword rules are simple and will miss unusual wording; they are a baseline, not a trained model.
- The real LLM call is only tested through a fake client. It has not been run against the live API in CI.
- No authentication, pagination or rate limiting yet.
- Next steps: PostgreSQL via SQLAlchemy and migrations, a small evaluation set to compare the rules against the LLM, and background processing of new tickets.

## Docker

```bash
docker build -t ticket-triage-api .
docker run -p 8000:8000 ticket-triage-api
```

## Licence

MIT
