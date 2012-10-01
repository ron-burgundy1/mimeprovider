from __future__ import absolute_import

from mimeprovider.documenttype import DocumentType

import pprint


class TextDocumentType(DocumentType):
    """
    Stupid docoument type that just returns a nicely formatted version of your
    data.
    """
    custom_mime = False
    mime = "text/plain"

    def parse(self, validator, cls, string):
        raise RuntimeError("parse not implemented")

    def render(self, validator, obj):
        data = obj.to_data()
        if validator:
            validator.validate(obj.__class__, data)
        pp = pprint.PrettyPrinter(indent=4, depth=1)
        return pp.pformat(data)


__document_type__ = TextDocumentType
