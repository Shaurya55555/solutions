# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional

# --- Event Ingestion Schemas ---

class PaymentEvent(BaseModel):
    event_id: str
    event_type: str
    transaction_id: str
    merchant_id: str
    merchant_name: str
    amount: float
    currency: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Response Schemas ---

class MerchantResponse(BaseModel):
    id: str
    name: str

    model_config = ConfigDict(from_attributes=True)

class EventResponse(BaseModel):
    id: str
    event_type: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class TransactionListResponse(BaseModel):
    id: str
    merchant_id: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TransactionDetailResponse(TransactionListResponse):
    merchant: Optional[MerchantResponse] = None
    events: List[EventResponse] = []
