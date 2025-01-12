#!/usr/bin/env python3
# Version: 1.5.0

"""
Scrollable, interactive ASCII tree view of a directory with the following features:

1. SHIFT-based subtree actions: expand/collapse, anonymize/de-anonymize.
2. Single-folder toggles: expand/collapse, anonymize/de-anonymize.
3. Single-file toggles: enable/disable to exclude files from clipboard copying.
4. Clipboard copying of visible, enabled files with a progress bar.
5. Full state persistence: expanded, anonymized, file enablement.
6. Single-file, efficient code with no extra modules.
7. Optional SHIFT-based accelerated navigation for UP/DOWN and W/S.

Usage:
- [W]/[S]: Navigate the tree (accelerate if SHIFT is detected)
- [e]/[E]: Expand/collapse a single folder or entire subtree
- [a]/[A]: Anonymize/de-anonymize a single folder or entire subtree
- [d]: Enable/disable a single file
- [c]: Copy all visible, enabled files to the clipboard
- [q]: Quit (saves state to .tree_state.json)
"""

import argparse, curses, json, os, random, string, subprocess, sys, threading, time
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Generator
import tiktoken

STATE_FILE = ".tree_state.json"
SUCCESS_MESSAGE_DURATION = 1.0
IGNORED_PATTERNS = [
    "__pycache__", "node_modules", "dist", "build", "venv",
    ".git", ".svn", ".hg", ".idea", ".vscode",
    ".env", ".DS_Store", "Thumbs.db", ".bak", ".tmp",
    "desktop.ini", ".log", ".db", ".key", ".pyc",
    ".exe", ".dll", ".so", ".dylib"
]
ALLOWED_EXTENSIONS = [
    ".py", ".pyi", ".pyc", ".pyo", ".pyd", ".txt", ".md", ".rst",
    ".docx", ".pdf", ".odt", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".sh", ".bash", ".zsh", ".csh", ".ksh",
    ".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".tsx",
    ".jsx", ".mjs", ".cjs", ".pl", ".php", ".tcl", ".lua",
    ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".go",
    ".rs", ".swift", ".vb", ".fs", ".sql", ".html",
    ".htm", ".css", ".scss", ".sass", ".less", ".xml"
]
COPY_FORMAT_PRESETS = {
    "blocks": "{path}:\n\"\"\"\n{content}\n\"\"\"\n",
    "lines": "{path}: {content}\n",
    "raw": "{content}\n",
}
SCROLL_SPEED = {"normal": 1, "accelerated": 5}
MAX_TREE_DEPTH = 10
ANONYMIZED_PREFIXES = [
    "Archive", "DataSet", "Library", "Module", "Component", "Resource",
    "Asset", "Document", "Record", "Media", "Collection", "Repository",
    "Bundle", "Package", "Catalog", "Inventory", "Ledger", "Index",
    "Database", "System", "Network", "Platform", "Framework", "Utility",
    "Tool", "Service", "Gateway", "Interface", "Connector", "Adapter"
]
INPUT_TIMEOUT = 0.1

try:
    ENCODING = tiktoken.encoding_for_model("gpt-4o")
except KeyError:
    print("Error: Model encoding not found.")
    sys.exit(1)

def count_tokens(content: str) -> int:
    return len(ENCODING.encode(content))

def copy_text_to_clipboard(t: str) -> None:
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True).communicate(input=t.encode("utf-16"))
        elif sys.platform.startswith("darwin"):
            subprocess.Popen("pbcopy", stdin=subprocess.PIPE).communicate(input=t.encode("utf-8"))
        else:
            subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE).communicate(input=t.encode("utf-8"))
    except:
        pass

def strike(text: str) -> str:
    return '\u0336' + text + '\u0336'

