import sys
import json
import pprint
import logging

import jsonschema

from mimeprovider.exceptions import MimeException
from mimeprovider.exceptions import MimeBadRequest
from mimeprovider.exceptions import MimeValidationError
from mimeprovider.exceptions import MimeInternalServerError

__all__ = ["MimeProvider"]

log = logging.getLogger(__name__)


class DocumentType(object):
    """
    Base class for document types.
    """
    # does this generate custom mimetypes depending on the object type?
    custom_mime = False

    # a template or the mime type.
    mime = None

    def get_mimetype(self, obj):
        if not self.custom_mime:
            return self.mime
        return self.mime.format(o=obj)


class JsonDocumentType(DocumentType):
    """
    A clever document type that sets up specific MIME depending on the
    available documents.
    """
    custom_mime = True
    mime = "application/{o.object_type}+json"

    def parse(self, context, cls, string):
        data = json.loads(string)

        if hasattr(cls, 'schema'):
            try:
                jsonschema.validate(data, cls.schema)
            except jsonschema.ValidationError as e:
                raise MimeValidationError(str(e))

        return cls.from_data(context, data)

    def render(self, context, obj):
        data = obj.to_data(context)
        return json.dumps(data)


class HtmlDocumentType(DocumentType):
    """
    Sneaky document type that attempt to build your sorry attempt of data into
    a html viewable structure.
    """
    custom_mime = False
    mime = "text/html"

    def parse(self, context, cls, string):
        raise RuntimeError("parse not implemented")

    def render(self, context, obj):
        buf = []

        buf.append("<html>")
        buf.append("<head></head>")
        buf.append("<body>")

        buf.append("<h1>{0} ({1})</h1>".format(obj.object_type,
                                               type(obj).__name__))

        def _build_value(buf, k, v):
            if isinstance(v, list):
                buf.append("<table>")
                for i in sorted(v):
                    buf.append("<tr><td align=\"left\">")
                    _build_data(buf, i)
                    buf.append("</td></tr>")
                buf.append("</table>")
            else:
                _build_data(buf, v)

        def _build_data(buf, data):
            if isinstance(data, dict):
                ref = data.get("$ref")

                if ref is not None:
                    rel = data.get("rel", ref)
                    buf.append(
                        "<a href='{0}'>{1}</a>".format(ref, rel))
                else:
                    buf.append("<table>")
                    for k, v in sorted(data.items()):
                        buf.append("<tr><th valign=\"top\" align=\"right\">")
                        buf.append(k + ":")
                        buf.append("</th><td align=\"left\">")
                        _build_value(buf, k, v)
                        buf.append("</td></tr>")
                    buf.append("</table>")
            else:
                buf.append("{0!s}".format(data))

        _build_data(buf, obj.to_data(context))

        buf.append("</body>")
        buf.append("</html>")

        return "".join(buf)


class TextDocumentType(DocumentType):
    """
    Stupid docoument type that just returns a nicely formatted version of your
    data.
    """
    custom_mime = False
    mime = "text/plain"

    def parse(self, context, cls, string):
        raise RuntimeError("parse not implemented")

    def render(self, context, obj):
        data = obj.to_data(context)
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
        return document_type.render(self, obj)

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
        import itertools

        custom = filter(lambda t: not t.custom_mime, documents)
        other = filter(lambda t: t.custom_mime, documents)

        generate_other = (
            [(t.mime.format(o=o), (t, o)) for o in objs] for t in other)

        generate_custom = ((t.mime, (t, None)) for t in custom)

        generate = itertools.chain(generate_custom, *generate_other)

        mimetypes = dict()

        for (mimetype, new_value) in generate:
            if mimetype in mimetypes:
                _, document_class = mimetypes[mimetype]
                _, new_document_class = new_value
                raise ValueError(("Conflicting mimetypes for {0} "
                                  "between {1} and {2}").format(
                                      mimetype,
                                      document_class,
                                      new_document_class
                                  ))

            mimetypes[mimetype] = new_value

        return mimetypes

    def client(self, *args, **kw):
        try:
            from mimeprovider.requests_client import Client
        except ImportError:
            raise

        return Client(self.mimetypes, *args, **kw)

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

        return document_type.parse(self, cls, request.body)

    @property
    def renderer(self):
        if self.error_handler is None:
            raise ValueError("No 'error_handler' available")

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

        def build_json_ref(request):
            def __json_ref(route, document=None, **kw):
                ref = dict()

                ref["$ref"] = request.route_path(route, **kw)

                if document and not hasattr(document, "object_type"):
                    raise MimeInternalServerError(
                        "Cannot reference object without 'object_type'")

                    ref["rel"] = kw.pop("rel_", document.object_type)
                else:
                    ref["rel"] = kw.pop("rel_", route)

                return ref

            return __json_ref

        config.set_request_property(build_json_ref, "json_ref", reify=True)
