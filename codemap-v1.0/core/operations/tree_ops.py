from typing import Generator, Tuple, Set, Optional

from core.model.tree_node import TreeNode

def toggle_node(node: TreeNode) -> None:
    if node.is_dir:
        node.expanded = not node.expanded
        node.update_render_name()

def set_subtree_expanded(node: TreeNode, expanded: bool) -> None:
    if node.is_dir:
        node.expanded = expanded
        node.update_render_name()
        for child in node.children:
            set_subtree_expanded(child, expanded)

def toggle_subtree(node: TreeNode) -> None:
    if node.is_dir:
        set_subtree_expanded(node, not node.expanded)

def flatten_tree(node: TreeNode, depth: int = 0, visited: Optional[Set[str]] = None, is_root: bool = True) -> Generator[Tuple[TreeNode, int, bool], None, None]:
    if visited is None:
        visited = set()
    if node.path in visited:
        return
    visited.add(node.path)
    show_tokens = False
    if is_root and node.token_count > 0:
        show_tokens = True
    yield (node, depth, show_tokens)
    if node.is_dir and node.expanded:
        for child in node.children:
            yield from flatten_tree(child, depth + 1, visited, False)

def are_all_files_enabled(node: TreeNode) -> bool:
    if not node.is_dir:
        return not node.disabled
    for child in node.children:
        if child.is_dir:
            if not are_all_files_enabled(child):
                return False
        else:
            if child.disabled:
                return False
    return True

def toggle_folder_enable_state(node: TreeNode, enable: bool) -> None:
    if not node.is_dir:
        return
    for child in node.children:
        if child.is_dir:
            toggle_folder_enable_state(child, enable)
        else:
            child.disabled = not enable
            child.update_render_name()
