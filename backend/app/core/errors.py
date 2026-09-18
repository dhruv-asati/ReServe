"""
AppError: the exception type ReServe's own code should raise for expected,
named failure cases (duplicate email, invalid credentials, missing/expired
token, forbidden role, etc.).

Raising AppError instead of a bare HTTPException lets app/main.py catch
every one of these in a single handler and always emit the project's
{"success": false, "error": {"code", "message"}} envelope, with a stable
machine-readable `code` a frontend can branch on.
"""


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)
