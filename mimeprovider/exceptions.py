class MimeException(Exception):
    status_code = 500
    title = "Internal Server Error"


class MimeBadRequest(MimeException):
    status_code = 400
    title = "Bad Request"


class MimeValidationError(MimeException):
    status_code = 400
    title = "Bad Request"


class MimeInternalServerError(MimeException):
    pass
