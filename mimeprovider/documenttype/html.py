from __future__ import absolute_import

from mimeprovider.documenttype import DocumentType

from mimeprovider.packages.mxml import mXml


def _build_data(first_element, first_data):
    queue = list([(first_element, first_data)])

    while len(queue) > 0:
        element, data = queue.pop()

        if isinstance(data, list):
            table = element.add("table", cellspacing="0", cellpadding="2")

            for i, item in enumerate(data):
                tr = table.add("tr")
                sequence = tr.add("th")
                sequence.adds(i)
                value = tr.add("td", style="padding: 0 2px", align="left")
                queue.insert(0, (value, item))

            continue

        if isinstance(data, dict):
            ref = data.get("$ref")

            if ref is not None:
                rel = data.get("rel", ref)
                link = element.add("a", href=ref)
                link.adds(rel)
                continue

            table = element.add("table", cellspacing="0", cellpadding="2")

            for k, v in sorted(data.items()):
                tr = table.add("tr")
                title = tr.add("th", valign="top", align="right")
                title.adds("{0}:".format(k))
                value = tr.add("td", style="padding: 0 2px;", align="left")
                queue.insert(0, (value, v))

            continue

        element.adds("{0!s}".format(data))


class HtmlDocumentType(DocumentType):
    """
    Sneaky document type that attempt to build your sorry attempt of data into
    a html viewable structure.
    """
    custom_mime = False
    mime = "text/html"

    def parse(self, validator, cls, string):
        raise RuntimeError("parse not implemented")

    def render(self, validator, obj):
        data = obj.to_data()

        if validator:
            validator.validate(obj.__class__, data)

        html = mXml("html")
        head = html.add("head")
        title = head.add("title")
        body = html.add("body")

        title.adds("Data")

        heading = body.add("h1")
        heading.adds("{0} ({1})".format(obj.object_type, type(obj).__name__))

        _build_data(body, data)

        return str(html)


__document_type__ = HtmlDocumentType
