#!/usr/bin/env python3
"""
Scrollable, interactive ASCII tree view of a directory with the following features:

1. SHIFT-based subtree actions: expand/collapse, anonymize/de-anonymize.
2. Single-folder toggles: expand/collapse, anonymize/de-anonymize.
3. Single-file toggles: enable/disable to exclude files from clipboard copying.
4. Clipboard copying of visible, enabled files with a progress bar.
5. Full state persistence: expanded, anonymized, file enablement.
6. Single-file, efficient code with no extra modules.

Usage:
- [UP]/[DOWN]: Navigate the tree
- [e]/[E]: Expand/collapse a single folder or entire subtree
- [a]/[A]: Anonymize/de-anonymize a single folder or entire subtree
- [d]: Enable/disable a single file
- [c]: Copy all visible, enabled files to the clipboard
- [q]: Quit (saves state to .tree_state.json)
"""

import argparse
import curses
import json
import os
import random
import string
import subprocess
import sys
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

STATE_FILE: str = ".tree_state.json"
SUCCESS_MESSAGE_DURATION: float = 0.5

IGNORED_FOLDERS: List[str] = [
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "venv",
]
IGNORED_MISC: List[str] = [
    ".env",
    ".DS_Store",
    "Thumbs.db",
]
IGNORED_LOGS: List[str] = [
    ".log",
    ".db",
    ".key",
    ".pyc",
]
IGNORED_PATTERNS: List[str] = IGNORED_FOLDERS + IGNORED_MISC + IGNORED_LOGS

ALLOWED_PYTHON: List[str] = [".py", ".pyi"]
ALLOWED_DOCS: List[str] = [".txt", ".md", ".rst"]
ALLOWED_CONFIG: List[str] = [".json", ".yaml", ".yml", ".toml"]
ALLOWED_SCRIPTS: List[str] = [".sh", ".bat"]
ALLOWED_EXTENSIONS: List[str] = ALLOWED_PYTHON + ALLOWED_DOCS + ALLOWED_CONFIG + ALLOWED_SCRIPTS


def human_readable_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes}B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.1f}K"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / (1024**2):.1f}M"
    return f"{size_in_bytes / (1024**3):.1f}G"


def copy_text_to_clipboard(text: str) -> None:
    try:
        if sys.platform.startswith('win'):
            p = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
            p.communicate(input=text.encode('utf-16'))
        elif sys.platform.startswith('darwin'):
            p = subprocess.Popen('pbcopy', stdin=subprocess.PIPE)
            p.communicate(input=text.encode('utf-8'))
        else:
            p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            p.communicate(input=text.encode('utf-8'))
    except Exception as exc:
        print(f"Copy error: {exc}")


class FileFilter:
    def __init__(self, ignored_patterns: Optional[List[str]] = None, allowed_extensions: Optional[List[str]] = None):
        self.ignored_patterns: List[str] = ignored_patterns or []
        self.allowed_extensions: List[str] = allowed_extensions or []

    def is_ignored(self, name: str) -> bool:
        for patt in self.ignored_patterns:
            if patt in name:
                return True
        _, ext = os.path.splitext(name)
        if self.allowed_extensions and ext and (ext.lower() not in self.allowed_extensions):
            return True
        return False


class TreeNode:
    def __init__(self, path: str, is_dir: bool = False, expanded: bool = False):
        self.path: str = path
        self.is_dir: bool = is_dir
        self.expanded: bool = expanded
        self.original_name: str = os.path.basename(path)
        self.display_name: str = self.original_name
        self.anonymized: bool = False
        self.disabled: Optional[bool] = False if not is_dir else None
        self.children: List['TreeNode'] = []

    def add_child(self, node: 'TreeNode') -> None:
        self.children.append(node)

    def sort_children(self) -> None:
        self.children.sort(key=lambda n: (not n.is_dir, n.display_name.lower()))


