import tempfile

from collections import defaultdict
from typing import Dict, Tuple
from typing import List
from typing import Optional

import memcache
import ketama

from hash_storage import HashStorage


class MemcacheKetamaClient(memcache.Client):
    """ A memcache subclass. It currently allows you to add a new host at run
    time.

    Sadly, this truely messes with the our keys. I.E. Adding a host at runtime
    effectively wipes our cache all together...Wonder why?
    """

    def __init__(self, servers, *args, **kwargs):
        super(MemcacheKetamaClient, self).__init__(servers, *args, **kwargs)
        self.ketama: Optional[ketama.Ketama] = None
        self.points: Optional[Dict[int, str]] = None
        self._update_ketama()

        self.hash_storage = HashStorage()

    def add_server(self, server):
        """ Adds a host at runtime to client
        """
        server = memcache._Host(
            server, self.debug, dead_retry=self.dead_retry,
            socket_timeout=self.socket_timeout,
            flush_on_reconnect=self.flush_on_reconnect
        )
        self.servers.append(server)
        self.buckets.append(server)

        self._update_ketama()

        points = self.ketama.get_points()

        hash_keys_mapping = self.hash_storage.get_keys([
            points[i][0]
            for i in range(len(points))
            if points[i - 1][1] == (last_server := str(len(self.servers) - 1)) and points[i][1] != last_server
        ])

        self._redistribute([(int(key_hash), key) for key_hash in hash_keys_mapping for key in hash_keys_mapping[key_hash]])

        self.hash_storage.delete_keys({k: list(v) for k, v in hash_keys_mapping.items()})

    def _redistribute(self, keys: List[Tuple[int, str]]) -> None:
        # todo: batch
        values = self.get_multi(keys)

        self.delete_multi(values.keys())

        self.set_multi({k[1]: v for k, v in values.items()})

    def _get_server(self, key):
        """ Current implementation of Memcache client
        """
        if isinstance(key, tuple):
            serverhash, key = key
            virtual_node = self.points[serverhash]

        else:
            serverhash, virtual_node = self.ketama.get_server(key)

        if not self.buckets:
            return None, None

        for i in range(self.__class__._SERVER_RETRIES):
            server = self.buckets[int(virtual_node)]
            if server.connect():
                return server, key
            serverhash = str(serverhash) + str(i)
            if isinstance(serverhash, str):
                serverhash = serverhash.encode('ascii')
            serverhash, virtual_node = self.ketama.get_server(serverhash)

        return None, None

    def set(self, key, val, time=0, min_compress_len=0, noreply=False):
        super(MemcacheKetamaClient, self).set(key, val)
        self.hash_storage.add_keys(self._get_hash_keys_mapping([key]))

    def set_multi(self, mapping, time=0, key_prefix='', min_compress_len=0, noreply=False):
        super(MemcacheKetamaClient, self).set_multi(mapping, time, key_prefix, )

        keys = []
        for k in list(mapping.keys()):
            keys.append(key_prefix + k)

        self.hash_storage.add_keys(self._get_hash_keys_mapping(keys))

    def delete(self, key, noreply=False):
        super(MemcacheKetamaClient, self).delete(key, noreply)
        self.hash_storage.delete_keys(self._get_hash_keys_mapping([key]))

    def delete_multi(self, keys, time=0, key_prefix='', noreply=False):
        super(MemcacheKetamaClient, self).delete_multi(keys, time, key_prefix, noreply)

        keys_with_prefix = []

        for key in keys:
            if isinstance(key, tuple):
                serverhash, key = key
                key = key_prefix + key
                key = (serverhash, key)
            else:
                key = key_prefix + key

            keys_with_prefix.append(key)


        self.hash_storage.delete_keys(self._get_hash_keys_mapping(keys_with_prefix))

    def _update_ketama(self):
        # TODO weights
        with tempfile.NamedTemporaryFile(delete=False, mode='w+') as f:
            f.write(''.join([f'{i} 1\n' for i in range(len(self.servers))]))
            f.flush()
            filename = f.name

        del self.ketama
        self.ketama = ketama.Ketama(filename)

        self.points = {k: v for k, v in self.ketama.get_points()}

    def _get_hash_keys_mapping(self, keys: List[str]) -> Dict[str, List[str]]:
        hash_keys_mapping = defaultdict(list)

        for key in keys:
            if isinstance(key, tuple):
                serverhash, key = key
                hash_keys_mapping[serverhash].append(key)
            else:
                hash_keys_mapping[self.ketama.get_server(key)[0]].append(key)

        return hash_keys_mapping
