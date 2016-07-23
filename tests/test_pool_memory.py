import unittest
import random
from multiprocessing import Pool
import gc
import time


def task(data):
    return [x**x for x in data]


class PoolMemoryCase(unittest.TestCase):
    def setUp(self):
        self.data = [random.random() for _ in range(5000000)]

        self.pool = Pool()
        self.results = {}
        pass

    def tearDown(self):
        pass

    def test_memory(self):
        for i in range(5):
            self.results[i] = self.pool.map_async(task, [self.data])

        for i in self.results.keys():
            self.results[i].wait()
            print "result", i, len(self.results[i].get()[0])
            del self.results[i]

        print "ended"
        time.sleep(5)

        del self.data
        self.pool.close()

        time.sleep(2)

        gc.collect()
        print "collected", self.pool

        time.sleep(5)
        print "exit"
