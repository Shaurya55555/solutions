from fastapi import FastAPI

app = FastAPI(
    title="Setu Payment Reconciliation API",
    description="Backend service for payment lifecycle events and reconciliation.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
