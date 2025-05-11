import curses, time, threading, gc, signal
from typing import Dict, List, Tuple, Optional
import config.constants as cfg
from core.model import TreeNode
from core.operations import flatten_tree
from ui.rendering import init_colors, Renderer
from ui.core.state import State
from ui.controls.manager import ControlManager
from ui.controls.keyboard import KeyboardEventHandler
from ui.controls.actions import ActionHandler
from core.utils.terminal import reset_terminal

class Application:
    def __init__(self, stdscr, root_node: TreeNode, path_to_node: Dict[str, TreeNode],
                 fmt: str, path_mode: str, tree_changed_flag: threading.Event, lock: threading.Lock):
        self.s = stdscr
        self.rn = root_node
        self.p2n = path_to_node
        self.fmt = fmt
        self.pm = path_mode
        self.tc_flag = tree_changed_flag
        self.l = lock
        self.resized = False
        self.fi = cfg.get_cli_refresh_interval()
        self._init()
        self._render()

    def _init(self):
        curses.curs_set(0); curses.noecho(); curses.cbreak()
        if hasattr(curses, "set_escdelay"):
            try: curses.set_escdelay(25)
            except: pass
        self.s.nodelay(True); self.s.keypad(True); self.s.timeout(0)
        self.s.clear(); self.s.refresh(); init_colors()
        signal.signal(signal.SIGINT, lambda *_: curses.ungetch(ord("q")))
        self.u = State()
        self.cache: List[Tuple[TreeNode, int, bool]] = []
        self.tot = 0
        self.sel: Optional[str] = None
        self.action_changed = False
        self.renderer = Renderer(self.s, self.u)
        self.cm = ControlManager(self.u)
        self.kb = KeyboardEventHandler(self.cm, self.u)
        self.ah = ActionHandler(self.s, self.u, self.rn, self.p2n,
                                self.fmt, self.pm, self.tc_flag, self.l)
        self.ah.register_handlers(self.cm)
        self.kb.setup(callback_fn=self._render)
        self._rebuild()

    def _rebuild(self):
        with self.l:
            self.tot = self.rn.calculate_token_count()
            self.cache = list(flatten_tree(self.rn, is_root=True))
            if self.cache and 0 <= self.u.current_index < len(self.cache):
                self.sel = self.cache[self.u.current_index][0].path

    def run(self):
        try:
            gc_t = time.perf_counter()
            nxt = time.perf_counter() + self.fi
            while not self.u.should_quit:
                now = time.perf_counter()
                if self.resized:
                    curses.endwin(); self.s.refresh(); self.resized = False; self._render()
                    nxt = now + self.fi
                redraw = self._events()
                if self._input(): redraw = True
                if redraw:
                    self._render()
                    nxt = now + self.fi
                if now - gc_t > 5.0:
                    gc.collect(); gc_t = now
                slp = nxt - time.perf_counter()
                if slp > 0: time.sleep(slp)
                else: nxt = time.perf_counter() + self.fi
        finally:
            self.kb.cleanup(); reset_terminal(self.s)

    def _events(self) -> bool:
        r = False
        if self.tc_flag.is_set():
            self._tree_change(); r = True
        if self.u.redraw_needed.is_set():
            self.u.redraw_needed.clear(); r = True
        if self.u.clear_success_if_expired(1.0): r = True
        return r

    def _input(self) -> bool:
        k = self.s.getch()
        if k == curses.KEY_RESIZE:
            self.resized = True
            return False
        if k != -1 and self.kb.handle_key(k):
            if self.tc_flag.is_set():
                self.action_changed = True
            return True
        return False

    def _tree_change(self):
        self._rebuild()
        with self.l:
            if self.sel:
                for i, (n, _, _) in enumerate(self.cache):
                    if n.path == self.sel:
                        self.u.current_index = i
                        break
            else:
                self.u.update_selected_index(0, len(self.cache))
            self.tc_flag.clear()
        self.action_changed = False
        self.sel = None

    def _render(self):
        rows = self.s.getmaxyx()[0] - 1
        with self.l:
            if self.action_changed:
                self.tot = self.rn.calculate_token_count()
                self.action_changed = False
            self.u.ensure_visible(rows, len(self.cache))
            cur = None
            if self.cache and 0 <= self.u.current_index < len(self.cache):
                cur = self.cache[self.u.current_index][0]
                self.ah.update_context(cur, self.cache)
            self.renderer.render(self.cache, cur, self.tot)

def run_application(stdscr,root_node:TreeNode,path_to_node:Dict[str,TreeNode],fmt:str,path_mode:str,tree_changed_flag:threading.Event,lock:threading.Lock):
    if hasattr(curses,"update_lines_cols"):curses.update_lines_cols()
    Application(stdscr,root_node,path_to_node,fmt,path_mode,tree_changed_flag,lock).run()
