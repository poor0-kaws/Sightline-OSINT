# SightlineOSINT

SightlineOSINT is an investigation tool in progress.

Right now, this repository contains the first backend slice:
- source adapter schemas
- provider validation
- a shared raw response wrapper
- a small ingestion service
- tests for the current ingestion prototype

The bigger goal is to grow this into a full OSINT workflow:
- fetch data from different sources
- save raw payloads
- normalize the data
- resolve duplicate entities
- build graph relationships
- expose the graph through an API
- show it in an investigation UI

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
  connectors/   provider-specific source adapters
  schemas/      shared models for requests and responses
  services/     small service layer over the adapters
  utils/        tiny shared helpers
tests/          unit tests for the current prototype
architecture.md the target system design
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
- `RAW_STORAGE_PATH`: where raw payloads should be saved later
- `NEO4J_URL`: graph database connection URL
- `IPINFO_API_KEY`: API key for the future real IPinfo integration
