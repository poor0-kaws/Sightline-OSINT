# SightlineOSINT

SightlineOSINT is a local OSINT investigation app.

It can:
- fetch or accept raw provider data
- save the raw data first
- normalize it into shared records
- resolve duplicate entities
- extract relationships
- write graph nodes and edges
- serve a FastAPI backend
- serve a React investigation UI

## How To Run Tests

1. Create a virtual environment.
2. Install the project in editable mode with dev tools.
3. Run `pytest`.

Example:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## How To Run The App

```bash
python -m pip install -e ".[dev]"
cd frontend
npm install
npm run build
cd ..
uvicorn backend.main:app --reload
```

## Frontend Checks

The React app lives in `frontend/`. Run these from the `frontend` directory:

```bash
npm run lint       # eslint over frontend/src
npm run typecheck  # tsc --noEmit (checks JavaScript via checkJs)
npm run build      # rebuild backend/api/static/react
```

The frontend source is split into `src/components/` (panels, graph canvas) and
`src/lib/` (API client, provider list, form helpers, graph helpers).

Open:

```text
http://localhost:8000/app
```

## Package Manager Flow

This repo uses a simple `pip` + virtual environment flow.

That means:
- `python -m venv .venv` creates an isolated environment
- `python -m pip install -e ".[dev]"` installs the project and test tools
- `pytest` runs the test suite

This is a good starting point because it is easy to understand and does not add extra tooling yet.

## Project Structure

```text
backend/
  api/          FastAPI routes and React static bundle
  cases/        case summaries
  connectors/   provider-specific source adapters
  graph/        graph write/read repositories
  normalization/ provider normalizers and shared entity extraction
  relationships/ relationship extraction
  resolution/   entity resolution
  schemas/      shared models
  services/     pipeline services
  storage/      saved raw records
  utils/        tiny shared helpers
frontend/       React investigation UI
tests/          unit tests for the current prototype
```

## Architecture Summary

The long-term flow for the project looks like this:

1. Fetch data from APIs, uploads, scrapers, webhooks, and manual input.
2. Save the original raw payload first.
3. Normalize each source into a shared shape.
4. Decide when two records describe the same real-world thing.
5. Build relationships between entities.
6. Store the result in a graph database.
7. Read and explore that graph through an API and UI.

In simple words:
- raw data is the untouched source truth
- normalized data is the cleaned shared shape
- the graph is the connected investigation view

## Environment Variables

The project includes a small settings module that reads environment variables.

- `APP_NAME`: visible app name
- `APP_ENV`: environment name like `development` or `test`
- `REQUEST_TIMEOUT_SECONDS`: default outbound request timeout
- `MAX_REQUEST_BYTES`: maximum incoming request body size
- `RATE_LIMIT_PER_MINUTE`: simple per-client API rate limit
- `RAW_STORAGE_PATH`: where raw payloads are saved
- `AUDIT_LOG_PATH`: JSONL audit log path
- `API_AUTH_TOKEN`: optional bearer token for API routes
- `GRAPH_REPOSITORY_KIND`: `memory` or `neo4j`
- `NEO4J_URL`: graph database connection URL
- `NEO4J_USERNAME`: Neo4j username
- `NEO4J_PASSWORD`: Neo4j password
- `IPINFO_API_KEY`: optional IPinfo API key for live Lite API lookups

Copy `.env.example` to `.env` for Docker Compose.

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

To use Neo4j writes, set:

```text
GRAPH_REPOSITORY_KIND=neo4j
NEO4J_URL=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=sightline-password
```

## Key API Routes

- `GET /health`
- `GET /cases`
- `GET /records/raw?case_id=default`
- `POST /source/raw`
- `POST /source/full`
- `GET /resolution/matches?case_id=default`
- `GET /graph/data?case_id=default`
- `POST /graph/rebuild?case_id=default`
- `GET /app`
