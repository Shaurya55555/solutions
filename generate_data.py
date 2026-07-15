import json
import uuid
import random
from datetime import datetime, timedelta, timezone

MERCHANTS = [
    {"id": "merchant_1", "name": "TechStore"},
    {"id": "merchant_2", "name": "FreshBasket"},
    {"id": "merchant_3", "name": "BookWorm"},
    {"id": "merchant_4", "name": "GameZone"},
    {"id": "merchant_5", "name": "FitGear"}
]

def generate_events():
    events = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    
    def create_event(t_id, m, ev_type, amount, t_offset):
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": ev_type,
            "transaction_id": t_id,
            "merchant_id": m["id"],
            "merchant_name": m["name"],
            "amount": amount,
            "currency": "INR",
            "timestamp": (base_time + t_offset).isoformat()
        }

    # 1. Successful Transactions (3000 txs -> 9000 events)
    for _ in range(3000):
        t_id = str(uuid.uuid4())
        m = random.choice(MERCHANTS)
        amount = round(random.uniform(100, 50000), 2)
        offset = timedelta(days=random.uniform(0, 28))
        
        events.append(create_event(t_id, m, "payment_initiated", amount, offset))
        events.append(create_event(t_id, m, "payment_processed", amount, offset + timedelta(seconds=5)))
        events.append(create_event(t_id, m, "settled", amount, offset + timedelta(days=1)))
        
    # 2. Failed Transactions (500 txs -> 1000 events)
    for _ in range(500):
        t_id = str(uuid.uuid4())
        m = random.choice(MERCHANTS)
        amount = round(random.uniform(100, 50000), 2)
        offset = timedelta(days=random.uniform(0, 28))
        
        events.append(create_event(t_id, m, "payment_initiated", amount, offset))
        events.append(create_event(t_id, m, "payment_failed", amount, offset + timedelta(seconds=2)))
        
    # 3. Pending Settlements (500 txs -> 1000 events)
    for _ in range(500):
        t_id = str(uuid.uuid4())
        m = random.choice(MERCHANTS)
        amount = round(random.uniform(100, 50000), 2)
        offset = timedelta(days=random.uniform(0, 28))
        
        events.append(create_event(t_id, m, "payment_initiated", amount, offset))
        events.append(create_event(t_id, m, "payment_processed", amount, offset + timedelta(seconds=5)))

    # 4. Discrepancies: Failed then Settled (100 txs -> 300 events)
    for _ in range(100):
        t_id = str(uuid.uuid4())
        m = random.choice(MERCHANTS)
        amount = round(random.uniform(100, 50000), 2)
        offset = timedelta(days=random.uniform(0, 28))
        
        events.append(create_event(t_id, m, "payment_initiated", amount, offset))
        events.append(create_event(t_id, m, "payment_failed", amount, offset + timedelta(seconds=5)))
        events.append(create_event(t_id, m, "settled", amount, offset + timedelta(days=1)))

    # 5. Duplicates (500 extra events)
    duplicates = random.sample(events, 500)
    events.extend(duplicates)

    # Shuffle events to simulate out-of-order delivery
    random.shuffle(events)
    
    return events

if __name__ == "__main__":
    print("Generating events...")
    events = generate_events()
    with open("sample_events.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"Generated {len(events)} events in sample_events.json")
