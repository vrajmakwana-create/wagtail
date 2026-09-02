from typing import Any, Optional

from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """
    Centralized API response handler.
    """

    @staticmethod
    def success(
        message: str = "Success",
        result: Optional[Any] = None,
        status_code: int = status.HTTP_200_OK,
    ):
        return Response(
            {
                "code": status_code,
                "message": message,
                "result": result,
            },
            status=status_code,
        )

    @staticmethod
    def error(
        message: str = "Something went wrong",
        result: Optional[Any] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        return Response(
            {
                "code": status_code,
                "message": message,
                "result": result,
            },
            status=status_code,
        )