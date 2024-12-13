import random
import string
from memcache_ketama_client import MemcacheKetamaClient


def random_key(size):
    """ Generates a random key
    """
    return ''.join(random.choice(string.ascii_letters) for _ in range(size))


if __name__ == '__main__':
    # We have 7 running memcached servers
    servers = ['memcache{}:11211'.format(i) for i in range(1, 8)]
    # We have 100 keys to split across our servers
    keys = [random_key(10) for i in range(100)]
    # Init our subclass
    client = MemcacheKetamaClient(servers=servers)
    # Distribute the keys on our servers
    for key in keys:
        client.set(key, 1)

    # Check how many keys come back
    valid_keys = client.get_multi(keys)
    print('{} percent of keys matched'.format(((len(valid_keys) / float(len(keys))) * 100)))

    # We add another server...and pow!
    client.add_server('memcache8:11211')
    # print('Added new server')

    valid_keys = client.get_multi(keys)
    print('{} percent of keys still matched'.format(((len(valid_keys) / float(len(keys))) * 100)))