class FileFilter:
    def __init__(self, ignored_patterns: List[str], allowed_extensions: List[str]):
        self.ignored_patterns = ignored_patterns
        self.allowed_extensions = allowed_extensions

    def is_ignored(self, name: str) -> bool:
        if any(p in name for p in self.ignored_patterns):
            return True
        _, ext = os.path.splitext(name)
        return bool(self.allowed_extensions and ext and ext.lower() not in self.allowed_extensions)

class TreeNode:
    def __init__(self, path: str, is_dir: bool, parent: Optional['TreeNode'] = None):
        self.path = path
        self.is_dir = is_dir
        self.expanded = False if is_dir else None
        self.original_name = os.path.basename(path)
        self.display_name = self.original_name
        self.render_name = self.original_name
        self.anonymized = False
        self.disabled = False if not is_dir else None
        self.children: List['TreeNode'] = []
        self.token_count: int = 0
        self.parent = parent

    def add_child(self, child: 'TreeNode') -> None:
        self.children.append(child)

    def sort_children(self) -> None:
        self.children.sort(key=lambda x: (not x.is_dir, x.display_name.lower()))

    def calculate_token_count(self) -> int:
        if not self.is_dir:
            return 0 if self.disabled else self.token_count
        self.token_count = sum(child.calculate_token_count() for child in self.children if (child.is_dir and child.expanded) or (not child.is_dir and not child.disabled))
        return self.token_count

    def update_token_count(self, delta: int) -> None:
        self.token_count += delta
        if self.parent:
            self.parent.update_token_count(delta)

    def update_render_name(self) -> None:
        self.render_name = self.display_name if self.is_dir else (strike(self.display_name) if self.disabled else self.display_name)

def build_tree(root_path: str, file_filter: FileFilter, path_to_node: Dict[str, TreeNode], lock: threading.Lock) -> TreeNode:
    root = TreeNode(root_path, True)
    root.expanded = True
    with lock:
        path_to_node[root_path] = root

    def recurse(node: TreeNode, current_path: str, depth: int) -> bool:
        if depth > MAX_TREE_DEPTH:
            return False
        try:
            entries = sorted(os.listdir(current_path))
        except PermissionError:
            return False
        has_children = False
        for entry in entries:
            if file_filter.is_ignored(entry):
                continue
            full_path = os.path.join(current_path, entry)
            is_dir = os.path.isdir(full_path)
            child = TreeNode(full_path, is_dir, node)
            if is_dir:
                if recurse(child, full_path, depth + 1):
                    node.add_child(child)
                    path_to_node[full_path] = child
                    has_children = True
            else:
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        child.token_count = count_tokens(f.read())
                except:
                    child.token_count = 0
                if not child.disabled:
                    node.update_token_count(child.token_count)
                node.add_child(child)
                path_to_node[full_path] = child
                has_children = True
        if has_children:
            node.sort_children()
            return True
        return False

    recurse(root, root_path, 0)
    root.calculate_token_count()
    return root

def load_state(file_path: str) -> Dict[str, Any]:
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_state(file_path: str, state: Dict[str, Any]) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass

def apply_state(node: TreeNode, state: Dict[str, Any], is_root: bool = False) -> None:
    if is_root:
        node.expanded = True
    else:
        node_state = state.get(node.path, {})
        if node.is_dir:
            node.expanded = node_state.get("expanded", node.is_dir)
            node.anonymized = node_state.get("anonymized", False)
            node.display_name = node_state.get("anonymized_name", node.original_name) if node.anonymized else node.original_name
        else:
            node.disabled = node_state.get("disabled", False)
    node.update_render_name()
    for child in node.children:
        apply_state(child, state)
    if node.is_dir:
        node.calculate_token_count()

def gather_state(node: TreeNode, state: Dict[str, Any], is_root: bool = False) -> None:
    if is_root:
        state[node.path] = {"expanded": True, "anonymized": node.anonymized, "anonymized_name": node.display_name if node.anonymized else None}
    else:
        if node.is_dir:
            state[node.path] = {"expanded": node.expanded, "anonymized": node.anonymized, "anonymized_name": node.display_name if node.anonymized else None}
        else:
            state[node.path] = {"disabled": node.disabled}
    for child in node.children:
        gather_state(child, state)

