from fastapi import HTTPException


def not_found(msg: str = "No encontrado") -> HTTPException:
    # Recurso ajeno y recurso inexistente son indistinguibles a propósito.
    return HTTPException(404, msg)


def conflict(code: str, msg: str, **extra) -> HTTPException:
    return HTTPException(409, {"code": code, "message": msg, **extra})


def bad(code: str, msg: str, status: int = 422) -> HTTPException:
    return HTTPException(status, {"code": code, "message": msg})
