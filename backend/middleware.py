"""Custom middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .deps import GATE_COOKIE_NAME, verify_gate_token

def _is_gate_exempt(path: str) -> bool:
    """Check if path is exempt from site gate."""
    p = path.split("?")[0].rstrip("/") or "/"
    return (
        p == "/auth/site-gate"
        or p == "/auth/bootstrap"
        or p.startswith("/docs")
        or p.startswith("/redoc")
        or p == "/openapi.json"
    )


class SiteGateMiddleware(BaseHTTPMiddleware):
    """Require site gate cookie for all requests except exempt paths."""

    async def dispatch(self, request: Request, call_next):
        if _is_gate_exempt(request.url.path):
            return await call_next(request)

        token = request.cookies.get(GATE_COOKIE_NAME)
        if not verify_gate_token(token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Site gate required"},
            )
        return await call_next(request)
