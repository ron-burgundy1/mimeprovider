from mimeprovider.documenttype import DocumentType

import pprint


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
        context.validate(obj.__class__, data)
        pp = pprint.PrettyPrinter(indent=4, depth=1)
        return pp.pformat(data)


__document_type__ = TextDocumentType
