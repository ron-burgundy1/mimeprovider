import sys
import json
import pprint
import operator
import logging

__all__ = ["MimeProvider"]

log = logging.getLogger(__name__)


class MimeException(Exception):
    status_code = 500
    title = "Internal Server Error"


class MimeBadRequest(MimeException):
    status_code = 400
    title = "Bad Request"


class MimeInternalServerError(MimeException):
    status_code = 500


class DocumentType(object):
    # does this generate custom mimetypes depending on the object type?
    custom_mime = False
    # a template or the actual mime type.
    mime = None

    def get_mimetype(self, obj):
        if not self.custom_mime:
            return self.mime
        return self.mime.format(o=obj)


class JsonDocumentType(DocumentType):
    custom_mime = True
    mime = "application/{o.object_type}+json"

    def parse(self, context, cls, string, request):
        data = json.loads(string)
        return cls.from_data(data, request)

    def render(self, context, obj, request):
        data = obj.to_data(request)
        return json.dumps(data)


class HtmlDocumentType(DocumentType):
    custom_mime = False
    mime = "text/html"

    def parse(self, context, cls, string, request):
        raise RuntimeError("parse not implemented")

    def render(self, context, obj, request):
        buf = []

        data = obj.to_data(request)

        buf.append("<html>")
        buf.append("<head></head>")
        buf.append("<body>")

        buf.append("<h1>{0} ({1})</h1>".format(obj.object_type,
                                               type(obj).__name__))

        if isinstance(data, list):
            buf.append("<table>")
            for i in data:
                buf.append("<tr><td>{0}</td></tr>".format(i))
            buf.append("</table>")
        elif isinstance(data, dict):
            buf.append("<table>")
            for k, v in data.items():
                buf.append("<tr><th>{0}</th><td>{1}</td></tr>".format(k, v))
            buf.append("</table>")
        else:
            buf.append("<pre>{0|r}</pre>".format(data))

        buf.append("</body>")
        buf.append("</html>")

        return "".join(buf)


class TextDocumentType(DocumentType):
    custom_mime = False
    mime = "text/plain"

    def parse(self, context, cls, string, request):
        raise RuntimeError("parse not implemented")

    def render(self, context, obj, request):
        data = obj.to_data(request)
        pp = pprint.PrettyPrinter(indent=4, depth=1)
        return pp.pformat(data)


class MimeRenderer(object):
    def __init__(self, mimetypes, error_document_type, error_handler):
        self.mimetypes = mimetypes
        self.error_document_type = error_document_type
        self.error_handler = error_handler

    def _render(self, obj, request):
        mime = request.accept.best_match(self.mimetypes)

        if mime is None:
            raise MimeBadRequest(
                "Unable to provide response for Accept: " +
                str(request.accept))

        document_type, _ = self.mimetypes[mime]

        if not hasattr(obj, "to_data"):
            log.error("Object missing 'to_data' attribute: " + repr(obj))
            raise MimeInternalServerError(
                "Cannot render requested resource")

        request.response.content_type = document_type.get_mimetype(obj)
        return document_type.render(self, obj, request)

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


class MimeProvider(object):
    def __init__(self, documents, **kw):
        self.renderer_name = kw.get("renderer_name", "mime")
        self.attribute_name = kw.get("attribute_name", "mime_body")
        self.error_handler = kw.get("error_handler", None)

        if self.error_handler is None:
            raise ValueError("missing required argument 'error_handler'")

        types = kw.get("types")
        if types is None:
            types = [
                JsonDocumentType(),
                TextDocumentType(),
                HtmlDocumentType()
            ]

        if not types:
            raise ValueError("no document types specified")

        documents = list(documents)

        self.error_document_type = kw.get("error_document_type", types[0])
        self._validate_documents(documents)
        self.mimetypes = self._build_mimetypes(documents, types)

    def _validate_documents(self, documents):
        for doc in documents:
            if not hasattr(doc, "object_type"):
                raise ValueError(
                    "Object does not have required 'object_type' attribute: "
                    + repr(doc))

    def _build_mimetypes(self, objs, documents):
        custom = filter(lambda t: not t.custom_mime, documents)
        other = filter(lambda t: t.custom_mime, documents)

        generate = (
            [(t.mime.format(o=o), (t, o)) for o in objs] for t in other)

        mimetypes = dict(reduce(operator.add, generate))
        mimetypes.update(dict((t.mime, (t, None)) for t in custom))
        return mimetypes

    def get_mime_body(self, request):
        if not request.body or not request.content_type:
            return None

        result = self.mimetypes.get(request.content_type)

        if result is None:
            raise MimeBadRequest(
                "Unsupported Content-Type: " + request.content_type)

        document_type, cls = result

        # the specific document does not support deserialization.
        if not hasattr(cls, "from_data"):
            raise MimeBadRequest(
                "Unsupported Content-Type: " +
                request.content_type)

        return document_type.parse(self, cls, request.body, request)

    @property
    def renderer(self):
        def setup_renderer(helper):
            return MimeRenderer(self.mimetypes, self.error_document_type,
                                self.error_handler)
        return setup_renderer

    def add_config(self, config):
        config.add_renderer(self.renderer_name, self.renderer)
        config.set_request_property(self.get_mime_body, self.attribute_name,
                                    reify=True)
        config.add_view(self.error_handler, context=MimeException,
                        renderer=self.renderer_name)
