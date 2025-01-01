#!/usr/bin/env python3

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

import argparse, curses, json, os, random, string, subprocess, sys, time
from typing import Any, Dict, Generator, List, Optional, Tuple
import tiktoken  # Import tiktoken for accurate token counting

STATE_FILE = ".tree_state.json"
SUCCESS_MESSAGE_DURATION = 0.5
IGNORED_FOLDERS = ["__pycache__", "node_modules", "dist", "build", "venv", ".git", ".svn", ".hg", ".idea", ".vscode"]
IGNORED_MISC = [".env", ".DS_Store", "Thumbs.db", ".bak", ".tmp", "desktop.ini"]
IGNORED_LOGS = [".log", ".db", ".key", ".pyc", ".exe", ".dll", ".so", ".dylib"]
IGNORED_PATTERNS = IGNORED_FOLDERS + IGNORED_MISC + IGNORED_LOGS
ALLOWED_PYTHON = [".py", ".pyi", ".pyc", ".pyo", ".pyd"]
ALLOWED_DOCS = [".txt", ".md", ".rst", ".docx", ".pdf", ".odt"]
ALLOWED_CONFIG = [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"]
ALLOWED_SCRIPTS = [".sh", ".bat", ".ps1", ".bash", ".zsh"]
ALLOWED_MEDIA = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".mp3", ".wav", ".mp4", ".avi", ".mkv"]
ALLOWED_EXTENSIONS = ALLOWED_PYTHON + ALLOWED_DOCS + ALLOWED_CONFIG + ALLOWED_SCRIPTS + ALLOWED_MEDIA
DEFAULT_COPY_FORMAT = "blocks"
COPY_FORMAT_PRESETS = {
    "blocks": "{path}:\n\"\"\"\n{content}\n\"\"\"\n",
    "lines": "{path}: {content}\n",
    "raw": "{content}\n",
}
SCROLL_SPEED = {"normal": 1, "accelerated": 5}
MAX_TREE_DEPTH = 10
ANONYMIZED_PREFIXES = ["Folder", "Project", "Repo", "Alpha", "Beta", "Omega", "Block", "Archive", "Data", "Source"]
INPUT_TIMEOUT = 0.1

class AppConfig:
    def __init__(self, copy_format: str, path_mode: str):
        self.copy_format = copy_format
        self.path_mode = path_mode

# Initialize tiktoken encoding for the desired model
try:
    ENCODING = tiktoken.encoding_for_model("gpt-4o")  # Replace "gpt-4o" with your specific model if different
except KeyError:
    print("Error: Model encoding not found. Please check the model name or ensure it's supported by tiktoken.")
    sys.exit(1)

def count_tokens(content: str) -> int:
    """Accurately count tokens using tiktoken."""
    tokens = ENCODING.encode(content)
    return len(tokens)

def copy_text_to_clipboard(t: str) -> None:
    """Copy text to the system clipboard."""
    try:
        if sys.platform.startswith("win"):
            p = subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True)
            p.communicate(input=t.encode("utf-16"))
        elif sys.platform.startswith("darwin"):
            p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE)
            p.communicate(input=t.encode("utf-8"))
        else:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(input=t.encode("utf-8"))
    except:
        pass

class FileFilter:
    def __init__(self, ignored_patterns: Optional[List[str]] = None, allowed_extensions: Optional[List[str]] = None):
        self.ignored_patterns = ignored_patterns or []
        self.allowed_extensions = allowed_extensions or []
    def is_ignored(self, n: str) -> bool:
        """Determine if a file or folder should be ignored based on patterns and extensions."""
        for p in self.ignored_patterns:
            if p in n:
                return True
        _, ext = os.path.splitext(n)
        if self.allowed_extensions and ext and ext.lower() not in self.allowed_extensions:
            return True
        return False

class TreeNode:
    def __init__(self, p: str, is_dir: bool = False, expanded: bool = False):
        self.path = p
        self.is_dir = is_dir
        self.expanded = expanded
        self.original_name = os.path.basename(p)
        self.display_name = self.original_name
        self.anonymized = False
        self.disabled = None if is_dir else False
        self.children: List['TreeNode'] = []
        self.token_count: int = 0  # For files: token count; for dirs: cumulative token count
    def add_child(self, n: "TreeNode") -> None:
        """Add a child TreeNode."""
        self.children.append(n)
    def sort_children(self) -> None:
        """Sort children: directories first, then files alphabetically."""
        self.children.sort(key=lambda x: (not x.is_dir, x.display_name.lower()))
    def calculate_token_count(self) -> int:
        """Recursively calculate the cumulative token count for directories."""
        if not self.is_dir:
            return self.token_count
        total = 0
        for child in self.children:
            total += child.calculate_token_count()
        self.token_count = total
        return self.token_count

