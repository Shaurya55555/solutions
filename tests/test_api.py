import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone

from app.main import app
from app.database import Base, get_db

# Use an in-memory database strictly for testing so we don't mess up our seeded data
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# This fixture runs before every test to ensure a clean slate
@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ingest_event():
    payload = {
        "event_id": "test-event-1",
        "event_type": "payment_initiated",
        "transaction_id": "test-txn-1",
        "merchant_id": "test-merchant-1",
        "merchant_name": "Test Merchant",
        "amount": 100.0,
        "currency": "INR",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    response = client.post("/events", json=payload)
    assert response.status_code == 200
    assert response.json()["id"] == "test-event-1"

def test_ingest_event_idempotency():
    payload = {
        "event_id": "test-event-idemp",
        "event_type": "payment_initiated",
        "transaction_id": "test-txn-2",
        "merchant_id": "test-merchant-1",
        "merchant_name": "Test Merchant",
        "amount": 150.0,
        "currency": "INR",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # First request should succeed
    res1 = client.post("/events", json=payload)
    assert res1.status_code == 200
    
    # Second request with the exact same payload should also succeed (idempotent)
    res2 = client.post("/events", json=payload)
    assert res2.status_code == 200
    
    # The responses should be identical
    assert res1.json() == res2.json()

def test_get_transactions_and_summary():
    # Insert a dummy transaction first
    payload = {
        "event_id": "test-event-3",
        "event_type": "settled",
        "transaction_id": "test-txn-3",
        "merchant_id": "m1",
        "merchant_name": "Merchant 1",
        "amount": 500.0,
        "currency": "INR",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    client.post("/events", json=payload)

    # Test GET /transactions
    res_txns = client.get("/transactions")
    assert res_txns.status_code == 200
    assert len(res_txns.json()) == 1
    assert res_txns.json()[0]["status"] == "settled"

    # Test GET /reconciliation/summary
    res_summary = client.get("/reconciliation/summary")
    assert res_summary.status_code == 200
    assert len(res_summary.json()) == 1
    assert res_summary.json()[0]["total_transactions"] == 1
    assert res_summary.json()[0]["total_amount"] == 500.0
