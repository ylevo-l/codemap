import os
import threading
from typing import Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from core.model.tree_node import TreeNode
from core.operations.tokens import update_node_token_count, token_count_manager
from core.filesystem.file_filter import FileFilter

class _WatchdogHandler(FileSystemEventHandler):
    def __init__(
        self,
        root_path: str,
        file_filter: FileFilter,
        path_to_node: Dict[str, TreeNode],
        tree_changed_flag: threading.Event,
        lock: threading.Lock,
    ) -> None:
        super().__init__()
        self.root_path = root_path
        self.file_filter = file_filter
        self.path_to_node = path_to_node
        self.tree_changed_flag = tree_changed_flag
        self.lock = lock

    def _add_file(self, path: str, is_dir: bool) -> None:
        parent_path = os.path.dirname(path)
        node_added = False
        new_node = None
        with self.lock:
            parent = self.path_to_node.get(parent_path)
            if parent and parent.is_dir and path not in self.path_to_node:
                new_node = TreeNode(path, is_dir, parent)
                parent.add_child(new_node)
                parent.sort_children()
                self.path_to_node[path] = new_node
                node_added = True
        if node_added:
            self.tree_changed_flag.set()
            if not is_dir and new_node:
                token_count_manager.queue_token_count(path, self._token_cb)

    def _remove_file(self, path: str) -> None:
        node_removed = False
        original_count = 0
        parent_node = None
        is_file = False
        is_disabled = False
        parent_was_expanded = False
        with self.lock:
            node = self.path_to_node.pop(path, None)
            if node:
                node_removed = True
                parent_node = node.parent
                is_file = not node.is_dir
                if is_file:
                    is_disabled = node.disabled
                    original_count = node.token_count
                if parent_node:
                    parent_was_expanded = parent_node.expanded
                    try:
                        parent_node.children.remove(node)
                    except ValueError:
                        pass
                if is_file and not is_disabled and original_count > 0 and parent_node and parent_was_expanded:
                    curr = parent_node
                    while curr and curr.expanded:
                        curr.token_count -= original_count
                        curr = curr.parent
        if node_removed:
            self.tree_changed_flag.set()

    def _token_cb(self, node_path: str, count: int) -> None:
        node_updated = False
        with self.lock:
            node = self.path_to_node.get(node_path)
            if node and not node.is_dir:
                 changed = update_node_token_count(node, count)
                 if changed:
                    node_updated = True
        if node_updated:
             self.tree_changed_flag.set()

    def on_created(self, event: FileSystemEvent):
        base_name = os.path.basename(event.src_path)
        if self.file_filter.is_ignored(base_name):
            return
        if not event.is_directory:
             _, ext = os.path.splitext(base_name)
             if self.file_filter.allowed_extensions and ext.lower() not in self.file_filter.allowed_extensions:
                 return
        self._add_file(event.src_path, event.is_directory)

    def on_deleted(self, event: FileSystemEvent):
        self._remove_file(event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        base_name = os.path.basename(event.src_path)
        if self.file_filter.is_ignored(base_name):
            return
        _, ext = os.path.splitext(base_name)
        if self.file_filter.allowed_extensions and ext.lower() not in self.file_filter.allowed_extensions:
            return
        token_count_manager.queue_token_count(event.src_path, self._token_cb, force_update=True)

    def on_moved(self, event: FileSystemEvent):
        self._remove_file(event.src_path)
        dest_base_name = os.path.basename(event.dest_path)
        if self.file_filter.is_ignored(dest_base_name):
             return
        if not event.is_directory:
             _, ext = os.path.splitext(dest_base_name)
             if self.file_filter.allowed_extensions and ext.lower() not in self.file_filter.allowed_extensions:
                 return
        self._add_file(event.dest_path, event.is_directory)

def watch_filesystem(
    root_path: str,
    file_filter: FileFilter,
    path_to_node: Dict[str, TreeNode],
    tree_changed_flag: threading.Event,
    stop_event: threading.Event,
    lock: threading.Lock,

) -> None:
    handler = _WatchdogHandler(root_path, file_filter, path_to_node, tree_changed_flag, lock)
    observer = Observer()
    observer.schedule(handler, root_path, recursive=True)
    observer.start()
    try:
        stop_event.wait()
    finally:
        observer.stop()
        observer.join()
