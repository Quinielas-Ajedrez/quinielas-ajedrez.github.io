"""Custom middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .deps import GATE_COOKIE_NAME, GATE_HEADER_NAME, verify_gate_token


def _gate_token_from_request(request) -> str | None:
    t = request.cookies.get(GATE_COOKIE_NAME)
    if t:
        return t
    h = request.headers.get(GATE_HEADER_NAME)
    return h.strip() if h else None


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
    """Require site gate cookie or X-Quiniela-Gate header for non-exempt paths."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if _is_gate_exempt(request.url.path):
            return await call_next(request)

        token = _gate_token_from_request(request)
        if not verify_gate_token(token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Site gate required"},
            )
        return await call_next(request)
