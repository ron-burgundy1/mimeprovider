import logging

from mimeprovider.documenttype import get_default_document_types
from mimeprovider.client import get_default_client

from mimeprovider.exceptions import MimeException
from mimeprovider.exceptions import MimeBadRequest

from mimeprovider.mimerenderer import MimeRenderer
from mimeprovider.validators import get_default_validator

__all__ = ["MimeProvider"]
__version__ = "0.1.2"

log = logging.getLogger(__name__)


def build_json_ref(request):
    def json_ref(route, document=None, **kw):
        ref = dict()

        ref["$ref"] = request.route_path(route, **kw)

        rel_default = None

        if document:
            rel_default = getattr(document, "object_type",
                                  document.__class__.__name__)
        else:
            rel_default = route

        ref["rel"] = kw.pop("rel_", rel_default)

        return ref

    return json_ref


class MimeProvider(object):
    def __init__(self, documents=[], **kw):
        self.renderer_name = kw.get("renderer_name", "mime")
        self.attribute_name = kw.get("attribute_name", "mime_body")
        self.error_handler = kw.get("error_handler", None)

        self.validator = kw.get("validator")

        if self.validator is None:
            self.validator = get_default_validator()

        types = kw.get("types")

        if types is None:
            types = get_default_document_types()

        if not types:
            raise ValueError("No document types specified")

        self.client = kw.get("client")

        if self.client is None:
            self.client = get_default_client()

        self.type_instances = [t() for t in types]
        self.mimetypes = dict(self._generate_base_mimetypes())

        self.error_document_type = kw.get(
            "error_document_type",
            self.type_instances[0])

        self.register(*documents)

    def _validate(self, document):
        if not hasattr(document, "object_type"):
            raise ValueError(
                ("Object does not have required 'object_type' "
                 "attribute {0!r}").format(document))

    def _generate_base_mimetypes(self):
        """
        Generate the base mimetypes as described by non customized document
        types.
        """
        for t in self.type_instances:
            if t.custom_mime:
                continue

            yield t.mime, (t, None, None)

    def _generate_document_mimetypes(self, documents):
        for t in self.type_instances:
            if not t.custom_mime:
                continue

            for o in documents:
                mimetype = t.mime.format(o=o)

                validator = None

                if hasattr(o, "schema"):
                    validator = self.validator(o.schema)

                yield mimetype, (t, o, validator)

    def register(self, *documents):
        documents = list(documents)

        for document in documents:
            self._validate(document)

        generator = self._generate_document_mimetypes(documents)

        for (m, value) in generator:
            if m not in self.mimetypes:
                self.mimetypes[m] = value
                continue

            _, cls = self.mimetypes[m]
            _, new_cls = value

            raise ValueError(
                "Conflicting handler for {0}, {1} and {2}".format(
                    m, cls, new_cls))

    def get_client(self, *args, **kw):
        return self.client(self.mimetypes, *args, **kw)

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
                                self.error_handler, validator=self.validator)

        return setup_renderer

    def add_config(self, config):
        config.add_renderer(self.renderer_name, self.renderer)
        config.set_request_property(self.get_mime_body, self.attribute_name,
                                    reify=True)
        config.set_request_property(build_json_ref, "json_ref", reify=True)

        config.add_view(self.error_handler, context=MimeException,
                        renderer=self.renderer_name)
