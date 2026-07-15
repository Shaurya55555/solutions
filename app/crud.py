from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import timezone

from app import models, schemas

def process_payment_event(db: Session, event: schemas.PaymentEvent):
    # Ensure timestamp is a naive UTC datetime to play nicely with SQLite/Postgres
    if event.timestamp.tzinfo is not None:
        naive_timestamp = event.timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        naive_timestamp = event.timestamp

    # 1. Idempotency Check: Does this event already exist?
    existing_event = db.query(models.Event).filter(models.Event.id == event.event_id).first()
    if existing_event:
        return existing_event # Return 200 OK without duplicating
        
    # 2. Upsert Merchant
    merchant = db.query(models.Merchant).filter(models.Merchant.id == event.merchant_id).first()
    if not merchant:
        merchant = models.Merchant(id=event.merchant_id, name=event.merchant_name)
        db.add(merchant)
        db.flush() # Flush to assign the merchant ID (if it was auto-generated, though here it is provided)
        
    # 3. Upsert Transaction and Update Status
    transaction = db.query(models.Transaction).filter(models.Transaction.id == event.transaction_id).first()
    if not transaction:
        transaction = models.Transaction(
            id=event.transaction_id,
            merchant_id=event.merchant_id,
            amount=event.amount,
            currency=event.currency,
            status=event.event_type,
            created_at=naive_timestamp,
            updated_at=naive_timestamp
        )
        db.add(transaction)
    else:
        # Basic state machine rules: Update status if this event is conceptually "newer"
        # We assume out-of-order delivery could happen, so we only update if the event timestamp is >= the current updated_at
        if naive_timestamp >= transaction.updated_at:
            transaction.status = event.event_type
            transaction.updated_at = naive_timestamp
            
    # 4. Insert the Event
    db_event = models.Event(
        id=event.event_id,
        transaction_id=event.transaction_id,
        event_type=event.event_type,
        timestamp=naive_timestamp
    )
    db.add(db_event)
    
    try:
        db.commit()
    except IntegrityError:
        # Catch any race conditions where another thread inserted the same event
        db.rollback()
        raise HTTPException(status_code=409, detail="Event already exists or a conflict occurred")
        
    return db_event

def get_transactions(db: Session, skip: int = 0, limit: int = 100, merchant_id: str = None, status: str = None):
    query = db.query(models.Transaction)
    if merchant_id:
        query = query.filter(models.Transaction.merchant_id == merchant_id)
    if status:
        query = query.filter(models.Transaction.status == status)
    
    # Order by newest first
    return query.order_by(models.Transaction.updated_at.desc()).offset(skip).limit(limit).all()

def get_transaction(db: Session, transaction_id: str):
    # Returns the transaction; events are accessible via the .events relationship
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
