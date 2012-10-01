class Client(object):
    def get(self, uri, **kw):
        return self.request('GET', uri, **kw)

    def post(self, uri, **kw):
        return self.request('POST', uri, **kw)

    def head(self, uri, **kw):
        return self.request('HEAD', uri, **kw)

    def put(self, uri, **kw):
        return self.request('PUT', uri, **kw)


def get_default_client():
    from mimeprovider.client.requests import RequestsClient
    return RequestsClient
