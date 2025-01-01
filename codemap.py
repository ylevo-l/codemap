#!/usr/bin/env python3
import argparse, curses, json, os, random, string, subprocess, sys, time
from typing import Any, Dict, Generator, List, Optional, Tuple

STATE_FILE=".tree_state.json"
SUCCESS_MESSAGE_DURATION=0.5
IGNORED_FOLDERS=["__pycache__","node_modules","dist","build","venv",".git",".svn",".hg",".idea",".vscode"]
IGNORED_MISC=[".env",".DS_Store","Thumbs.db",".bak",".tmp","desktop.ini"]
IGNORED_LOGS=[".log",".db",".key",".pyc",".exe",".dll",".so",".dylib"]
IGNORED_PATTERNS=IGNORED_FOLDERS+IGNORED_MISC+IGNORED_LOGS
ALLOWED_PYTHON=[".py",".pyi",".pyc",".pyo",".pyd"]
ALLOWED_DOCS=[".txt",".md",".rst",".docx",".pdf",".odt"]
ALLOWED_CONFIG=[".json",".yaml",".yml",".toml",".ini",".cfg"]
ALLOWED_SCRIPTS=[".sh",".bat",".ps1",".bash",".zsh"]
ALLOWED_MEDIA=[".jpg",".jpeg",".png",".gif",".bmp",".svg",".mp3",".wav",".mp4",".avi",".mkv"]
ALLOWED_EXTENSIONS=ALLOWED_PYTHON+ALLOWED_DOCS+ALLOWED_CONFIG+ALLOWED_SCRIPTS+ALLOWED_MEDIA
DEFAULT_COPY_FORMAT="blocks"
COPY_FORMAT_PRESETS={"blocks":"{path}:\n\"\"\"\n{content}\n\"\"\"\n","lines":"{path}: {content}\n","raw":"{content}\n"}
SCROLL_SPEED={"normal":1,"accelerated":5}
MAX_TREE_DEPTH=10
SIZE_DISPLAY_THRESHOLD=10*1024*1024
ANONYMIZED_PREFIXES=["Folder","Project","Repo","Alpha","Beta","Omega","Block","Archive","Data","Source"]
INPUT_TIMEOUT=0.1

class AppConfig:
    def __init__(self,copy_format:str,path_mode:str):
        self.copy_format=copy_format
        self.path_mode=path_mode

def human_readable_size(s:int)->str:
    if s<1024:return f"{s}B"
    elif s<1024**2:return f"{s/1024:.1f}K"
    elif s<1024**3:return f"{s/(1024**2):.1f}M"
    return f"{s/(1024**3):.1f}G"

def copy_text_to_clipboard(t:str)->None:
    try:
        if sys.platform.startswith("win"):
            p=subprocess.Popen("clip",stdin=subprocess.PIPE,shell=True)
            p.communicate(input=t.encode("utf-16"))
        elif sys.platform.startswith("darwin"):
            p=subprocess.Popen("pbcopy",stdin=subprocess.PIPE)
            p.communicate(input=t.encode("utf-8"))
        else:
            p=subprocess.Popen(["xclip","-selection","clipboard"],stdin=subprocess.PIPE)
            p.communicate(input=t.encode("utf-8"))
    except:pass

class FileFilter:
    def __init__(self,ignored_patterns:Optional[List[str]]=None,allowed_extensions:Optional[List[str]]=None):
        self.ignored_patterns=ignored_patterns or []
        self.allowed_extensions=allowed_extensions or []
    def is_ignored(self,n:str)->bool:
        for p in self.ignored_patterns:
            if p in n:return True
        _,ext=os.path.splitext(n)
        if self.allowed_extensions and ext and ext.lower() not in self.allowed_extensions:return True
        return False

class TreeNode:
    def __init__(self,p:str,is_dir:bool=False,expanded:bool=False):
        self.path=p
        self.is_dir=is_dir
        self.expanded=expanded
        self.original_name=os.path.basename(p)
        self.display_name=self.original_name
        self.anonymized=False
        self.disabled=None if is_dir else False
        self.children=[]
    def add_child(self,n:"TreeNode")->None:
        self.children.append(n)
    def sort_children(self)->None:
        self.children.sort(key=lambda x:(not x.is_dir,x.display_name.lower()))

def build_tree(rp:str,f:FileFilter)->TreeNode:
    root=TreeNode(rp,True,True)
    def w(p:TreeNode,d:str,depth:int=0)->None:
        if depth>MAX_TREE_DEPTH:return
        try:e=sorted(os.listdir(d))
        except:return
        flt=[]
        for i in e:
            x=os.path.join(d,i)
            if f.is_ignored(i):continue
            if os.path.isdir(x)or os.path.isfile(x):flt.append(i)
        for j in flt:
            fp=os.path.join(d,j)
            if os.path.isdir(fp):
                c=TreeNode(fp,True,False)
                p.add_child(c)
                w(c,fp,depth+1)
            else:
                c=TreeNode(fp,False,False)
                p.add_child(c)
        p.sort_children()
    w(root,rp,0)
    return root

