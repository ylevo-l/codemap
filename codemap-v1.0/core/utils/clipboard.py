import os,sys,subprocess,threading,time,functools,concurrent.futures,re
from dataclasses import dataclass
from pathlib import Path
from typing import List,Tuple,Optional,Set
from config.constants import COPY_FORMAT_PRESETS,get_cli_refresh_interval,count_tokens
from core.refactor.language import determine_language
from core.utils.caching import LRUCache
from core.utils.debug import log

@dataclass(frozen=True)
class Segment:
    path: str
    body: str

MAX_SEG = 5000

_DEST_TRIM = 2048

_VALID_TRIM = 4096

_SEG_TRIM = 32

_norm = functools.lru_cache(8192)(lambda p: os.path.normpath(p.replace("\\", os.sep).replace("/", os.sep)))

_abs  = functools.lru_cache(8192)(os.path.abspath)

_case = functools.lru_cache(8192)(os.path.normcase)

_SEG_RE = re.compile(
    r'([^\r\n]+)\r?\n\s*```[^\r\n]*\r?\n(.*?)\r?\n\s*```',
    re.S

)

_DELIM_PATTERN = re.compile(r'^(?P<rune>\W)\1{2,}$')

def _system_clipboard() -> str:
    if sys.platform.startswith("win"):
        try: return subprocess.check_output("powershell Get-Clipboard", shell=True).decode("latin-1","ignore")
        except: return ""
    if sys.platform.startswith("darwin"):
        try: return subprocess.check_output(["pbpaste"]).decode("latin-1")
        except: return ""
    try: return subprocess.check_output(["xclip","-selection","clipboard","-o"]).decode("latin-1")
    except: return ""

def _robust_split(text: str) -> List[Segment]:
    out: List[Segment] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) and len(out) < MAX_SEG:
        while i < len(lines) and not lines[i].strip(): i += 1
        if i >= len(lines): break
        path = _norm(lines[i].strip())
        i += 1
        while i < len(lines) and not lines[i].strip(): i += 1
        if i >= len(lines):
            out.append(Segment(path, ""))
            break
        body: List[str] = []
        start_line = lines[i]
        i += 1
        if start_line.startswith("```"):
            fence = "```"
            while i < len(lines) and not lines[i].strip().startswith(fence):
                body.append(lines[i]); i += 1
            if i < len(lines): i += 1
        else:
            m = _DELIM_PATTERN.match(start_line.strip())
            if m:
                fence = m.group(0)
                if i < len(lines) and not _DELIM_PATTERN.match(lines[i].strip()):
                    i += 1
                while i < len(lines):
                    if _DELIM_PATTERN.match(lines[i].strip()):
                        i += 1
                        break
                    body.append(lines[i]); i += 1
            else:
                body.append(start_line)
                while i < len(lines) and lines[i]:
                    body.append(lines[i]); i += 1
        out.append(Segment(path, "\n".join(body)))
    return out

def _parse(buf: str) -> List[Segment]:
    if not buf: return []
    fast = [Segment(_norm(p).strip(), c) for p, c in _SEG_RE.findall(buf)]
    return fast[:MAX_SEG] if fast else _robust_split(buf)

class _Clip:
    __slots__ = ("raw","ts","segments","base","abs_root","rel_root")

    def __init__(self):
        self.raw = ""
        self.ts = 0.0
        self.segments: List[Segment] = []
        self.base: Set[str] = set()
        self.abs_root: Optional[str] = None
        self.rel_root: Optional[str] = None

    def _analyse(self):
        self.base = {os.path.basename(s.path) for s in self.segments}
        abs_paths = [s.path for s in self.segments if os.path.isabs(s.path)]
        if abs_paths and len(abs_paths) == len(self.segments):
            dirs = {os.path.dirname(_abs(p)) for p in abs_paths}
            self.abs_root = dirs.pop() if len(dirs) == 1 else None
            self.rel_root = None
        else:
            rels = [s.path for s in self.segments if not os.path.isabs(s.path)]
            tops = {p.split(os.sep)[0] for p in rels if p}
            self.rel_root = tops.pop() if len(tops) == 1 else None
            self.abs_root = None

    def update(self, txt: str):
        self.raw = txt
        self.ts = time.perf_counter()
        self.segments = _parse(txt)[:MAX_SEG]
        self._analyse()

_clip = _Clip()

_SEG_CACHE   = LRUCache(128)

_dest_cache  = LRUCache(4096)

_valid_cache = LRUCache(8192)

def trim_caches():
    _dest_cache.prune(_DEST_TRIM)
    _valid_cache.prune(_VALID_TRIM)
    _SEG_CACHE.prune(_SEG_TRIM)

def get_clipboard_segments() -> List[Tuple[str,str]]:
    return [(s.path, s.body) for s in _clip.segments]

def _dest(base: str, src: str) -> Optional[str]:
    k = (_abs(base), src)
    hit = _dest_cache.get(k)
    if hit is not None: return hit
    bb, rel = k
    rel = _norm(rel.strip())
    if os.path.isabs(rel):
        d = _abs(rel)
        res = d if d == bb or d.startswith(bb+os.sep) else None
    else:
        parts = rel.split(os.sep)
        root = os.path.basename(bb)
        if parts[0] == root:
            res = os.path.join(bb, *parts[1:])
        elif root in parts:
            res = os.path.join(bb, *parts[parts.index(root)+1:])
        else:
            res = os.path.join(bb, rel)
    _dest_cache.put(k, res)
    return res