def generate_anonymized_name() -> str:
    return random.choice(ANONYMIZED_PREFIXES) + "_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def toggle_node(node: TreeNode) -> None:
    if node.is_dir:
        node.expanded = not node.expanded
        node.update_render_name()

def anonymize_toggle(node: TreeNode) -> None:
    if node.is_dir:
        node.anonymized = not node.anonymized
        node.display_name = generate_anonymized_name() if node.anonymized else node.original_name
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

def anonymize_subtree(node: TreeNode) -> None:
    if node.is_dir:
        node.anonymized = not node.anonymized
        node.display_name = generate_anonymized_name() if node.anonymized else node.original_name
        node.update_render_name()
        for child in node.children:
            anonymize_subtree(child)

def flatten_tree(node: TreeNode, depth: int = 0, ancestor_has_tokens: bool = False) -> Generator[Tuple[TreeNode, int, bool], None, None]:
    show_tokens = False
    if not ancestor_has_tokens and node.token_count > 0 and node.is_dir:
        show_tokens = True
        ancestor_has_tokens = True
    yield (node, depth, show_tokens)
    if node.is_dir and node.expanded:
        for child in node.children:
            yield from flatten_tree(child, depth + 1, ancestor_has_tokens)

def collect_visible_files(node: TreeNode, path_mode: str) -> List[Tuple[str, str]]:
    files = []
    def recurse(nd: TreeNode, path: List[str]):
        current_path = path + [nd.display_name]
        if nd.is_dir and nd.expanded:
            for child in nd.children:
                recurse(child, current_path)
        elif not nd.is_dir and not nd.disabled:
            display_path = os.path.join(*current_path) if path_mode == "relative" else nd.display_name
            try:
                with open(nd.path, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                content = "<Could not read file>"
            files.append((display_path, content))
    recurse(node, [])
    return files

def copy_files_subloop(stdscr: Any, files: List[Tuple[str, str]], fmt: str) -> str:
    copied_text = []
    my, mx = stdscr.getmaxyx()
    total = len(files)
    progress_bar_length = max(10, mx - 30)
    for idx, (path, content) in enumerate(files, 1):
        copied_text.append(
            COPY_FORMAT_PRESETS.get(fmt, COPY_FORMAT_PRESETS["blocks"]).format(
                path=path,
                content=content or "<Could not read file>"
            )
        )
        progress = int((idx / total) * progress_bar_length)
        progress_bar = "#" * progress + "-" * (progress_bar_length - progress)
        status = f"Copying {idx}/{total} files: [{progress_bar}]"
        try:
            stdscr.addstr(my - 1, 0, status[:mx-1], curses.color_pair(7))
        except curses.error:
            pass
        stdscr.refresh()
    return ''.join(copied_text)

def init_colors() -> None:
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)    # Files
    curses.init_pair(2, curses.COLOR_GREEN, -1)   # Directories
    curses.init_pair(3, curses.COLOR_RED, -1)     # Disabled files
    curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Token labels
    curses.init_pair(5, curses.COLOR_YELLOW, -1)  # Additional labels
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Success message
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # General text and symbols

def safe_addnstr(stdscr: Any, y: int, x: int, text: str, color: int) -> None:
    max_y, max_x = stdscr.getmaxyx()
    if 0 <= y < max_y and 0 <= x < max_x:
        try:
            stdscr.addnstr(y, x, text, max_x - x - 1, curses.color_pair(color))
        except curses.error:
            pass

