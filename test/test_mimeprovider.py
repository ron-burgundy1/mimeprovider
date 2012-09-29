import unittest

from mimeprovider import MimeProvider


class TestMimeProvider(unittest.TestCase):
    def test_register(self):
        class A:
            object_type = "foo"

        class B:
            object_type = "bar"

        mimeprovider = MimeProvider([A])
        mimeprovider.register(B)

        for i in mimeprovider.type_instances:
            self.assertTrue(i.get_mimetype(A) in mimeprovider.mimetypes)
            self.assertTrue(i.get_mimetype(B) in mimeprovider.mimetypes)


if __name__ == "__main__":
    unittest.main()
