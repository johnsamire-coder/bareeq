from rest_framework.exceptions import APIException


class BusinessError(APIException):
    """An error the app shows to the user: {"code": "...", "detail": "..."}.
    `code` is a stable name the app can check; `detail` is the Arabic message."""

    status_code = 400

    def __init__(self, code, message, status=400):
        self.status_code = status
        super().__init__({"code": code, "detail": message})