def run_curses(
    stdscr: Any,
    root_node: TreeNode,
    path_to_node: Dict[str, TreeNode],
    fmt: str,
    path_mode: str,
    tree_changed_flag: threading.Event,
    lock: threading.Lock
) -> None:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.halfdelay(int(INPUT_TIMEOUT * 10))
    init_colors()
    current_index, scroll_offset, shift_mode = 0, 0, False
    copying_success, success_message_time = False, 0.0
    step_normal, step_accel = SCROLL_SPEED["normal"], SCROLL_SPEED["accelerated"]
    flattened_cache: List[Tuple[TreeNode, int, bool]] = []
    tree_changed, total_tokens = True, root_node.token_count

    while True:
        now = time.time()
        if copying_success and (now - success_message_time > SUCCESS_MESSAGE_DURATION):
            copying_success = False
        if tree_changed_flag.is_set():
            with lock:
                flattened_cache = list(flatten_tree(root_node))
            tree_changed, tree_changed_flag.clear()
            total_tokens = root_node.token_count
        if tree_changed:
            with lock:
                flattened_cache = list(flatten_tree(root_node))
            tree_changed, total_tokens = False, root_node.token_count
        max_y, max_x = stdscr.getmaxyx()
        visible_lines = max_y - 1
        with lock:
            current_index = max(0, min(current_index, len(flattened_cache) - 1))
        if current_index < scroll_offset:
            scroll_offset = current_index
        elif current_index >= scroll_offset + visible_lines:
            scroll_offset = current_index - visible_lines + 1
        stdscr.erase()
        with lock:
            for i in range(scroll_offset, min(scroll_offset + visible_lines, len(flattened_cache))):
                node, depth, show_tokens = flattened_cache[i]
                is_selected, y, x = (i == current_index), i - scroll_offset, 0
                arrow = "> " if is_selected else "  "
                safe_addnstr(stdscr, y, x, arrow, 0)
                x += len(arrow)
                prefix = "│  " * depth
                safe_addnstr(stdscr, y, x, prefix, 0)
                x += len(prefix)
                
                # Add improved expand/collapse symbols for directories in white
                if node.is_dir:
                    symbol = "▾ " if node.expanded else "▸ "
                    symbol_color = 7  # White for symbols
                    safe_addnstr(stdscr, y, x, symbol, symbol_color)
                    x += len(symbol)
                
                # Set color based on node type
                color = 2 if node.is_dir else (3 if node.disabled else 1)
                safe_addnstr(stdscr, y, x, node.render_name, color)
                x += len(node.render_name)
                if show_tokens and node.token_count > 0:
                    separator = " | "
                    if x + len(separator) < max_x:
                        safe_addnstr(stdscr, y, x, separator, 7)
                        x += len(separator)
                    tokens_label = "Tokens: "
                    tokens_number = f"{node.token_count}"
                    if x + len(tokens_label) < max_x:
                        safe_addnstr(stdscr, y, x, tokens_label, 4)
                        x += len(tokens_label)
                    if x + len(tokens_number) < max_x:
                        safe_addnstr(stdscr, y, x, tokens_number, 7)
        if copying_success:
            safe_addnstr(stdscr, max_y - 1, 0, "Successfully Copied to Clipboard".ljust(max_x), 6)
        else:
            labels = []
            with lock:
                if flattened_cache:
                    node, _, _ = flattened_cache[current_index]
                    if node.is_dir:
                        if shift_mode:
                            labels.extend([("[E] Toggle All", 7), ("[A] " + ("Anonymize All" if not node.anonymized else "De-Anonymize All"), 7)])
                        else:
                            labels.extend([("[e] Toggle", 7), ("[a] " + ("Anonymize" if not node.anonymized else "De-Anonymize"), 7)])
                    else:
                        labels.append(("[d] " + ("Enable" if node.disabled else "Disable"), 7))
                    labels.append(("[c] Copy", 7))
                else:
                    labels.append(("No files to display.", 7))
            with lock:
                tokens_visible = any(
                    show_tokens for _, _, show_tokens in flattened_cache[scroll_offset:scroll_offset + visible_lines]
                )
            if not tokens_visible:
                if total_tokens > 0:
                    labels.extend([("|", 7), ("Tokens:", 4), (str(total_tokens), 7)])
                else:
                    labels.extend([("|", 7), ("No tokens to copy.", 4)])
            x_position = 0
            for text, color in labels:
                safe_addnstr(stdscr, max_y - 1, x_position, text, color)
                x_position += len(text) + 2
        stdscr.refresh()
        try:
            key = stdscr.getch()
        except KeyboardInterrupt:
            key = ord('q')
        if key == -1:
            continue
        shift_mode = True if 65 <= key <= 90 else False if 97 <= key <= 122 else shift_mode
        step = step_accel if shift_mode else step_normal
        if key in (ord("w"), ord("W")):
            current_index = max(0, current_index - step)
        elif key in (ord("s"), ord("S")):
            current_index = min(len(flattened_cache) - 1, current_index + step)
        elif key in (curses.KEY_ENTER, 10, 13):
            with lock:
                node, _, _ = flattened_cache[current_index]
                if node.is_dir:
                    toggle_node(node)
                    node.calculate_token_count()
                    if node.parent:
                        node.parent.calculate_token_count()
                    tree_changed_flag.set()
        elif shift_mode:
            with lock:
                node, _, _ = flattened_cache[current_index]
                if node.is_dir:
                    if key == ord("E"):
                        toggle_subtree(node)
                        node.calculate_token_count()
                        if node.parent:
                            node.parent.calculate_token_count()
                        tree_changed_flag.set()
                    elif key == ord("A"):
                        anonymize_subtree(node)
                        node.calculate_token_count()
                        if node.parent:
                            node.parent.calculate_token_count()
                        tree_changed_flag.set()
        else:
            with lock:
                node, _, _ = flattened_cache[current_index]
                if key == ord("e") and node.is_dir:
                    toggle_node(node)
                    node.calculate_token_count()
                    if node.parent:
                        node.parent.calculate_token_count()
                    tree_changed_flag.set()
                elif key == ord("a") and node.is_dir:
                    anonymize_toggle(node)
                    node.calculate_token_count()
                    if node.parent:
                        node.parent.calculate_token_count()
                    tree_changed_flag.set()
                elif key == ord("d") and not node.is_dir:
                    previous_tokens = node.token_count if not node.disabled else 0
                    node.disabled = not node.disabled
                    node.update_render_name()
                    new_tokens = node.token_count if not node.disabled else 0
                    delta = new_tokens - previous_tokens
                    if node.parent:
                        node.parent.update_token_count(delta)
                    tree_changed_flag.set()
                elif key == ord("c"):
                    files_to_copy = collect_visible_files(node, path_mode)
            if key == ord("c") and files_to_copy:
                copied_text = copy_files_subloop(stdscr, files_to_copy, fmt)
                copy_text_to_clipboard(copied_text)
                copying_success, success_message_time = True, time.time()
        if key in (ord("q"), ord("Q")):
            state = {}
            with lock:
                gather_state(root_node, state, is_root=True)
            save_state(STATE_FILE, state)
            curses.endwin()
            sys.exit(0)

