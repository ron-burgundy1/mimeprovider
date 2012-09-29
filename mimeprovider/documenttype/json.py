from mimeprovider.documenttype import DocumentType

import json


class JsonDocumentType(DocumentType):
    """
    A clever document type that sets up specific MIME depending on the
    available documents.
    """
    custom_mime = True
    mime = "application/{o.object_type}+json"

    def parse(self, context, cls, string):
        data = json.loads(string)
        context.validate(cls, data)
        return cls.from_data(context, data)

    def render(self, context, obj):
        data = obj.to_data(context)
        context.validate(obj.__class__, data)
        return json.dumps(data)


__document_type__ = JsonDocumentType
