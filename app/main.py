from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app import schemas, crud
from app.database import get_db

app = FastAPI(
    title="Setu Payment Reconciliation API",
    description="Backend service for payment lifecycle events and reconciliation.",
    version="1.0.0"
)

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

@app.get("/transactions", response_model=List[schemas.TransactionResponse])
def list_transactions(
    skip: int = 0, 
    limit: int = 100, 
    merchant_id: Optional[str] = None, 
    status: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    List transactions with optional filtering (merchant_id, status) and pagination.
    """
    return crud.get_transactions(db, skip=skip, limit=limit, merchant_id=merchant_id, status=status)

@app.get("/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
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
