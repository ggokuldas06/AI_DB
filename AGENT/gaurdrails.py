import json
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

BLOCKED_PATTERNS =[
    "drop table", "drop database", "delete from", "truncate",
    "alter table", "create user", "grant ", "revoke ",
    "--", ";--", "'; ", '"; ',                         
    "ignore previous", "ignore all instructions",       
    "system prompt", "jailbreak",
]
ALLOWED_TOPICS = [
    "customer", "order", "product", "sales", "revenue", "payment",
    "region", "category", "employee", "report", "top", "total",
    "average", "count", "how many", "which", "what", "who", "list",
    "show", "find", "give", "best", "worst", "compare",
]

def check_input(text: str) -> str | None:
    lower= text.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in lower:
            return f"Blocked: query contains disallowed pattern '{pattern}'."
    
    if not any(topic in lower for topic in ALLOWED_TOPICS):
        return "Only questions about sales, customers, orders, products, or reports are allowed."
    
    return None

SENSITIVE_FIELDS = ["email", "phone", "credit_limit", "notes", "assigned_rep"]

def scrub_output(result: str) -> str:
    """Remove sensitive fields if the response is JSON."""
    try:
        data = json.loads(result)
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    for field in SENSITIVE_FIELDS:
                        row.pop(field, None)
            return json.dumps(data, indent=2)
    except (json.JSONDecodeError, TypeError):
        pass
    return result

class GuardrailsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            body_bytes=await request.body()
            body = json.loads(body_bytes) if body_bytes else {}
            text=body.get("question") or body.get("request") or ""

            error=check_input(text)
            if error:
                return JSONResponse(status_code=400, content={"error": error})
        except Exception as e:
            pass

        response=await call_next(request)
        if response.headers.get("content-type", "").startswith("application/json"):
                raw = b""
                async for chunk in response.body_iterator:
                    raw += chunk
                scrubbed = scrub_output(raw.decode()).encode()
                from starlette.responses import Response
                return Response(
                    content=scrubbed,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json",
                )
        return response

