from unittest import TestCase
import random
import string

import memcache

from memcache_ketama_client import MemcacheKetamaClient
from collections import defaultdict


class MemcacheClientTestCase(TestCase):
    def setUp(self):
        self.keys_count = 10_000
        random.seed(42)

        self.client = MemcacheKetamaClient(servers=[f'memcache{i}:11211' for i in range(1, 8)])

    def tearDown(self):
        if hasattr(self.client, 'hash_storage'):
            self.client.hash_storage.flushall()

        self.client.flush_all()
        del self.client

    def test_get_server__is_deterministic(self):
        keys = [str(i) for i in range(self.keys_count)]
        for key in keys:
            self.client.set(key, 1)

        result = self.client.get_multi(keys)
        self.assertEqual(self.keys_count, len(result))

    def test_default_add_server__missed_keys(self):
        keys = [str(i) for i in range(self.keys_count)]
        for key in keys:
            self.client.set(key, 1)

        result = self.client.get_multi(keys)
        self.assertEqual(self.keys_count, len(result))

        del self.client
        self.client = memcache.Client(servers=[f'memcache{i}:11211' for i in range(1, 9)])

        result_after_add_server = self.client.get_multi(keys)

        self.assertNotEqual(self.keys_count, len(result_after_add_server))

    def test_new_server__missed_keys(self):
        keys = [str(i) for i in range(self.keys_count)]
        for key in keys:
            self.client.set(key, 1)

        result = self.client.get_multi(keys)
        self.assertEqual(self.keys_count, len(result))

        del self.client
        self.client = MemcacheKetamaClient(servers=[f'memcache{i}:11211' for i in range(1, 9)])

        result_after_add_server = self.client.get_multi(keys)

        self.assertNotEqual(self.keys_count, len(result_after_add_server))

    def test_add_server__no_missed_keys(self):

        keys = [str(i) for i in range(self.keys_count)]
        for key in keys:
            self.client.set(key, 1)

        result = self.client.get_multi(keys)
        self.assertEqual(self.keys_count, len(result))

        self.client.add_server('memcache8:11211')

        del self.client
        self.client = MemcacheKetamaClient(servers=[f'memcache{i}:11211' for i in range(1, 9)])

        result_after_add_server = self.client.get_multi(keys)

        self.assertEqual(self.keys_count, len(result_after_add_server))

    def test_set_and_hash_storage__successful_hash_set_creation_after_set_command(self):
        key = self.generate_random_key()

        self.client.set(key, 1)

        self.assertEqual({str(self.client.ketama.get_server(key)[0]): {key}}, self.client.hash_storage.get_keys())

    def test_set_and_hash_storage__successful_hash_set_creation_after_delete_command(self):
        key = self.generate_random_key()

        self.client.set(key, 1)

        self.client.delete(key)

        self.assertEqual({}, self.client.hash_storage.get_keys())

    def test_set_and_hash_storage__successful_hash_set_creation_after_set_multi_command(self):

        random_keys = []
        for i in range(self.keys_count):
            random_keys.append(self.generate_random_key())

        mapping = {}
        for key in random_keys:
            mapping[key] = key

        self.client.set_multi(mapping)

        hash_keys_mapping = defaultdict(set)
        for key in random_keys:
            hash_keys_mapping[str(self.client.ketama.get_server(key)[0])].add(key)

        self.assertEqual(dict(hash_keys_mapping), self.client.hash_storage.get_keys())

    def test_set_and_hash_storage__successful_hash_set_creation_after_delete_multi_command(self):
        random_keys = []
        for i in range(self.keys_count):
            random_keys.append(self.generate_random_key())

        mapping = {}
        for key in random_keys:
            mapping[key] = key

        self.client.set_multi(mapping)

        self.client.delete_multi(mapping.keys())

        self.assertEqual({}, self.client.hash_storage.get_keys())

    def generate_random_key(self, length=8):
        characters = string.ascii_letters + string.digits  # All uppercase, lowercase letters and digits
        random_key = ''.join(random.choice(characters) for _ in range(length))
        return random_key

