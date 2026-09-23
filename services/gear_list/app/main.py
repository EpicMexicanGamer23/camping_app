import httpx
from fastapi import FastAPI

app = FastAPI(
    title="Gear-List Service",
    description="Second microservice",
    version="1.0.0",
)


@app.get("/")
def root():
    return {"service": "Reminders", "message": "Hello from Gear-List Service"}