def build_tree(root_path: str, file_filter: FileFilter) -> TreeNode:
    root_node: TreeNode = TreeNode(root_path, is_dir=True, expanded=True)

    def walk_dir(parent: TreeNode, directory: str) -> None:
        try:
            entries: List[str] = sorted(os.listdir(directory))
        except PermissionError:
            return
        filtered: List[str] = []
        for e in entries:
            full: str = os.path.join(directory, e)
            if file_filter.is_ignored(e):
                continue
            if os.path.isdir(full) or os.path.isfile(full):
                filtered.append(e)

        for item in filtered:
            full_path: str = os.path.join(directory, item)
            if os.path.isdir(full_path):
                child_node: TreeNode = TreeNode(full_path, is_dir=True, expanded=False)
                parent.add_child(child_node)
                walk_dir(child_node, full_path)
            else:
                child_node: TreeNode = TreeNode(full_path, is_dir=False)
                parent.add_child(child_node)

        parent.sort_children()

    walk_dir(root_node, root_path)

    with open("tree_debug.log", "w", encoding="utf-8") as f:
        def log_tree(nd: TreeNode, depth: int = 0) -> None:
            prefix: str = ("│  " * depth) if depth > 0 else ""
            toggle: str = "●" if nd.is_dir and nd.expanded else ("○" if nd.is_dir else " ")
            f.write(f"{prefix}{toggle} {nd.display_name}\n")
            if nd.is_dir:
                for c in nd.children:
                    log_tree(c, depth + 1)
        log_tree(root_node)
    return root_node


def load_state(file_path: str) -> Dict[str, Any]:
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_state(file_path: str, state_dict: Dict[str, Any]) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
    except IOError:
        pass


def apply_state(node: TreeNode, states: Dict[str, Any]) -> None:
    if node.path in states:
        st: Dict[str, Any] = states[node.path]
        node.expanded = st.get("expanded", node.is_dir)
        node.anonymized = st.get("anonymized", False)
        if node.anonymized:
            node.display_name = st.get("anonymized_name", node.original_name)
        else:
            node.display_name = node.original_name
        if not node.is_dir:
            node.disabled = st.get("disabled", False)

    for child in node.children:
        apply_state(child, states)


def gather_state(node: TreeNode, states: Dict[str, Any]) -> None:
    if node.path not in states:
        states[node.path] = {}
    states[node.path]["expanded"] = node.expanded
    states[node.path]["anonymized"] = node.anonymized
    if node.anonymized:
        states[node.path]["anonymized_name"] = node.display_name
    else:
        states[node.path]["anonymized_name"] = None
    if not node.is_dir:
        states[node.path]["disabled"] = node.disabled

    for c in node.children:
        gather_state(c, states)


def generate_anonymized_name() -> str:
    prefixes: List[str] = ["Folder", "Project", "Repo", "Alpha", "Beta", "Omega", "Block"]
    prefix: str = random.choice(prefixes)
    suffix: str = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}_{suffix}"


def toggle_node(n: TreeNode) -> None:
    if n.is_dir:
        n.expanded = not n.expanded


def anonymize_toggle(n: TreeNode) -> None:
    if n.is_dir:
        if not n.anonymized:
            n.anonymized = True
            n.display_name = generate_anonymized_name()
        else:
            n.anonymized = False
            n.display_name = n.original_name


def toggle_subtree(n: TreeNode) -> None:
    if n.is_dir:
        n.expanded = not n.expanded
        for c in n.children:
            toggle_subtree(c)


def anonymize_subtree(n: TreeNode) -> None:
    if n.is_dir:
        new_state: bool = not n.anonymized
        n.anonymized = new_state
        if new_state:
            n.display_name = generate_anonymized_name()
        else:
            n.display_name = n.original_name
        for c in n.children:
            anonymize_subtree(c)


