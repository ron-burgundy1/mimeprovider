from __future__ import absolute_import

from mimeprovider.documenttype import DocumentType

import json


class JsonDocumentType(DocumentType):
    """
    A clever document type that sets up specific MIME depending on the
    available documents.
    """
    custom_mime = True
    mime = "application/{o.object_type}+json"

    def parse(self, validator, cls, string):
        data = json.loads(string)
        if validator:
            validator.validate(cls, data)
        return cls.from_data(data)

    def render(self, validator, obj):
        data = obj.to_data()
        if validator:
            validator.validate(obj.__class__, data)
        return json.dumps(data)


__document_type__ = JsonDocumentType
