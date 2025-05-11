from collections import OrderedDict,deque
from threading import Lock
from typing import TypeVar,Optional,Generic,Tuple,List

K=TypeVar("K")

V=TypeVar("V")

class LRUCache(Generic[K,V]):
    def __init__(self,max_size:int=1000):
        self.max_size=max_size
        self._cache:OrderedDict[K,V]=OrderedDict()
        self._lock=Lock()

    def get(self,key:K,default:Optional[V]=None)->Optional[V]:
        with self._lock:
            if key in self._cache:
                val=self._cache.pop(key)
                self._cache[key]=val
                return val
            return default

    def put(self,key:K,val:V)->None:
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
            elif len(self._cache)>=self.max_size:
                self._cache.popitem(last=False)
            self._cache[key]=val

    def prune(self,n:int)->None:
        with self._lock:
            for _ in range(min(n,len(self._cache))):
                self._cache.popitem(last=False)

    def clear(self)->None:
        with self._lock:self._cache.clear()

    def __contains__(self,key:K)->bool:
        with self._lock:return key in self._cache

    def __len__(self)->int:
        with self._lock:return len(self._cache)

    def items(self)->List[Tuple[K,V]]:
        with self._lock:return list(self._cache.items())
