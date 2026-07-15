import json
import urllib.request
import urllib.error

def seed_data():
    with open("sample_events.json", "r") as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events. Seeding database...")
    
    url = "http://127.0.0.1:8000/events"
    req_headers = {'Content-Type': 'application/json'}
    
    for i, event in enumerate(events):
        data = json.dumps(event).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=req_headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10.0) as response:
                if response.status != 200:
                    print(f"Failed to ingest event {event['event_id']}: {response.status}")
        except urllib.error.URLError as e:
             if (i == 0):
                 print(f"Could not connect to the server. Is uvicorn running on {url}? Error: {e}")
                 return
             print(f"Failed to ingest event {event['event_id']}: {e}")
                
        if (i + 1) % 1000 == 0:
            print(f"Processed {i + 1}/{len(events)} events...")
                
    print("Seeding complete!")

if __name__ == "__main__":
    seed_data()
