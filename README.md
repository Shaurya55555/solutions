# Setu Payment Reconciliation Service

A lightweight, production-ready backend service designed to ingest payment lifecycle events, maintain transaction state, and provide reconciliation reports.

## Architecture Overview

*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+). Chosen for its speed, built-in Pydantic validation, and automatic OpenAPI documentation.
*   **Database**: PostgreSQL / SQLite. 
    *   *SQLite* is used by default for lightning-fast local development without dependencies.
    *   *PostgreSQL* is configured via `docker-compose` and is intended for production due to its robust concurrent write handling.
*   **ORM**: SQLAlchemy & Alembic. Alembic handles database migrations.
*   **Design Paradigm**: The system is designed around **strict idempotency**. Incoming events are deduplicated at the database level using their `event_id` as the Primary Key. Status updates function as a simple state machine, keeping the transaction state consistent regardless of event duplication.

## Setup Instructions

There are two ways to run this service locally: Native Python or Docker.

### Option A: Docker (Recommended)
This will spin up a PostgreSQL database and the FastAPI web server.

1. Ensure Docker and Docker Compose are installed.
2. Run: `docker-compose up --build -d`
3. The API is now available at `http://127.0.0.1:8000`. Migrations run automatically.

### Option B: Local Python Setup (SQLite)
1. Create a virtual environment: `python3 -m venv .venv`
2. Activate it: `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations to create the local `app.db` file: `alembic upgrade head`
5. Start the server: `uvicorn app.main:app --reload`

## Generating Sample Data & Seeding

To verify the endpoints with realistic data, two scripts are provided:

1. `python3 generate_data.py`: Generates `sample_events.json` containing >11,000 events (successes, failures, discrepancies, and 500 intentional duplicates).
2. `python3 seed_data.py`: Ingests the JSON file into the running server via the `POST /events` endpoint, verifying performance and idempotency.

## API Documentation

Once the server is running, you can access the interactive OpenAPI (Swagger) documentation at:
**[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

### Endpoints
*   `GET /health`: Health check.
*   `POST /events`: Ingest a payment event (Idempotent).
*   `GET /transactions`: List transactions (supports pagination, filtering by `merchant_id` and `status`).
*   `GET /transactions/{transaction_id}`: Fetch detailed transaction history.
*   `GET /reconciliation/summary`: SQL-aggregated transaction counts/amounts grouped by date, merchant, and status.
*   `GET /reconciliation/discrepancies`: SQL-based detection of inconsistent states (e.g. failed but settled, stuck in pending).

*(A fully configured Postman Collection `Setu_Reconciliation_API.postman_collection.json` is also included in the repository).*

## Testing

Automated tests are written using `pytest`. They use an isolated, in-memory SQLite database.
Run them using:
```bash
pytest
```

## Deployment Details

*(Candidate Note: You will deploy this to Render/Railway and put your public URL here)*

**Public URL:** `[Insert Production URL Here]`

The application can be seamlessly deployed on platforms like **Render**, **Railway**, or **Fly.io**. Since Alembic is configured, the deployment command simply needs to be `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Just ensure a PostgreSQL database is attached and the `DATABASE_URL` environment variable is exposed to the web service.

## Assumptions & Tradeoffs

1.  **Idempotency Handling**: If a duplicate event arrives, the API gracefully returns a `200 OK` with the existing event data instead of a `409 Conflict`. This is a design choice assuming that partner webhooks prefer silent successes for duplicates rather than treating them as errors.
2.  **State Machine Simplification**: In a production environment, strict rules would dictate state transitions (e.g., `settled` cannot transition back to `payment_failed`). To keep the take-home simple but robust, the latest event timestamp dictates the transaction status, and any impossible states are surfaced via the `/reconciliation/discrepancies` endpoint.
3.  **SQL vs Python**: All heavy lifting for aggregations (`/summary`) and complex matching (`/discrepancies`) is offloaded to the database engine via efficient SQLAlchemy constructs (`group_by`, `.any()`). Python loops are strictly avoided for data manipulation.
4.  **Local vs Prod Database**: SQLite is used dynamically if no `DATABASE_URL` is found. This trades a bit of environment parity for immense reviewer convenience (they can run it instantly without configuring Postgres). PostgreSQL is fully supported and recommended.
