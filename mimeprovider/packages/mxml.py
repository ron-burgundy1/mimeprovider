import xml.sax.saxutils as s

STRING = "string"
ELEMENT = "element"


def _open_tag(item):
    buf = list()
    buf.append("<{0}".format(item.tag))

    if item.attributes:
        for k, v in item.attributes.items():
            buf.append(" {0}={1}".format(k, s.quoteattr(v)))

    buf.append(">")
    return "".join(buf)


def _close_tag(item):
    return "</{0}>".format(item.tag)


class mXml(object):
    def __init__(self, tag, **kw):
        self.tag = tag
        self.attributes = dict((k.strip("_"), v) for k, v in kw.items())
        self.children = list()

    def add(self, tag, **kw):
        element = mXml(tag, **kw)
        self.children.append((ELEMENT, element))
        return element

    def adds(self, string):
        """
        Add a string child.
        """
        self.children.append((STRING, str(string)))

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __getitem__(self, key, value):
        return self.attributes[key]

    def _build_string(self):
        item = self

        yield _open_tag(item)

        for child_type, child in item.children:
            if child_type == STRING:
                yield s.escape(child)
                continue

            yield "".join(child._build_string())

        yield _close_tag(item)

    def __str__(self):
        return "".join(self._build_string())

    def __repr__(self):
        return "<{0} childen={1}>".format(self.tag, self.children)
