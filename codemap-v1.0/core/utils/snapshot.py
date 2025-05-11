import os,shutil,hashlib
from config.constants import SNAPSHOT_DIR

def _hash_path(p:str)->str:
    return hashlib.sha1(os.path.abspath(p).encode()).hexdigest()

def _base_dir(p:str)->str:
    return os.path.join(SNAPSHOT_DIR,_hash_path(p))

def has_snapshot(p:str)->bool:
    return os.path.exists(_base_dir(p))

def save_snapshot(p:str)->bool:
    try:
        dst=_base_dir(p)
        if os.path.exists(dst):
            shutil.rmtree(dst,ignore_errors=True)
        if os.path.isdir(p):
            shutil.copytree(p,dst)
        else:
            os.makedirs(dst,exist_ok=True)
            shutil.copy2(p,os.path.join(dst,os.path.basename(p)))
        return True
    except:
        return False

def _restore_dir(src:str,dst:str):
    for root,dirs,files in os.walk(src):
        rel=os.path.relpath(root,src)
        target=os.path.join(dst,rel) if rel!="." else dst
        os.makedirs(target,exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root,f),os.path.join(target,f))

def load_snapshot(p:str)->bool:
    try:
        src=_base_dir(p)
        if not os.path.exists(src):
            return False
        if os.path.isdir(p):
            _restore_dir(src,p)
        else:
            shutil.copy2(os.path.join(src,os.path.basename(p)),p)
        return True
    except:
        return False

def delete_snapshot(p:str)->bool:
    try:
        shutil.rmtree(_base_dir(p),ignore_errors=True)
        return True
    except:
        return False
