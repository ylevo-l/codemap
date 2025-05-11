from typing import List, Tuple
from core.model.tree_node import TreeNode
from ui.core.state import State

class NavigationHandler:
    def __init__(self, ui_state: State):
        self._u = ui_state

    def _step(self, shift: bool) -> int:
        return self._u.step_accel if shift else self._u.step_normal
    @staticmethod
    def _clamp(i: int, size: int) -> int:
        return 0 if size == 0 else max(0, min(size - 1, i))

    def navigate(self, direction: int, nodes: List[Tuple[TreeNode, int, bool]], shift: bool) -> int:
        if not nodes:
            return 0
        size = len(nodes)
        cur = self._clamp(self._u.current_index, size)
        delta = -self._step(shift) if direction < 0 else self._step(shift)
        dest = self._clamp(cur + delta, size)
        if dest == cur:
            return cur
        rng = range(cur - 1, dest - 1, -1) if direction < 0 else range(cur + 1, dest + 1)
        for i in rng:
            if nodes[i][0].is_dir:
                return i
        return dest
