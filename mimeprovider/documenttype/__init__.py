import importlib


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


DEFAULT_DOCUMENT_TYPES = [
    "mimeprovider.documenttype.html",
    "mimeprovider.documenttype.json",
    "mimeprovider.documenttype.text",
]


def get_default_document_types():
    result = list()

    for module in DEFAULT_DOCUMENT_TYPES:
        m = importlib.import_module(module)
        result.append(m.__document_type__)

    return result
