import sys
import logging

from pyramid.httpexceptions import HTTPError

from mimeprovider import MimeProvider


class BaseObject(object):
    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)
        self.__keys__ = kw.keys()

    def to_data(self):
        return dict((k, getattr(self, k, None)) for k in self.__keys__)

    @classmethod
    def from_data(cls, BaseObject):
        return cls(**BaseObject)


class SomeData(BaseObject):
    schema = {
        "type": "object",
        "properties": {
            "string": {
                "type": "string",
                "required": True,
            },
            "integer": {
                "type": "number",
                "required": True,
            },
            "somelist": {
                "type": "array",
                "required": True,
            },
        }
    }

    object_type = "somedata"


class Error(BaseObject):
    schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "required": True,
            }
        }
    }

    object_type = "error"


def example_endpoint(request):
    if request.mime_body:
        body = request.mime_body
        print "== got a request body =="
        print "string:", body.string
        print "integer:", body.integer
        print "somelist:", body.somelist

    return SomeData(string="Hello World", integer=12, somelist=["Foo", "Bar"])


def http_errors(exc, request):
    request.response.status_code = exc.status_code
    return Error(message=exc.title)


def mime_error_handler(exc, request):
    request.response.status_code = exc.status_code
    return Error(message=str(exc))


def other_exceptions(exc, request):
    logging.error("Unhandled framework error", exc_info=sys.exc_info())
    request.response.status_code = 500
    return Error(message="Unhandled server error")


from pyramid.config import Configurator
from wsgiref.simple_server import make_server

# provide a list of document types.
document_types = [
    Error,
    SomeData
]

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    config = Configurator()
    config.add_route('example', '/example/{name}')

    config.add_view(example_endpoint, route_name='example', renderer='mime')

    # error handler to convert HTTPError's to the correct response type.
    config.add_view(http_errors, context=HTTPError, renderer='mime')
    config.add_view(other_exceptions, context=Exception, renderer='mime')

    provider = MimeProvider(document_types, error_handler=mime_error_handler)
    config.include(provider.add_config)

    app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 8080, app)
    server.serve_forever()