def build_tree(rp: str, f: FileFilter) -> TreeNode:
    """Build the directory tree recursively."""
    root = TreeNode(rp, True, True)
    def w(p: TreeNode, d: str, depth: int = 0) -> None:
        if depth > MAX_TREE_DEPTH:
            return
        try:
            e = sorted(os.listdir(d))
        except:
            return
        flt = []
        for i in e:
            x = os.path.join(d, i)
            if f.is_ignored(i):
                continue
            if os.path.isdir(x) or os.path.isfile(x):
                flt.append(i)
        for j in flt:
            fp = os.path.join(d, j)
            if os.path.isdir(fp):
                c = TreeNode(fp, True, False)
                p.add_child(c)
                w(c, fp, depth + 1)
            else:
                c = TreeNode(fp, False, False)
                try:
                    with open(fp, "r", encoding="utf-8") as file:
                        content = file.read()
                        c.token_count = count_tokens(content)
                except:
                    c.token_count = 0
                p.add_child(c)
        p.sort_children()
    w(root, rp, 0)
    root.calculate_token_count()
    return root

def load_state(fp: str) -> Dict[str, Any]:
    """Load the saved state from a JSON file."""
    if os.path.isfile(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(fp: str, d: Dict[str, Any]) -> None:
    """Save the current state to a JSON file."""
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except:
        pass

def apply_state(n: TreeNode, s: Dict[str, Any]) -> None:
    """Apply the saved state to the tree."""
    if n.path in s:
        st = s[n.path]
        n.expanded = st.get("expanded", n.is_dir)
        n.anonymized = st.get("anonymized", False)
        if n.anonymized:
            n.display_name = st.get("anonymized_name", n.original_name)
        else:
            n.display_name = n.original_name
        if not n.is_dir:
            n.disabled = st.get("disabled", False)
    for c in n.children:
        apply_state(c, s)
    if n.is_dir:
        n.calculate_token_count()

def gather_state(n: TreeNode, s: Dict[str, Any]) -> None:
    """Gather the current state of the tree for saving."""
    if n.path not in s:
        s[n.path] = {}
    s[n.path]["expanded"] = n.expanded
    s[n.path]["anonymized"] = n.anonymized
    if n.anonymized:
        s[n.path]["anonymized_name"] = n.display_name
    else:
        s[n.path]["anonymized_name"] = None
    if not n.is_dir:
        s[n.path]["disabled"] = n.disabled
    for c in n.children:
        gather_state(c, s)

def generate_anonymized_name() -> str:
    """Generate a random anonymized folder name."""
    return random.choice(ANONYMIZED_PREFIXES) + "_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

def toggle_node(n: TreeNode) -> None:
    """Toggle the expansion state of a directory."""
    if n.is_dir:
        n.expanded = not n.expanded

def anonymize_toggle(n: TreeNode) -> None:
    """Toggle the anonymization state of a directory."""
    if n.is_dir:
        x = not n.anonymized
        n.anonymized = x
        n.display_name = generate_anonymized_name() if x else n.original_name

def set_subtree_expanded(n: TreeNode, e: bool) -> None:
    """Set the expansion state for a directory and all its subdirectories."""
    n.expanded = e
    for c in n.children:
        if c.is_dir:
            set_subtree_expanded(c, e)

def toggle_subtree(n: TreeNode) -> None:
    """Toggle the expansion state for a directory and all its subdirectories."""
    if n.is_dir:
        x = not n.expanded
        set_subtree_expanded(n, x)

def anonymize_subtree(n: TreeNode) -> None:
    """Toggle the anonymization state for a directory and all its subdirectories."""
    if n.is_dir:
        x = not n.anonymized
        n.anonymized = x
        n.display_name = generate_anonymized_name() if x else n.original_name
        for c in n.children:
            anonymize_subtree(c)

def flatten_tree(n: TreeNode, d: int = 0) -> Generator[Tuple[TreeNode, int], None, None]:
    """Flatten the tree into a list for easy navigation."""
    yield (n, d)
    if n.is_dir and n.expanded:
        for c in n.children:
            yield from flatten_tree(c, d + 1)

def collect_visible_files(n: TreeNode, path_mode: str) -> List[Tuple[str, str]]:
    """Collect all visible and enabled files for copying."""
    r = []
    def g(nd: TreeNode, p: List[str]) -> None:
        z = p + [nd.display_name]
        if nd.is_dir and nd.expanded:
            for ch in nd.children:
                g(ch, z)
        elif not nd.is_dir and nd.disabled == False:
            rp = os.path.join(*z) if path_mode == "relative" else nd.display_name
            ct = ""
            try:
                with open(nd.path, "r", encoding="utf-8") as f:
                    ct = f.read()
            except:
                ct = "<Could not read file>"
            r.append((rp, ct))
    g(n, [])
    return r

def copy_files_subloop(stdscr: Any, vf: List[Tuple[str, str]], fmt: str) -> str:
    """Handle the copying of files with a progress bar."""
    lines = []
    my, mx = stdscr.getmaxyx()
    t = len(vf)
    for i, (rp, ct) in enumerate(vf, 1):
        fs = fmt
        if fs not in COPY_FORMAT_PRESETS:
            fs = "blocks"
        block = COPY_FORMAT_PRESETS[fs].format(path=rp, content=ct if ct else "<Could not read file>")
        lines.append(block)
        bw = max(10, mx - 25)
        dn = int(bw * (i / t)) if t else 0
        rm = bw - dn
        bs = "#" * dn + " " * rm
        ps = f"Copying {i}/{t} files: [{bs}]"
        stdscr.clear()
        try:
            stdscr.addnstr(my - 1, 0, ps, mx - 1)
        except:
            pass
        stdscr.refresh()
    return "".join(lines)

def init_colors() -> None:
    """Initialize color pairs for the UI."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)  # Files
    curses.init_pair(2, curses.COLOR_GREEN, -1)  # Directories
    curses.init_pair(3, curses.COLOR_RED, -1)    # Disabled files
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Success message

def safe_addnstr(stdscr: Any, y: int, x: int, s: str, c: int) -> None:
    """Safely add a string to the screen, preventing overflow."""
    my, mx = stdscr.getmaxyx()
    if y < 0 or y >= my or x >= mx:
        return
    s = s[:max(0, mx - x)]
    try:
        stdscr.addstr(y, x, s, curses.color_pair(c))
    except:
        pass

def run_curses(stdscr: Any, root_node: TreeNode, states: Dict[str, Any], fmt: str, path_mode: str) -> None:
    """Main loop for the curses-based UI."""
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.halfdelay(int(INPUT_TIMEOUT * 10))
    init_colors()

    current_index = 0
    scroll_offset = 0
    shift_mode = False
    copying_success = False
    success_message_time = 0.0
    step_normal = SCROLL_SPEED["normal"]
    step_accel = SCROLL_SPEED["accelerated"]

    while True:
        now = time.time()
        if copying_success and (now - success_message_time > SUCCESS_MESSAGE_DURATION):
            copying_success = False

        stdscr.clear()
        my, mx = stdscr.getmaxyx()
        flattened = list(flatten_tree(root_node))
        visible_lines = my - 1

        # Enforce bounds
        if current_index < 0:
            current_index = 0
        elif current_index >= len(flattened):
            current_index = max(0, len(flattened) - 1)

        # Scroll offset
        if current_index < scroll_offset:
            scroll_offset = current_index
        elif current_index >= scroll_offset + visible_lines:
            scroll_offset = current_index - visible_lines + 1

        # Draw the visible portion of the tree
        for i in range(scroll_offset, min(scroll_offset + visible_lines, len(flattened))):
            node, depth = flattened[i]
            is_selected = (i == current_index)

            y = i - scroll_offset
            x = 0

            arrow = "> " if is_selected else "  "
            safe_addnstr(stdscr, y, x, arrow, 0)
            x += len(arrow)

            prefix = "│  " * depth
            safe_addnstr(stdscr, y, x, prefix, 0)
            x += len(prefix)

            # Pick color based on node type and state
            if node.is_dir:
                color = 2  # Directory color (green)
            else:
                color = 3 if node.disabled else 1  # Disabled file (red) or normal file (cyan)

            # Show name
            safe_addnstr(stdscr, y, x, node.display_name, color)
            x += len(node.display_name)

            # Show token count if greater than 0
            if node.token_count > 0:
                token_text = f" ({node.token_count} tk)"
                if x + len(token_text) >= mx:
                    token_text = token_text[:mx - x - 1] + "..."
                safe_addnstr(stdscr, y, x, token_text, 0)

        # Bottom line: Instructions or success message
        if copying_success:
            msg = "Successfully Saved to Clipboard"
            padded = msg + " " * (mx - len(msg))
            safe_addnstr(stdscr, my - 1, 0, padded, 4)  # Success message color
        else:
            ins = ""
            if flattened:
                node, _ = flattened[current_index]
                if node.is_dir:
                    if shift_mode:
                        ins += "[E] Toggle All"
                        if not node.anonymized:
                            ins += "  [A] Anonymize All"
                        else:
                            ins += "  [A] De-Anonymize All"
                    else:
                        ins += "[e] Toggle"
                        if not node.anonymized:
                            ins += "  [a] Anonymize"
                        else:
                            ins += "  [a] De-Anonymize"
                else:
                    if node.disabled:
                        ins += "[d] Enable"
                    else:
                        ins += "[d] Disable"
                ins += "   [c] Copy"
            safe_addnstr(stdscr, my - 1, 0, ins, 0)

        stdscr.refresh()
        k = stdscr.getch()
        if k == -1:
            continue

        # Detect shift mode based on key case
        if 65 <= k <= 90:  # Uppercase letters
            shift_mode = True
        elif 97 <= k <= 122:  # Lowercase letters
            shift_mode = False

        sp = step_accel if shift_mode else step_normal

        # Handle navigation and actions
        if k in (ord("w"), ord("W")):
            current_index = max(0, current_index - sp)
        elif k in (ord("s"), ord("S")):
            current_index = min(len(flattened) - 1, current_index + sp)
        elif k in (curses.KEY_ENTER, 10, 13):
            nd, _ = flattened[current_index]
            if nd.is_dir:
                toggle_node(nd)
                nd.calculate_token_count()
        elif shift_mode:
            if k == ord("E"):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    toggle_subtree(nd)
                    nd.calculate_token_count()
            elif k == ord("A"):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    anonymize_subtree(nd)
        else:
            if k == ord("e"):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    toggle_node(nd)
                    nd.calculate_token_count()
            elif k == ord("a"):
                nd, _ = flattened[current_index]
                if nd.is_dir:
                    anonymize_toggle(nd)
            elif k == ord("d"):
                nd, _ = flattened[current_index]
                if not nd.is_dir:
                    nd.disabled = not nd.disabled
            elif k == ord("c"):
                vf = collect_visible_files(root_node, path_mode)
                if vf:
                    ft = copy_files_subloop(stdscr, vf, fmt)
                    copy_text_to_clipboard(ft)
                    copying_success = True
                    success_message_time = time.time()

        # Quit the application
        if k in (ord("q"), ord("Q")):
            s = {}
            gather_state(root_node, s)
            save_state(STATE_FILE, s)
            break

def main() -> None:
    """Parse arguments, build the tree, load state, and start the UI."""
    parser = argparse.ArgumentParser(
        description="Scrollable, interactive ASCII tree view of a directory."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to display (defaults to current)."
    )
    parser.add_argument(
        "--copy-format",
        choices=["blocks", "lines", "raw"],
        default=DEFAULT_COPY_FORMAT,
        help="Format of copied files."
    )
    parser.add_argument(
        "--path-mode",
        choices=["relative", "basename"],
        default="relative",
        help="Display full relative paths or just the file/folder name."
    )
    args = parser.parse_args()
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.")
        sys.exit(1)
    f = FileFilter(
        ignored_patterns=IGNORED_PATTERNS,
        allowed_extensions=ALLOWED_EXTENSIONS
    )
    rp = os.path.abspath(args.directory)
    root = build_tree(rp, f)
    st = load_state(STATE_FILE)
    apply_state(root, st)
    curses.wrapper(run_curses, root, st, args.copy_format, args.path_mode)

if __name__ == "__main__":
    main()
