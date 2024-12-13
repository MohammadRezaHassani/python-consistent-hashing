# Implement consistent hashing for scaling Memcached cluster using ketama and Python Memcached Clinet 

## what is `consistent hashing`?

![My Image](https://media.licdn.com/dms/image/v2/D5612AQF7xNod2WiFqQ/article-cover_image-shrink_720_1280/article-cover_image-shrink_720_1280/0/1666715227884?e=1738800000&v=beta&t=m_8sCGFrZE6eimqhVt6HCgl_EGIAXu8gaKq8nHSAo5k)

Consistent hashing is a technique used in distributed systems to efficiently map data to nodes in a way that minimizes the need for rebalancing when nodes are added or removed. In traditional hashing, when a new node is added or removed, a large portion of the data needs to be rehashed, which can be inefficient. In contrast, consistent hashing distributes the data across a ring-like structure, where each node is assigned a position on the ring. When a piece of data is inserted, it is mapped to the nearest node in the clockwise direction. With consistent hashing, only a small portion of the data needs to be redistributed when a node is added or removed, making the system more scalable and resilient to changes in the node pool. This technique is widely used in distributed caching systems, load balancing, and data storage solutions. for more information you can visit [consistent hashing wikipedia page](https://en.wikipedia.org/wiki/Consistent_hashing)

## problem statement
As a developer, you're likely familiar with Memcached, a powerful tool used as a cache to reduce database load. Large companies like Meta use Memcached to improve load distribution and enhance performance. However, no good thing comes without its drawbacks.

One of the first things you'll notice is that the Memcached client interface is quite simple, primarily offering basic operations like `[set, get, delete]` and their multi-functions `(set_multi, get_multi, delete_multi)`. While these are sufficient for basic use cases, they lack more advanced features.

The real problem becomes evident when you dive into the Memcached client implementation, particularly the hashing algorithm it uses. The default Python Memcached client uses a straightforward hash function to assign servers, where it chooses a server based on the formula:
```python
server_hash % number_of_servers
```
While this seems simple, it presents a significant issue when it comes to scaling.
As you know, horizontal scaling is a common practice for distributing the load across multiple servers, especially when vertical scaling has its limitations. The issue arises when you add a new server to the system. Due to the basic hashing mechanism used by the client, some keys are lost. Why? Because the hashing strategy isn’t consistent.

This means that when you add a new server, the existing data distribution changes, resulting in a redistribution of the keys. The problem is that with a simple hash, many keys that were previously assigned to other servers might now end up on the new server, causing data loss or unnecessary rebalancing.

To solve this, we need a more sophisticated hashing mechanism: consistent hashing. This approach ensures that when a new server is added, only a minimal amount of data needs to be redistributed, and most importantly, we don’t lose any keys in the process. Consistent hashing enables horizontal scaling without disrupting the system and ensures data integrity across all requests.

## Tools we use
- `Ketama Library`(Consistent hashing algorithm we use for data retrieval and redistribution )
- `python Memcached Client`(Real Cache Storage for storing our key, value pairs)
- `Redis`(Hash Storage. we will discuss it later!!)

## Ketama and Consistent Hashing

Let's discuss **Ketama**, what it is, why we need it, and how we use it in the context of the **consistent hashing** problem for our Memcached client.

**Ketama** is an open-source library that implements the **consistent hashing** algorithm. It provides a simple interface with two main functions:

1. **get_server()**
2. **get_points()**

### 1. What is `get_server()`?

The `get_server()` function is responsible for determining which server a given key should be assigned to. It takes a key as input and returns a tuple containing the server hash and the server name (which is configured in the Ketama configuration file).

### 2. What is `get_points()`?

In the context of consistent hashing, we hash both the keys and the servers, mapping them onto a circular hash ring. The `get_points()` function returns the points on the ring that correspond to a given server. This is where Ketama introduces a key improvement over traditional consistent hashing: the concept of **virtual nodes (v-nodes)**.

### 3. What are v-nodes? How do they work and why do we need them?

Ketama improves on traditional consistent hashing by using **virtual nodes**. For each physical server, it maps multiple virtual nodes onto the hash ring. This means each real server is represented by several virtual nodes on the ring, improving the distribution of data.

### 4. How do v-nodes help with consistent hashing?

The use of v-nodes helps distribute data more evenly across the servers. In traditional consistent hashing, each physical server is represented by a single point on the ring. But by using virtual nodes, Ketama ensures that the data is distributed more uniformly, preventing any server from becoming overloaded and improving overall system performance.

### 5. How to use Ketama?

Ketama uses a configuration file to define the servers. Each server is assigned a name and a weight. For simplicity, we often use a weight of `1` for each server. A sample Ketama configuration file might look like this:

```text
server_1 1
server_2 1
server_3 1
```

This configuration defines three servers. Ketama then maps each server to 160 points on the hash ring. The total number of points on the ring is therefore:

```text
number_of_servers * 160
```

# How Ketama Handles Data Redistribution When Adding a Node



When a new node is added to the system, the **Ketama** consistent hashing algorithm ensures that data redistribution is efficient. Instead of redistributing all the data across all nodes, Ketama only redistributes the minimal amount of data necessary, making the process much more efficient.

The key concept here is that the amount of data that needs to be moved is proportional to the total data divided by the new number of nodes, rather than requiring a complete redistribution.

### How Ketama Works When Adding a Node

When a new node is added to the system, 160 points are added to the **hash ring**. However, the **Ketama** algorithm only redistributes the keys that are directly affected by the new node. 

This means that the redistribution of keys is not an all-or-nothing process; only the keys that map to the newly added points on the ring are reassigned to the new node. The remaining data stays where it was, minimizing the data movement.

### Example: Efficient Data Redistribution

Let's consider an example where we start with 3 nodes and then add a 4th node to the system.

#### Initial Setup (3 Nodes)
- **Total Data**: 300 keys
- **Nodes**: 3
- **Data per node**: 300 keys / 3 nodes = 100 keys per node

In this setup, each of the 3 nodes is responsible for 100 keys. The data is distributed evenly across the 3 nodes.

#### Adding a New Node (4 Nodes)

Now, let's say we add a 4th node to the system and update the **Ketama** configuration. With the new node, 160 points are added to the hash ring.

- **New nodes**: 4
- **Total data**: 300 keys
- **Data per node**: 300 keys / 4 nodes = 75 keys per node

#### Data Redistribution After Adding the New Node

In the case of Ketama's consistent hashing, only the keys that are assigned to the newly added points on the hash ring need to be moved. This means that only 75 keys will be redistributed to the new node, while the remaining 225 keys will stay with their existing nodes.

### Why This Is Efficient

In traditional hashing, adding a new node often leads to the redistribution of all the data, which can be inefficient and cause performance issues. In contrast, Ketama ensures that only a small portion of the data (proportional to the total data divided by the new number of nodes) needs to be moved.

#### Key Takeaways:
- **Before adding the node**: Each of the 3 nodes handles 100 keys.
- **After adding the node**: Only 75 keys are redistributed to the new node, and the remaining 225 keys stay in their original locations.

This makes **Ketama** much more efficient, as it minimizes the amount of data that needs to be moved when scaling the system.

### ketama Benefit

The ability to add new nodes with minimal data redistribution is one of the key advantages of using **consistent hashing** and **Ketama**. By only redistributing the necessary data (proportional to the number of nodes), Ketama ensures that the system scales efficiently without unnecessary overhead.

This is the power of consistent hashing in practice — as the number of nodes increases, the amount of data that needs to be moved remains relatively small, making the process more scalable and less resource-intensive.

# Why Do We Need Redis?

The decision to use **Redis** is based on the context of the problem. While you may choose another solution depending on your specific use case, we believe **Redis** is a great fit for our problem due to several key factors:

1. Its robust data structures
2. Fast query response times

## Data Redistribution When Adding a Node

When a new node is added, we have several options for data redistribution:

1. Load all the data from the servers whose keys need to be transferred to the newly added node.
2. Only load the fraction of data from the target servers that needs to be transferred to the new node.

The first approach comes with a significant overhead since it requires loading all keys from the entire system. To avoid this, we opted for a more efficient approach using a heuristic to load only the relevant portion of data. This is where **Redis** comes into play.

## How Redis Helps with Data Redistribution

When a new node is added, the **Ketama** algorithm determines which virtual nodes' data should be redistributed. To optimize the data transfer, we leverage Redis' **set data structures**. Here's how it works:

- For each **v-node hash**, we store all the related keys in a Redis set.
- When it's time to transfer the data, we query the appropriate Redis set for the specific hash and only load the related keys, rather than loading all the server keys.

This approach minimizes the data that needs to be moved and ensures we are only working with the relevant data during the redistribution process. By using Redis' hash storage and set data structures, we can efficiently handle data redistribution with minimal overhead.

### Why Redis?

The combination of **Redis' fast querying** and its ability to store and manage data in an efficient way makes it the perfect tool for our solution. Instead of dealing with large data sets from entire servers, Redis allows us to load only the data we need, making the system scalable and efficient.


# How to Run the Code

To run the application and perform the tests, follow these simple steps:

1. **Start the application using Docker Compose:**
   ```bash
   docker-compose up
   ```
2. **Access the running container**: Once the containers are up, enter the Python application container using the following command:
   ```bash
    docker exec -it python-app bash
   ```
   
3. **Run the tests: Inside the container**: run all the 9 tests that we have prepared for you using pytest:
    ```bash
    pytest
    ```
    
## Summary
By running these steps, you can easily start the application and verify that the system is functioning as expected with the pre-written tests. Pytest will provide you with a summary of the test results, so you can quickly spot any issues and address them.


