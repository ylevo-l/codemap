from __future__ import annotations
import concurrent.futures, re
from pathlib import Path
from typing import Any, Dict, List, Optional
from config.constants import CLEANUP_OPTIONS, CLEANUP_PATTERNS
from .language import determine_language, strip_comments_and_docstrings

_SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".php", ".rb", ".go", ".rs"

}

def _sanitize_whitespace(text: str):
    if not text:
        return ""
    lines = text.splitlines()
    out: List[str] = []
    skip_leading = True
    prev_blank = True
    import_block = False
    inside_class = False
    class_idx = -1
    last_indent = -1
    prev_def = False
    patterns: Dict[str, List[str]] = {
        "python": ["import ", "from "],
        "javascript": ["import ", "require("],
        "typescript": ["import ", "require("],
        "java": ["import "],
        "c": ["#include "],
        "cpp": ["#include "],
        "go": ["import "],
        "rust": ["use "],
        "php": ["require ", "include ", "require_once ", "include_once "],
        "ruby": ["require ", "include "],
        "csharp": ["using "],
    }
    curr_patterns = [p for v in patterns.values() for p in v]
    for idx, raw in enumerate(lines):
        line = raw.rstrip()
        if not line:
            if skip_leading or (out and out[-1] == "") or prev_def:
                continue
            if last_indent > 0:
                continue
            out.append("")
            prev_blank = True
            continue
        skip_leading = False
        indent = len(raw) - len(raw.lstrip())
        top_level = indent == 0
        is_import = any(line.lstrip().startswith(p) for p in curr_patterns)
        is_class = top_level and (
            (line.startswith("class ") and (line.endswith(":") or "{" in line))
            or ("class " in line and ("{" in line or line.endswith("{")))
        )
        is_def = (
            line.lstrip().startswith("def ") and (line.rstrip().endswith(":") or line.rstrip().endswith("{"))
        ) or (
            line.lstrip().startswith("function ") and (line.rstrip().endswith("{") or "=>" in line)
        ) or (
            any(p in line.lstrip() for p in ("public ", "private ", "protected ")) and "(" in line
        )
        if is_class:
            inside_class = True
            class_idx = idx
        elif top_level:
            inside_class = False
        if top_level:
            if is_import:
                import_block = True
            elif import_block:
                if not prev_blank:
                    out.append("")
                    prev_blank = True
                import_block = False
            elif not is_import and not prev_blank:
                prev = out[-1] if out else ""
                if not any(prev.strip().startswith(p) for p in ("@", "//")):
                    out.append("")
                    prev_blank = True
        elif inside_class and is_def and indent > 0:
            if idx != class_idx + 1:
                if not prev_blank and not prev_def and not any(out[-1].strip().startswith(p) for p in ("@", "//")):
                    out.append("")
                    prev_blank = True
        out.append(line)
        prev_blank = False
        last_indent = indent
        prev_def = is_def
    while out and not out[-1]:
        out.pop()
    code = "\n".join(out) + "\n" if out else ""
    code = re.sub(r"(^class[^\n]*:\n)([ \t]*\n)+", r"\1", code, flags=re.MULTILINE)
    return code

def _should_refactor(path: Path):
    return path.suffix.lower() in _SUPPORTED_EXTENSIONS and path.is_file()

def cleanup_after_refactor(directory_path: str, patterns: Optional[List[str]] = None, opts: Optional[Dict[str, Any]] = None):
    from .cleanup import cleanup_directory
    patterns = patterns or CLEANUP_PATTERNS
    options = {**CLEANUP_OPTIONS, **(opts or {})}
    return cleanup_directory(directory_path, patterns, options)

def get_cleanup_preview(directory_path: str, patterns: Optional[List[str]] = None, opts: Optional[Dict[str, Any]] = None):
    from .cleanup import get_cleanup_statistics
    patterns = patterns or CLEANUP_PATTERNS
    options = {**CLEANUP_OPTIONS, **(opts or {})}
    return get_cleanup_statistics(directory_path, patterns, options)

def refactor_file(file_path: str | Path):
    path = Path(file_path)
    if not _should_refactor(path):
        return False
    try:
        original = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    language = determine_language(str(path))
    transformed = strip_comments_and_docstrings(original, language)
    transformed = _sanitize_whitespace(transformed)
    if transformed != original:
        try:
            path.write_text(transformed, encoding="utf-8")
        except OSError:
            return False
    cleanup_after_refactor(str(path.parent))
    return True

def refactor_directory(
    directory_path: str,
    patterns: Optional[List[str]] = None,
    opts: Optional[Dict[str, Any]] = None,
    max_workers: int = 8,

):
    root = Path(directory_path)
    if not root.is_dir():
        return False
    files = [p for p in root.rglob("*") if _should_refactor(p)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(refactor_file, files))
    cleanup_after_refactor(directory_path, patterns, opts)
    return True
