import uuid

import structlog


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


logger = structlog.get_logger()


class RequestIDMiddleware:
    """Pure ASGI middleware — avoids anyio task-group issues from BaseHTTPMiddleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            request_id = headers.get(b"x-request-id", str(uuid.uuid4()).encode()).decode()
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                request_id=request_id,
                path=scope.get("path", ""),
                method=scope.get("method", ""),
            )

            async def send_with_header(message):
                if message["type"] == "http.response.start":
                    message = dict(message)
                    message["headers"] = list(message.get("headers", [])) + [
                        (b"x-request-id", request_id.encode())
                    ]
                await send(message)

            await self.app(scope, receive, send_with_header)
        else:
            await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware — avoids anyio task-group issues from BaseHTTPMiddleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            security_headers = [
                (b"x-content-type-options", b"nosniff"),
                (b"x-frame-options", b"DENY"),
                (b"x-xss-protection", b"1; mode=block"),
                (b"referrer-policy", b"strict-origin-when-cross-origin"),
            ]

            async def send_with_headers(message):
                if message["type"] == "http.response.start":
                    message = dict(message)
                    message["headers"] = list(message.get("headers", [])) + security_headers
                await send(message)

            await self.app(scope, receive, send_with_headers)
        else:
            await self.app(scope, receive, send)