def flatten_tree(n: TreeNode, depth: int = 0) -> Generator[Tuple[TreeNode, int], None, None]:
    yield (n, depth)
    if n.is_dir and n.expanded:
        for c in n.children:
            yield from flatten_tree(c, depth + 1)


def collect_visible_files(n: TreeNode) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []

    def gather(nd: TreeNode, prefix_parts: List[str]) -> None:
        new_parts: List[str] = prefix_parts + [nd.display_name]
        if nd.is_dir and nd.expanded:
            for ch in nd.children:
                gather(ch, new_parts)
        elif not nd.is_dir:
            if not nd.disabled:
                rel_path: str = os.path.join(*new_parts)
                content: str = ""
                try:
                    with open(nd.path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    content = "<Could not read file>"
                results.append((rel_path, content))

    gather(n, [])
    return results


def copy_files_subloop(stdscr: Any, visible_files: List[Tuple[str, str]]) -> str:
    text_lines: List[str] = ["Below is the collected code from all visible, enabled files.\n"]
    max_y: int
    max_x: int
    max_y, max_x = stdscr.getmaxyx()
    total: int = len(visible_files)

    for idx, (rel_path, content) in enumerate(visible_files, start=1):
        text_lines.append(f"{rel_path}:")
        text_lines.append('"""')
        text_lines.append(content if content else "<Could not read file>")
        text_lines.append('"""')
        text_lines.append("")

        bar_width: int = max(10, max_x - 25)
        done: int = int(bar_width * (idx / total)) if total else 0
        remain: int = bar_width - done
        bar_str: str = "#" * done + " " * remain
        progress_str: str = f"Copying {idx}/{total} files: [{bar_str}]"

        stdscr.clear()
        stdscr.addnstr(max_y - 1, 0, progress_str, max_x - 1)
        stdscr.refresh()

    return "\n".join(text_lines)


def init_colors() -> None:
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)


