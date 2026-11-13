import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("uvicorn.error")


async def record_request(request: Request, call_next):
    request_id = uuid4().hex
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
        return response
    finally:
        route = request.scope.get("route")
        logger.info(json.dumps({
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "route": getattr(route, "path", "unmatched"),
            "status": status,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        }))
