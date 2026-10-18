from fastapi.responses import JSONResponse


def error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)
