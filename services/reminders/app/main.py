import httpx
from fastapi import FastAPI

app = FastAPI(
    title="Reminders Service",
    description="First microservice",
    version="1.0.0",
)

reminders = []


@app.get("/")
def root():
    return {"service": "Reminders", "message": "Hello from Reminders Service"}


@app.get("/call-service-b")
async def call_service_b():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://service-b:8000/hello")

    return {
        "service_a": "Reminders",
        "service_b_response": response.json(),
    }

@app.get("")
def get_reminders():
    return {"reminders": []}