from rest_framework.response import Response


def success_response(
    message="Success",
    result=None,
    status_code=200,
):
    return Response(
        {
            "code": status_code,
            "message": message,
            "result": result,
        },
        status=status_code,
    )


def error_response(
    message="Something went wrong",
    result=None,
    status_code=400,
):
    return Response(
        {
            "code": status_code,
            "message": message,
            "result": result,
        },
        status=status_code,
    )