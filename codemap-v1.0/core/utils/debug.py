import os,sys,subprocess,tempfile,threading,time,atexit,traceback

INFO=20

WARN=30

ERROR=40

_LEVEL_MAP={INFO:"INF",WARN:"WRN",ERROR:"ERR"}

_log_file=None

_lock=threading.Lock()

_dup_msg:str|None=None

_dup_cnt:int=0

_flush_interval=2.0

_stop_evt=threading.Event()

def _emit(line:str):
    if _log_file:
        print(line,file=_log_file,flush=True)

def _compose(level:int,msg:str)->str:
    ts=time.strftime("%H:%M:%S")
    th=threading.current_thread().name
    return f"{ts} {_LEVEL_MAP.get(level,'DBG')} {th}: {msg}"

def _flush():
    global _dup_msg,_dup_cnt
    if _dup_msg is None:return
    if _dup_cnt>1:_emit(f"{_dup_msg} (x{_dup_cnt})")
    _dup_msg=None;_dup_cnt=0

def _flusher():
    while not _stop_evt.wait(_flush_interval):
        with _lock:_flush()

def _spawn(path:str):
    if sys.platform.startswith("win"):
        for cmd in (["powershell","-NoExit","-Command",f"Get-Content -Path '{path}' -Wait"],
                    ["cmd","/c","start","","cmd","/k",f"type \"{path}\" & pause"]):
            try:subprocess.Popen(cmd,creationflags=subprocess.CREATE_NEW_CONSOLE);return
            except:pass
    elif sys.platform.startswith("darwin"):
        try:subprocess.Popen(["open","-a","Terminal",path]);return
        except:pass
    else:
        for t in("x-terminal-emulator","xterm","gnome-terminal","konsole"):
            try:subprocess.Popen([t,"-e","tail","-f",path]);break
            except:continue

def init():
    global _log_file
    if _log_file or not os.getenv("CM_DEBUG"):return
    _log_file=tempfile.NamedTemporaryFile("w",delete=False,encoding="utf-8")
    sys.stderr=_log_file
    _spawn(_log_file.name)
    threading.Thread(target=_flusher,daemon=True).start()

def log(*msg,level:int=INFO):
    init()
    line=_compose(level," ".join(map(str,msg)))
    with _lock:
        global _dup_msg,_dup_cnt
        if line==_dup_msg:
            _dup_cnt+=1;return
        _flush();_dup_msg=line;_dup_cnt=1;_emit(line)

def log_exc(prefix:str|None=None):
    exc=traceback.format_exc().strip()
    if exc:
        log(prefix or "EXCEPTION",exc,level=ERROR)

def shutdown():
    _stop_evt.set()
    with _lock:_flush()

atexit.register(shutdown)

init()
