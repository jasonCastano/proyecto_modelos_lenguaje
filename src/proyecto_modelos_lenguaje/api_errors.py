"""Sobre de error común de la API (``{"error": {code, message, retryable, action}}``).

Lo comparten ``api.py`` y los routers v1 de la spec 026. Nunca incluye trazas ni secretos.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse


class ApiV1Error(Exception):
    """Error controlado de los routers v1; ``api.py`` lo convierte en el sobre común."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        action: str = "revisar",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.action = action
        self.retryable = retryable


def error_response(
    code: str,
    message: str,
    *,
    retryable: bool,
    action: str,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "action": action,
            }
        },
    )