def load_state(fp:str)->Dict[str,Any]:
    if os.path.isfile(fp):
        try:
            with open(fp,"r",encoding="utf-8")as f:return json.load(f)
        except:return {}
    return{}

def save_state(fp:str,d:Dict[str,Any])->None:
    try:
        with open(fp,"w",encoding="utf-8")as f:json.dump(d,f,indent=2)
    except:pass

def apply_state(n:TreeNode,s:Dict[str,Any])->None:
    if n.path in s:
        st=s[n.path]
        n.expanded=st.get("expanded",n.is_dir)
        n.anonymized=st.get("anonymized",False)
        if n.anonymized:
            n.display_name=st.get("anonymized_name",n.original_name)
        else:
            n.display_name=n.original_name
        if not n.is_dir:
            n.disabled=st.get("disabled",False)
    for c in n.children:apply_state(c,s)

def gather_state(n:TreeNode,s:Dict[str,Any])->None:
    if n.path not in s:s[n.path]={}
    s[n.path]["expanded"]=n.expanded
    s[n.path]["anonymized"]=n.anonymized
    if n.anonymized:
        s[n.path]["anonymized_name"]=n.display_name
    else:
        s[n.path]["anonymized_name"]=None
    if not n.is_dir:
        s[n.path]["disabled"]=n.disabled
    for c in n.children:gather_state(c,s)

def generate_anonymized_name()->str:
    return random.choice(ANONYMIZED_PREFIXES)+"_"+("".join(random.choices(string.ascii_uppercase+string.digits,k=4)))

def toggle_node(n:TreeNode)->None:
    if n.is_dir:n.expanded=not n.expanded

def anonymize_toggle(n:TreeNode)->None:
    if n.is_dir:
        x=not n.anonymized
        n.anonymized=x
        n.display_name=generate_anonymized_name()if x else n.original_name

def set_subtree_expanded(n:TreeNode,e:bool)->None:
    n.expanded=e
    for c in n.children:
        if c.is_dir:set_subtree_expanded(c,e)

def toggle_subtree(n:TreeNode)->None:
    if n.is_dir:
        x=not n.expanded
        set_subtree_expanded(n,x)

def anonymize_subtree(n:TreeNode)->None:
    if n.is_dir:
        x=not n.anonymized
        n.anonymized=x
        n.display_name=generate_anonymized_name()if x else n.original_name
        for c in n.children:anonymize_subtree(c)

def flatten_tree(n:TreeNode,d:int=0)->Generator[Tuple[TreeNode,int],None,None]:
    yield(n,d)
    if n.is_dir and n.expanded:
        for c in n.children:yield from flatten_tree(c,d+1)

def collect_visible_files(n:TreeNode,path_mode:str)->List[Tuple[str,str]]:
    r=[]
    def g(nd:TreeNode,p:List[str]):
        z=p+[nd.display_name]
        if nd.is_dir and nd.expanded:
            for ch in nd.children:g(ch,z)
        elif not nd.is_dir and nd.disabled==False:
            rp=os.path.join(*z)if path_mode=="relative"else nd.display_name
            ct=""
            try:
                with open(nd.path,"r",encoding="utf-8")as f:ct=f.read()
            except:ct="<Could not read file>"
            r.append((rp,ct))
    g(n,[])
    return r

def copy_files_subloop(stdscr:Any,vf:List[Tuple[str,str]],fmt:str)->str:
    lines=[]
    my,mx=stdscr.getmaxyx()
    t=len(vf)
    for i,(rp,ct) in enumerate(vf,1):
        fs=fmt
        if fs not in COPY_FORMAT_PRESETS:fs="blocks"
        block=COPY_FORMAT_PRESETS[fs].format(path=rp,content=ct if ct else"<Could not read file>")
        lines.append(block)
        bw=max(10,mx-25)
        dn=int(bw*(i/t))if t else 0
        rm=bw-dn
        bs="#"*dn+" "*rm
        ps=f"Copying {i}/{t} files: [{bs}]"
        stdscr.clear()
        stdscr.addnstr(my-1,0,ps,mx-1)
        stdscr.refresh()
    return"".join(lines)

def init_colors()->None:
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1,curses.COLOR_CYAN,-1)
    curses.init_pair(2,curses.COLOR_GREEN,-1)
    curses.init_pair(3,curses.COLOR_RED,-1)
    curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLUE)

