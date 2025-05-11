from __future__ import annotations
import threading,time,gc
from core.model.tree_node import TreeNode
from core.utils.debug import log
import core.utils.clipboard as clip

def _loop(interval,token_mgr,file_filter):
    while True:
        try:
            token_mgr.trim_cache()
            clip.trim_caches()
            if file_filter:file_filter.clear_cache()
            TreeNode.clear_caches()
            gc.collect()
            log("MAINTENANCE")
        except:pass
        time.sleep(interval)

def start_maintenance(token_manager,file_filter=None,interval:float=60.0):
    t=threading.Thread(target=_loop,args=(max(5.0,interval),token_manager,file_filter),daemon=True,name="cm_maint")
    t.start()
    return t
