from __future__ import absolute_import

import jsonschema

from mimeprovider.exceptions import MimeValidationError


class JsonSchemaValidator(object):
    def __init__(self, schema):
        self.schema = schema

    def validate(self, obj):
        try:
            jsonschema.validate(obj, self.schema)
        except Exception as e:
            raise MimeValidationError(str(e))


__validator__ = JsonSchemaValidator
