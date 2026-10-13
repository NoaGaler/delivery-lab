from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Optional, Any

app = FastAPI()

# מנגנוני שגיאות לפי א.5
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request"})

# זיכרון לשמירת הנתונים
deliveries: dict[int, dict[str, Any]] = {}
current_id = 1

VALID_STATUSES = {"created", "in_transit", "delivered"}
VALID_TRANSITIONS = {
    "created": "in_transit",
    "in_transit": "delivered",
}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/deliveries", status_code=201)
async def create_delivery(request: Request):
    global current_id
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    recipient = body.get("recipient")
    address = body.get("address")

    if not isinstance(recipient, str) or not recipient.strip():
        raise HTTPException(status_code=400, detail="recipient must be a non-empty string")
    if not isinstance(address, str) or not address.strip():
        raise HTTPException(status_code=400, detail="address must be a non-empty string")

    new_delivery = {
        "id": current_id,
        "recipient": recipient,
        "address": address,
        "status": "created"
    }
    deliveries[current_id] = new_delivery
    current_id += 1
    return new_delivery

@app.get("/deliveries")
def list_deliveries(status: Optional[str] = None):
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        return [d for d in deliveries.values() if d["status"] == status]
    return list(deliveries.values())

@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return deliveries[delivery_id]

@app.patch("/deliveries/{delivery_id}/status")
async def update_delivery_status(delivery_id: int, request: Request):
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    new_status = body.get("status")
    if not isinstance(new_status, str) or new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status value")

    current_status = deliveries[delivery_id]["status"]
    expected_next = VALID_TRANSITIONS.get(current_status)

    if new_status != expected_next:
        raise HTTPException(status_code=409, detail=f"Cannot transition from {current_status} to {new_status}")

    deliveries[delivery_id]["status"] = new_status
    return deliveries[delivery_id]

@app.delete("/deliveries/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if deliveries[delivery_id]["status"] != "created":
        raise HTTPException(status_code=409, detail="Only deliveries with status 'created' can be deleted")

    del deliveries[delivery_id]
    return Response(status_code=204)