def run_curses(stdscr:Any,root:TreeNode,states:Dict[str,Any],fmt:str,path_mode:str)->None:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)
    curses.halfdelay(int(INPUT_TIMEOUT*10))
    init_colors()
    ci=0
    so=0
    sm=False
    cs=False
    stime=0.0
    while True:
        n=time.time()
        if cs and(n-stime>SUCCESS_MESSAGE_DURATION):cs=False
        stdscr.clear()
        my,mx=stdscr.getmaxyx()
        fz=list(flatten_tree(root))
        vl=my-1
        if ci<0:ci=0
        elif ci>=len(fz):ci=max(0,len(fz)-1)
        if ci<so:so=ci
        elif ci>=so+vl:so=ci-vl+1
        for i in range(so,min(so+vl,len(fz))):
            nd,dp=fz[i]
            sel=(i==ci)
            y=i-so
            x=0
            ar="> "if sel else"  "
            stdscr.addstr(y,x,ar)
            x+=len(ar)
            px="│  "*dp
            stdscr.addstr(y,x,px)
            x+=len(px)
            if nd.is_dir:
                c=2
                stdscr.addstr(y,x,nd.display_name,curses.color_pair(c))
                x+=len(nd.display_name)
                try:
                    ss=human_readable_size(os.path.getsize(nd.path))
                except:ss="?"
                st=f"  ({ss})"
                if x+len(st)>=mx:st=st[:mx-x-1]+"..."
                stdscr.addstr(y,x,st)
            else:
                c=3 if nd.disabled else 1
                stdscr.addstr(y,x,nd.display_name,curses.color_pair(c))
                x+=len(nd.display_name)
                if nd.disabled:
                    ds=" (DISABLED)"
                    if x+len(ds)>=mx:ds=ds[:mx-x-1]+"..."
                    stdscr.addstr(y,x,ds)
                    x+=len(ds)
                try:
                    ss=human_readable_size(os.path.getsize(nd.path))
                except:ss="?"
                st=f"  ({ss})"
                if x+len(st)>=mx:st=st[:mx-x-1]+"..."
                stdscr.addstr(y,x,st)
        if cs:
            m="Successfully Saved to Clipboard"
            p=m+" "*(mx-len(m))
            stdscr.addnstr(my-1,0,p,mx-1)
        else:
            ins=""
            if fz:
                nd,_=fz[ci]
                if nd.is_dir:
                    if sm:
                        ins+="[E] Toggle All"
                        if not nd.anonymized:ins+="  [A] Anonymize All"
                        else:ins+="  [A] De-Anonymize All"
                    else:
                        ins+="[e] Toggle"
                        if not nd.anonymized:ins+="  [a] Anonymize"
                        else:ins+="  [a] De-Anonymize"
                else:
                    if nd.disabled:ins+="[d] Enable"
                    else:ins+="[d] Disable"
                ins+="   [c] Copy"
            stdscr.addnstr(my-1,0,ins,mx-1)
        stdscr.refresh()
        k=stdscr.getch()
        if k==-1:continue
        if 65<=k<=90:sm=True
        elif 97<=k<=122:sm=False
        sp=SCROLL_SPEED["accelerated"]if sm else SCROLL_SPEED["normal"]
        if k in(curses.KEY_UP,ord("w"),ord("W")):
            ci=max(0,ci-sp)
        elif k in(curses.KEY_DOWN,ord("s"),ord("S")):
            ci=min(len(fz)-1,ci+sp)
        elif k in(curses.KEY_ENTER,10,13):
            nd,_=fz[ci]
            if nd.is_dir:toggle_node(nd)
        elif sm:
            if k==ord("E"):
                nd,_=fz[ci]
                if nd.is_dir:toggle_subtree(nd)
            elif k==ord("A"):
                nd,_=fz[ci]
                if nd.is_dir:anonymize_subtree(nd)
        else:
            if k==ord("e"):
                nd,_=fz[ci]
                if nd.is_dir:toggle_node(nd)
            elif k==ord("a"):
                nd,_=fz[ci]
                if nd.is_dir:anonymize_toggle(nd)
            elif k==ord("d"):
                nd,_=fz[ci]
                if not nd.is_dir:nd.disabled=not nd.disabled
            elif k==ord("c"):
                vf=collect_visible_files(root,path_mode)
                if vf:
                    ft=copy_files_subloop(stdscr,vf,fmt)
                    copy_text_to_clipboard(ft)
                    cs=True
                    stime=time.time()
        if k in(ord("q"),ord("Q")):
            s={}
            gather_state(root,s)
            save_state(STATE_FILE,s)
            break

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("directory",nargs="?",default=".")
    parser.add_argument("--copy-format",choices=["blocks","lines","raw"],default=DEFAULT_COPY_FORMAT)
    parser.add_argument("--path-mode",choices=["relative","basename"],default="basename")
    a=parser.parse_args()
    if not os.path.isdir(a.directory):
        print(f"Error: '{a.directory}' is not a directory.")
        sys.exit(1)
    f=FileFilter(ignored_patterns=IGNORED_PATTERNS,allowed_extensions=ALLOWED_EXTENSIONS)
    rp=os.path.abspath(a.directory)
    root=build_tree(rp,f)
    st=load_state(STATE_FILE)
    apply_state(root,st)
    curses.wrapper(run_curses,root,st,a.copy_format,a.path_mode)

if __name__=="__main__":
    main()
