import os, shutil, fnmatch, stat
from typing import List, Dict, Any, Optional, Tuple

def _onerror(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except:
        pass

def _remove_path(path: str, follow_symlinks: bool) -> None:
    try:
        if os.path.isdir(path) and (follow_symlinks or not os.path.islink(path)):
            shutil.rmtree(path, onerror=_onerror)
        elif os.path.exists(path):
            os.remove(path)
    except:
        pass

def _match(name: str, patterns: List[str]) -> bool:
    for p in patterns:
        if fnmatch.fnmatch(name, p):
            return True
    return False

def cleanup_directory(directory_path: str, patterns: List[str], options: Dict[str, Any]):
    if not os.path.isdir(directory_path):
        return False
    if not options.get("enabled", True):
        return True
    recursive = options.get("recursive", True)
    follow_symlinks = options.get("follow_symlinks", False)
    delete_empty_dirs = options.get("delete_empty_dirs", False)
    for root, dirs, files in os.walk(directory_path, topdown=False, followlinks=follow_symlinks):
        for f in files:
            if _match(f, patterns):
                _remove_path(os.path.join(root, f), follow_symlinks)
        for d in dirs:
            full = os.path.join(root, d)
            if _match(d, patterns):
                _remove_path(full, follow_symlinks)
        if not recursive:
            break
    if delete_empty_dirs:
        delete_empty_directories(directory_path, recursive, follow_symlinks)
    return True

def delete_empty_directories(directory_path: str, recursive: bool = True, follow_symlinks: bool = False):
    if not os.path.isdir(directory_path):
        return
    for root, dirs, files in os.walk(directory_path, topdown=False, followlinks=follow_symlinks):
        if root == directory_path:
            continue
        if not files and not dirs:
            try:
                os.rmdir(root)
            except:
                pass
        if not recursive and root != directory_path:
            break

def get_cleanup_statistics(directory_path: str, patterns: List[str], options: Dict[str, Any]):
    if not os.path.isdir(directory_path):
        return 0, 0, []
    if not options.get("enabled", True):
        return 0, 0, []
    recursive = options.get("recursive", True)
    follow_symlinks = options.get("follow_symlinks", False)
    d_count = 0
    f_count = 0
    items: List[str] = []
    for root, dirs, files in os.walk(directory_path, topdown=True, followlinks=follow_symlinks):
        for d in list(dirs):
            if _match(d, patterns):
                items.append(os.path.join(root, d))
                d_count += 1
                dirs.remove(d)
        for f in files:
            if _match(f, patterns):
                items.append(os.path.join(root, f))
                f_count += 1
        if not recursive:
            break
    return d_count, f_count, items
