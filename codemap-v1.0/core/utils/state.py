import os
import json
import tempfile
from typing import Any, Dict
from core.model.tree_node import TreeNode
from config.constants import STATE_FILE

def load_state(file_path: str) -> Dict[str, Any]:
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(file_path: str, state: Dict[str, Any]) -> None:
    try:
        dir_path = os.path.dirname(os.path.abspath(file_path)) or "."
        with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_path, encoding="utf-8") as tmp:
            json.dump(state, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, file_path)
    except:
        pass

def _rel(path: str, base: str) -> str:
    try:
        return os.path.relpath(path, base)
    except:
        return path

def apply_state(node: TreeNode, state: Dict[str, Any], base_path: str, is_root: bool = False) -> None:
    key = _rel(node.path, base_path)
    if is_root:
        node.expanded = True
    node_state = state.get(key, {})
    if node.is_dir:
        node.expanded = node_state.get("expanded", node.expanded)
    else:
        node.disabled = node_state.get("disabled", node.disabled or False)
    node.update_render_name()
    for child in node.children:
        apply_state(child, state, base_path)
    if is_root:
        node.calculate_token_count()

def gather_state(node: TreeNode, state: Dict[str, Any], base_path: str, is_root: bool = False) -> None:
    key = _rel(node.path, base_path)
    if node.is_dir:
        state[key] = {"expanded": node.expanded}
    else:
        state[key] = {"disabled": node.disabled}
    for child in node.children:
        gather_state(child, state, base_path)
