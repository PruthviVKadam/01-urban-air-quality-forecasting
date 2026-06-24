"""Request-id middleware: accept an inbound X-Request-ID or mint one, echo it back.

The id is stored in a contextvar so the JSON log formatter and the exception handlers
can attach it without threading it through every call.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.request_context import set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        set_request_id(request_id)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        from app.cache import is_rate_limited
        from fastapi.responses import JSONResponse
        
        # Extract IP, fallback to 127.0.0.1
        client_ip = request.client.host if request.client else "127.0.0.1"
        
        # 120 requests per minute
        if is_rate_limited(client_ip, max_requests=120, window_seconds=60):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "code": "http_429",
                    "detail": "Too many requests. Please try again later."
                }
            )
            
        return await call_next(request)
