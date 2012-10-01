import sys
import logging

from mimeprovider.exceptions import MimeBadRequest
from mimeprovider.exceptions import MimeInternalServerError

log = logging.getLogger(__name__)


class MimeRenderer(object):
    def __init__(self, mimetypes, error_document_type, error_handler, **kw):
        self.mimetypes = mimetypes
        self.error_document_type = error_document_type
        self.error_handler = error_handler

    def _render(self, obj, request):
        mime = request.accept.best_match(self.mimetypes)

        if mime is None:
            raise MimeBadRequest(
                "Unable to provide response for Accept: " +
                str(request.accept))

        document_type, _, validator = self.mimetypes[mime]

        if not hasattr(obj, "to_data"):
            log.error("Object missing 'to_data' attribute: " + repr(obj))
            raise MimeInternalServerError(
                "Cannot render requested resource")

        request.response.content_type = document_type.get_mimetype(obj)
        return document_type.render(validator, obj)

    def _render_error(self, exc, request):
        error = self.error_handler(exc, request)
        request.response.content_type = \
            self.error_document_type.get_mimetype(error)
        return self.error_document_type.render(self, error, request)

    def __call__(self, obj, system):
        request = system.get("request")

        if request is None:
            return ""

        try:
            return self._render(obj, request)
        except MimeBadRequest as exc:
            log.error("error during render", exc_info=sys.exc_info())
            return self._render_error(exc, request)
