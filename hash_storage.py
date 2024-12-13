import os

from typing import List, Optional, Set
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

import redis


# TODO lint

class HashStorage:
    """
    we use redis for storing the v-node hashes in and redistributing the data
    you can use any other thing base on your purpose
    """

    def __init__(self, redis_host=None, redis_port=None, prefix=''):
        self.prefix = f'{prefix}:' if prefix else ''
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'redis')
        self.redis_port = redis_port or int(os.getenv('REDIS_PORT', 6379))
        self.redis_client = redis.StrictRedis(host=self.redis_host, port=self.redis_port, db=0)

    def add_keys(self, hash_keys_mapping: Dict[str, List[str]]):
        with ThreadPoolExecutor(max_workers=10) as executor:  # todo: Adjust number of workers
            for k, v in hash_keys_mapping.items():
                executor.submit(self._add_keys, k, v)

    def delete_keys(self, hash_keys_mapping: Dict[str, List[str]]):
        with ThreadPoolExecutor(max_workers=10) as executor:  # todo: Adjust number of workers
            for k, v in hash_keys_mapping.items():
                executor.submit(self._delete_keys, k, v)

    def get_keys(self, key_hashes: Optional[List[str]] = None) -> Dict[str, Set[str]]:
        if not key_hashes:
            key_hashes = [key_hash.decode('utf-8') for key_hash in self.redis_client.keys(f'{self.prefix}*')]
        else:
            key_hashes = [f'{self.prefix}{key_hash}' for key_hash in key_hashes]

        # TODO send only one q to redis and remove call to this func
        return {h: set(self._get_keys(h)) for h in key_hashes}

    def _get_keys(self, key_hash: str) -> List[str]:
        return [k.decode('utf-8') for k in self.redis_client.smembers(f'{self.prefix}{key_hash}')]

    def _add_keys(self, key_hash, keys: List[str]):
        return self.redis_client.sadd(f'{self.prefix}{key_hash}', *keys)

    def _delete_keys(self, key_hash, keys):
        if not keys:
            self.redis_client.delete(f'{self.prefix}{key_hash}')
            return

        self.redis_client.srem(f'{self.prefix}{key_hash}', *keys)

    def flushall(self):
        self.redis_client.flushall()
