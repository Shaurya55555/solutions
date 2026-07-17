# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends, status, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os

from app import schemas, crud
from app.database import get_db

app = FastAPI(
    title="Payment Reconciliation API",
    description="Backend service for payment lifecycle events and reconciliation.",
    version="1.0.0"
)

# Serve static files (CSS, JS)
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def serve_home():
    """Serve the dashboard home page."""
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/ui/events", include_in_schema=False)
def serve_events():
    """Serve the event ingestion page."""
    return FileResponse(os.path.join(static_dir, "events.html"))

@app.get("/ui/transactions", include_in_schema=False)
def serve_transactions():
    """Serve the transactions list page."""
    return FileResponse(os.path.join(static_dir, "transactions.html"))

@app.get("/ui/transaction", include_in_schema=False)
def serve_transaction_detail():
    """Serve the transaction detail/lookup page."""
    return FileResponse(os.path.join(static_dir, "transaction.html"))

@app.get("/ui/summary", include_in_schema=False)
def serve_summary():
    """Serve the reconciliation summary page."""
    return FileResponse(os.path.join(static_dir, "summary.html"))

@app.get("/ui/discrepancies", include_in_schema=False)
def serve_discrepancies():
    """Serve the discrepancies page."""
    return FileResponse(os.path.join(static_dir, "discrepancies.html"))

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/events", status_code=status.HTTP_200_OK, response_model=schemas.EventResponse)
def ingest_event(event: schemas.PaymentEvent, db: Session = Depends(get_db)):
    """
    Ingest a payment lifecycle event.
    Idempotent: Re-submitting the same event_id will not result in duplicates.
    """
    db_event = crud.process_payment_event(db, event)
    return db_event

@app.get("/transactions", response_model=List[schemas.TransactionListResponse])
def list_transactions(
    skip: int = 0, 
    limit: int = 100, 
    merchant_id: Optional[str] = None, 
    status: Optional[str] = None, 
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Optional[str] = "updated_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    """
    List transactions with optional filtering (merchant_id, status, dates), sorting, and pagination.
    """
    return crud.get_transactions(
        db, skip=skip, limit=limit, merchant_id=merchant_id, status=status, 
        start_date=start_date, end_date=end_date, sort_by=sort_by, sort_order=sort_order
    )

@app.get("/transactions/{transaction_id}", response_model=schemas.TransactionDetailResponse)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """
    Fetch details of a specific transaction including its event history.
    """
    db_txn = crud.get_transaction(db, transaction_id=transaction_id)
    if db_txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_txn

@app.get("/reconciliation/summary")
def get_reconciliation_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated transaction counts and amounts grouped by date, merchant, and status.
    """
    return crud.get_reconciliation_summary(db)

@app.get("/reconciliation/discrepancies")
def get_reconciliation_discrepancies(db: Session = Depends(get_db)):
    """
    Identifies transactions with inconsistent states.
    Examples: 
    - Marked as settled but had a failed event previously.
    - Stuck in processed state for > 48 hours without settling.
    """
    return crud.get_discrepancies(db)
