import os
import threading
from typing import Dict, Set, Deque
from collections import deque

from core.model.tree_node import TreeNode
from core.operations.tokens import token_count_manager, update_node_token_count
from core.filesystem.file_filter import FileFilter

def build_tree(root_path: str, file_filter: FileFilter,
               path_to_node: Dict[str, TreeNode], lock: threading.Lock) -> TreeNode:
    root_node = TreeNode(root_path, True)
    root_node.expanded = True
    with lock:
        path_to_node[root_path] = root_node
    queue: Deque[TreeNode] = deque([root_node])
    processed_dirs: Set[str] = set([root_path])
    token_count_tasks = 0
    while queue:
        current_dir_node = queue.popleft()
        dir_path = current_dir_node.path
        try:
            contents = os.listdir(dir_path)
            dirs = []
            files = []
            for name in contents:
                if file_filter.is_ignored(name):
                    continue
                full_path = os.path.join(dir_path, name)
                if os.path.isdir(full_path):
                    dirs.append(name)
                else:
                    files.append(name)
            for dirname in sorted(dirs, key=str.lower):
                full_path = os.path.join(dir_path, dirname)
                if full_path in processed_dirs:
                    continue
                processed_dirs.add(full_path)
                with lock:
                    dir_node = TreeNode(full_path, True, current_dir_node)
                    current_dir_node.add_child(dir_node)
                    path_to_node[full_path] = dir_node
                queue.append(dir_node)
            for filename in sorted(files, key=str.lower):
                full_path = os.path.join(dir_path, filename)
                with lock:
                    file_node = TreeNode(full_path, False, current_dir_node)
                    def token_count_callback(node_path: str, token_count: int) -> None:
                        with lock:
                            node = path_to_node.get(node_path)
                            if node and not node.is_dir:
                                update_node_token_count(node, token_count)
                    if token_count_tasks < 50:
                        token_count_manager.queue_token_count(full_path, token_count_callback)
                        token_count_tasks += 1
                    current_dir_node.add_child(file_node)
                    path_to_node[full_path] = file_node
        except (PermissionError, FileNotFoundError, OSError):
            continue
    file_filter.clear_cache()
    root_node.calculate_token_count()
    return root_node