def _ancestors(p: str):
    cur = _abs(p)
    while True:
        yield cur
        nxt = os.path.dirname(cur)
        if nxt == cur: break
        cur = nxt

def _dir_scope(base: str) -> bool:
    if _clip.abs_root:
        root = _clip.abs_root
        return root == base or root.startswith(base+os.sep)
    if _clip.rel_root:
        top = _clip.rel_root
        if os.path.basename(base) == top: return True
        if top in _abs(base).split(os.sep): return True
        if os.path.exists(os.path.join(base, top)): return True
        return False
    return True

def has_valid_paste(p: str, is_dir: bool) -> bool:
    key = (_case(_abs(p)), is_dir, _clip.ts)
    hit = _valid_cache.get(key)
    if hit is not None: return hit
    b = _abs(p)
    segs = _clip.segments
    if not segs:
        _valid_cache.put(key, False)
        return False
    if is_dir:
        if not _dir_scope(b):
            _valid_cache.put(key, False)
            return False
        ok = any(_dest(b, s.path) for s in segs)
        _valid_cache.put(key, ok)
        return ok
    target = _case(_abs(p))
    if os.path.basename(target) not in _clip.base:
        _valid_cache.put(key, False)
        return False
    for s in segs:
        if os.path.isabs(s.path) and _case(_abs(s.path)) == target:
            _valid_cache.put(key, True)
            return True
        for a in _ancestors(os.path.dirname(target)):
            if _dest(a, s.path) == target:
                _valid_cache.put(key, True)
                return True
    _valid_cache.put(key, False)
    return False

def _write(dst: str, body: str) -> bool:
    try:
        data = body.encode("latin-1")
        if os.path.exists(dst):
            with open(dst, "rb") as f:
                if f.read() == data: return True
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "wb") as f: f.write(data)
        return True
    except: return False

_WRITER_POOL = concurrent.futures.ThreadPoolExecutor(
    max_workers=max(4, min(16, os.cpu_count() or 4)),
    thread_name_prefix="paste"

)

def paste_into(p: str, is_dir: bool, allowed: Optional[Set[str]] = None) -> bool:
    segs = _clip.segments
    if not segs: return False
    canon = lambda x: _case(_abs(x))
    if is_dir:
        base = _abs(p)
        tasks = []
        for s in segs:
            d = _dest(base, s.path)
            if not d: continue
            if allowed and canon(d) not in allowed: continue
            tasks.append((d, s.body))
        if not tasks: return False
        fut = [_WRITER_POOL.submit(_write, d, b) for d, b in tasks]
        return any(f.result() for f in fut)
    target = canon(p)
    for s in segs:
        if os.path.isabs(s.path) and canon(s.path) == target and _write(target, s.body):
            return True
        for a in _ancestors(os.path.dirname(target)):
            r = _dest(a, s.path)
            if r and canon(r) == target and _write(target, s.body):
                return True
    return False

def _tpl(p: str, c: str, fmt: str) -> str:
    t = COPY_FORMAT_PRESETS.get(fmt, COPY_FORMAT_PRESETS["optimized"])
    return t.format(path=p, content=c.rstrip() or "<Could not read file>", language=determine_language(p))

def copy_files_subloop(stdscr, files: List[Tuple[str,str]], fmt: str) -> str:
    outs = []; chars = toks = 0; paths = []
    for p, c in files:
        chars += len(c)
        toks   += count_tokens(c)
        paths.append(p)
        outs.append(_tpl(p, c, fmt))
    log("COPY", len(files), "file(s)", chars, "chars", toks, "tokens", "paths:", ",".join(paths))
    return "\n".join(outs)

def copy_text_to_clipboard(t: str):
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True).communicate(t.encode("utf-16le"))
        elif sys.platform.startswith("darwin"):
            subprocess.Popen("pbcopy", stdin=subprocess.PIPE).communicate(t.encode())
        else:
            subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE).communicate(t.encode())
    except: pass
    _clip.update(t)
    log("CLIPBOARD UPDATED", len(t), "chars", count_tokens(t), "tokens")

def _refresh():
    txt = _system_clipboard()
    if txt == _clip.raw: return
    h = hash(txt)
    cached = _SEG_CACHE.get(h)
    if cached:
        _clip.raw, _clip.ts, (_clip.segments, _clip.base, _clip.abs_root, _clip.rel_root) = txt, time.perf_counter(), cached
        return
    _clip.update(txt)
    _SEG_CACHE.put(h, (_clip.segments, _clip.base, _clip.abs_root, _clip.rel_root))

def _bg():
    interval = max(get_cli_refresh_interval()*5, 0.1)
    while True:
        try:
            _refresh()
            _valid_cache.clear()
            _dest_cache.clear()
            trim_caches()
        except: pass
        time.sleep(interval)

threading.Thread(target=_bg, daemon=True, name="clip_refresh").start()

__all__ = [
    "copy_text_to_clipboard",
    "copy_files_subloop",
    "has_valid_paste",
    "paste_into",
    "get_clipboard_segments",
    "trim_caches"

]
