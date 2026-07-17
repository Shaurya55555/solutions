# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload, selectinload
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

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

def get_transactions(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    merchant_id: str = None, 
    status: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc"
):
    query = db.query(models.Transaction)
    
    # Filtering
    if merchant_id:
        query = query.filter(models.Transaction.merchant_id == merchant_id)
    if status:
        query = query.filter(models.Transaction.status == status)
    if start_date:
        query = query.filter(models.Transaction.created_at >= start_date)
    if end_date:
        query = query.filter(models.Transaction.created_at <= end_date)
    
    # Sorting
    if sort_by == "amount":
        order_col = models.Transaction.amount
    elif sort_by == "created_at":
        order_col = models.Transaction.created_at
    else:
        order_col = models.Transaction.updated_at
        
    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
        
    return query.offset(skip).limit(limit).all()

def get_transaction(db: Session, transaction_id: str):
    # Use joinedload (N-to-1) and selectinload (1-to-N) to fetch all related data in exactly 2 SQL queries total, eliminating the N+1 problem.
    return db.query(models.Transaction).options(
        joinedload(models.Transaction.merchant),
        selectinload(models.Transaction.events)
    ).filter(models.Transaction.id == transaction_id).first()

def get_reconciliation_summary(db: Session):
    # Aggregating directly in SQL using GROUP BY
    summary = db.query(
        func.date(models.Transaction.created_at).label('date'),
        models.Transaction.merchant_id,
        models.Transaction.status,
        func.count(models.Transaction.id).label('total_transactions'),
        func.sum(models.Transaction.amount).label('total_amount')
    ).group_by(
        func.date(models.Transaction.created_at),
        models.Transaction.merchant_id,
        models.Transaction.status
    ).all()
    
    return [
        {
            "date": row.date,
            "merchant_id": row.merchant_id,
            "status": row.status,
            "total_transactions": row.total_transactions,
            "total_amount": float(row.total_amount) if row.total_amount else 0.0
        }
        for row in summary
    ]

def get_discrepancies(db: Session):
    # 1. Settled transactions that have a 'payment_failed' event in their history
    # SQLAlchemy's .any() translates to an efficient SQL EXISTS subquery
    failed_but_settled = db.query(models.Transaction).filter(
        models.Transaction.status == 'settled',
        models.Transaction.events.any(models.Event.event_type == 'payment_failed')
    ).all()
    
    # 2. Transactions stuck in initiated or processed for more than 48 hours
    two_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
    stuck_transactions = db.query(models.Transaction).filter(
        models.Transaction.status.in_(['payment_initiated', 'payment_processed']),
        models.Transaction.created_at < two_days_ago
    ).all()
    
    # 3. Conflicting state transitions (e.g. duplicate terminal events fighting for state)
    # Identifies transactions that have more than one terminal event in their history
    conflicting_transitions = db.query(models.Transaction).join(models.Event).filter(
        models.Event.event_type.in_(['settled', 'payment_failed'])
    ).group_by(models.Transaction.id).having(func.count(models.Event.id) > 1).all()
    
    return {
        "failed_but_settled": failed_but_settled,
        "stuck_transactions": stuck_transactions,
        "conflicting_transitions": conflicting_transitions
    }