def calculate_token_counts(
    root: TreeNode,
    path_to_node: Dict[str, TreeNode],
    tree_changed_flag: threading.Event,
    lock: threading.Lock
) -> None:
    while True:
        with lock:
            for node in path_to_node.values():
                if not node.is_dir and node.token_count == 0 and not node.disabled:
                    try:
                        with open(node.path, "r", encoding="utf-8") as f:
                            node.token_count = count_tokens(f.read())
                    except:
                        node.token_count = 0
                    if node.parent:
                        node.parent.update_token_count(node.token_count)
            tree_changed_flag.set()
        time.sleep(5)

def scan_filesystem(
    root_path: str,
    file_filter: FileFilter,
    path_to_node: Dict[str, TreeNode],
    tree_changed_flag: threading.Event,
    stop_event: threading.Event,
    lock: threading.Lock
) -> None:
    previous_state = {}
    with lock:
        for path, node in path_to_node.items():
            if not node.is_dir:
                try:
                    previous_state[path] = os.path.getmtime(path)
                except:
                    previous_state[path] = None
    while not stop_event.is_set():
        current_state = {}
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [d for d in dirnames if not file_filter.is_ignored(d)]
            for name in filenames:
                if file_filter.is_ignored(name):
                    continue
                full_path = os.path.join(dirpath, name)
                try:
                    current_state[full_path] = os.path.getmtime(full_path)
                except:
                    current_state[full_path] = None
        added = set(current_state.keys()) - set(previous_state.keys())
        removed = set(previous_state.keys()) - set(current_state.keys())
        modified = {path for path in current_state.keys() & previous_state.keys() if current_state[path] != previous_state[path]}
        if added or removed or modified:
            with lock:
                for path in added:
                    is_dir = os.path.isdir(path)
                    parent_path = os.path.dirname(path)
                    parent_node = path_to_node.get(parent_path)
                    if parent_node and parent_node.is_dir and parent_node.expanded:
                        new_node = TreeNode(path, is_dir, parent_node)
                        if not is_dir:
                            try:
                                with open(path, "r", encoding="utf-8") as f:
                                    new_node.token_count = count_tokens(f.read())
                            except:
                                new_node.token_count = 0
                            if not new_node.disabled:
                                parent_node.update_token_count(new_node.token_count)
                        parent_node.add_child(new_node)
                        parent_node.sort_children()
                        path_to_node[path] = new_node
                for path in removed:
                    node = path_to_node.get(path)
                    if node:
                        parent = node.parent
                        if parent:
                            parent.children.remove(node)
                            if not node.is_dir and not node.disabled:
                                parent.update_token_count(-node.token_count)
                        del path_to_node[path]
                for path in modified:
                    node = path_to_node.get(path)
                    if node and not node.is_dir and not node.disabled:
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                new_count = count_tokens(f.read())
                        except:
                            new_count = 0
                        delta = new_count - node.token_count
                        node.token_count = new_count
                        if node.parent:
                            node.parent.update_token_count(delta)
            tree_changed_flag.set()
        previous_state = current_state
        time.sleep(1)

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrollable, interactive ASCII tree view of a directory.")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to display (defaults to current).")
    parser.add_argument("--copy-format", choices=["blocks", "lines", "raw"], default="blocks", help="Format of copied files.")
    parser.add_argument("--path-mode", choices=["relative", "basename"], default="relative", help="Display full relative paths or just the file/folder name.")
    args = parser.parse_args()
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.")
        sys.exit(1)
    file_filter = FileFilter(IGNORED_PATTERNS, ALLOWED_EXTENSIONS)
    root_path = os.path.abspath(args.directory)
    path_to_node: Dict[str, TreeNode] = {}
    lock = threading.Lock()
    root_node = build_tree(root_path, file_filter, path_to_node, lock)
    saved_state = load_state(STATE_FILE)
    with lock:
        apply_state(root_node, saved_state, is_root=True)
    tree_changed_flag = threading.Event()
    stop_event = threading.Event()
    threading.Thread(target=calculate_token_counts, args=(root_node, path_to_node, tree_changed_flag, lock), daemon=True).start()
    threading.Thread(target=scan_filesystem, args=(root_path, file_filter, path_to_node, tree_changed_flag, stop_event, lock), daemon=True).start()
    try:
        curses.wrapper(
            partial(
                run_curses,
                root_node=root_node,
                path_to_node=path_to_node,
                fmt=args.copy_format,
                path_mode=args.path_mode,
                tree_changed_flag=tree_changed_flag,
                lock=lock
            )
        )
    finally:
        stop_event.set()

if __name__ == "__main__":
    main()