def run_curses(stdscr: Any, root_node: TreeNode, states: Dict[str, Any]) -> None:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    init_colors()

    current_index: int = 0
    scroll_offset: int = 0
    shift_mode: bool = False

    copying_success: bool = False
    success_message_time: float = 0.0

    root_path: str = root_node.path

    while True:
        now: float = time.time()
        if copying_success and (now - success_message_time > SUCCESS_MESSAGE_DURATION):
            copying_success = False

        stdscr.clear()
        max_y: int
        max_x: int
        max_y, max_x = stdscr.getmaxyx()

        flattened: List[Tuple[TreeNode, int]] = list(flatten_tree(root_node))
        visible_lines: int = max_y - 1

        if current_index < 0:
            current_index = 0
        elif current_index >= len(flattened):
            current_index = max(0, len(flattened) - 1)
        if current_index < scroll_offset:
            scroll_offset = current_index
        elif current_index >= scroll_offset + visible_lines:
            scroll_offset = current_index - visible_lines + 1

        for i in range(scroll_offset, min(scroll_offset + visible_lines, len(flattened))):
            node, depth = flattened[i]
            is_selected: bool = (i == current_index)

            y: int = i - scroll_offset
            x: int = 0

            arrow: str = "> " if is_selected else "  "
            stdscr.addstr(y, x, arrow, curses.color_pair(0))
            x += len(arrow)

            prefix: str = "│  " * depth
            stdscr.addstr(y, x, prefix, curses.color_pair(0))
            x += len(prefix)

            if node.is_dir:
                text: str = node.display_name
                stdscr.addstr(y, x, text, curses.color_pair(0))
                x += len(text)

                try:
                    size_str: str = human_readable_size(os.path.getsize(node.path))
                except OSError:
                    size_str = "?"
                size_text: str = f"  ({size_str})"
                if x + len(size_text) >= max_x:
                    size_text = size_text[:max_x - x - 1] + "..."
                stdscr.addstr(y, x, size_text, curses.color_pair(0))
            else:
                text: str = node.display_name
                stdscr.addstr(y, x, text, curses.color_pair(1))
                x += len(text)

                if node.disabled:
                    disabled_text: str = " (DISABLED)"
                    if x + len(disabled_text) >= max_x:
                        disabled_text = disabled_text[:max_x - x - 1] + "..."
                    stdscr.addstr(y, x, disabled_text, curses.color_pair(0))
                    x += len(disabled_text)

                try:
                    size_str: str = human_readable_size(os.path.getsize(node.path))
                except OSError:
                    size_str = "?"
                size_text: str = f"  ({size_str})"
                if x + len(size_text) >= max_x:
                    size_text = size_text[:max_x - x - 1] + "..."
                stdscr.addstr(y, x, size_text, curses.color_pair(0))

        if copying_success:
            msg: str = "Successfully Saved to Clipboard"
            padded: str = msg + " " * (max_x - len(msg))
            stdscr.addnstr(max_y - 1, 0, padded, max_x - 1)
        else:
            instr_line: str = ""
            if flattened:
                node, _ = flattened[current_index]
                if node.is_dir:
                    if shift_mode:
                        instr_line += "[E] Toggle All"
                        if not node.anonymized:
                            instr_line += "  [A] Anonymize All"
                        else:
                            instr_line += "  [A] De-Anonymize All"
                    else:
                        instr_line += "[e] Toggle"
                        if not node.anonymized:
                            instr_line += "  [a] Anonymize"
                        else:
                            instr_line += "  [a] De-Anonymize"
                else:
                    if node.disabled:
                        instr_line += "[d] Enable"
                    else:
                        instr_line += "[d] Disable"

                instr_line += "   [c] Copy"
            stdscr.addnstr(max_y - 1, 0, instr_line, max_x - 1)

        stdscr.refresh()

        key: int = stdscr.getch()
        if key == -1:
            continue

        if 65 <= key <= 90:
            shift_mode = True
        elif 97 <= key <= 122:
            shift_mode = False

        # Handle navigation and toggle keys
        if key in (curses.KEY_UP, ord('w'), ord('W')):
            current_index = max(0, current_index - 1)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            current_index = min(len(flattened) - 1, current_index + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            nd, _ = flattened[current_index]
            if nd.is_dir:
                toggle_node(nd)
        elif shift_mode:
            if key == ord('E'):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    toggle_subtree(nd)
            elif key == ord('A'):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    anonymize_subtree(nd)
        else:
            if key == ord('e'):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    toggle_node(nd)
            elif key == ord('a'):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    anonymize_toggle(nd)
            elif key == ord('d'):
                nd, _ = flattened[current_index]
                if not nd.is_dir:
                    nd.disabled = not nd.disabled
            elif key == ord('c'):
                visible_files: List[Tuple[str, str]] = collect_visible_files(root_node)
                if visible_files:
                    final_text: str = copy_files_subloop(stdscr, visible_files)
                    copy_text_to_clipboard(final_text)
                    copying_success = True
                    success_message_time = time.time()

        if key in (ord('q'), ord('Q')):
            st: Dict[str, Any] = {}
            gather_state(root_node, st)
            save_state(STATE_FILE, st)
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrollable, interactive ASCII tree view of a directory."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to display (defaults to current)."
    )
    args = parser.parse_args()

    file_filter: FileFilter = FileFilter(
        ignored_patterns=IGNORED_PATTERNS,
        allowed_extensions=ALLOWED_EXTENSIONS
    )

    root_path: str = os.path.abspath(args.directory)
    if not os.path.isdir(root_path):
        print(f"Error: '{root_path}' is not a directory.")
        sys.exit(1)

    root_node: TreeNode = build_tree(root_path, file_filter)
    states: Dict[str, Any] = load_state(STATE_FILE)
    apply_state(root_node, states)

    curses.wrapper(run_curses, root_node, states)


if __name__ == "__main__":
    main()
