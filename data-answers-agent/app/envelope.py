"""ApiResponse envelope — every route returns this shape."""

from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: Literal["ok", "needs_clarification", "declined", "error"]
    data: Optional[T] = None
    clarification: Optional[str] = None
    decline_reason: Optional[str] = None
    request_id: str
    error: Optional[str] = None


def ok_response(data: T, request_id: str) -> ApiResponse[T]:
    return ApiResponse(status="ok", data=data, request_id=request_id)


def clarification_response(clarification: str, request_id: str) -> ApiResponse:
    return ApiResponse(
        status="needs_clarification",
        clarification=clarification,
        request_id=request_id,
    )


def declined_response(reason: str, request_id: str) -> ApiResponse:
    return ApiResponse(
        status="declined",
        decline_reason=reason,
        request_id=request_id,
    )


def error_response(message: str, request_id: str) -> ApiResponse:
    return ApiResponse(status="error", error=message, request_id=request_id)
