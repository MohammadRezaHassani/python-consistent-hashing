from unittest import TestCase

from hash_storage import HashStorage


class HashStorageTestCase(TestCase):
    def setUp(self):
        self.keys_count = 100
        self.storage = HashStorage()
        self.storage.flushall()

    def test_hash_storage__set_operations(self):
        hash_value = "test_set"

        keys = [str(i) for i in range(self.keys_count)]

        self.storage.add_keys({hash_value: keys})

        self.assertEqual({hash_value: set(keys)}, self.storage.get_keys())

        self.storage.delete_keys({hash_value: keys})

        self.assertEqual({}, self.storage.get_keys())
