import argparse,os,sys,threading,curses
from functools import partial
import core.utils.debug
from config import IGNORED_PATTERNS,ALLOWED_EXTENSIONS,STATE_FILE
from core.filesystem import FileFilter,build_tree,watch_filesystem
from core.operations import calculate_token_counts,token_count_manager
from core.utils.state import load_state,apply_state
from core.utils.sweeper import start_maintenance
from ui.application import run_application

class CodeMap:
    def __init__(self,root_path,copy_format,path_mode):
        self.root_path=root_path;self.copy_format=copy_format;self.path_mode=path_mode
        self.file_filter=FileFilter(IGNORED_PATTERNS,ALLOWED_EXTENSIONS)
        self.path_to_node={};self.lock=threading.Lock()
        self.root_node=build_tree(self.root_path,self.file_filter,self.path_to_node,self.lock)
        apply_state(self.root_node,load_state(STATE_FILE),base_path=self.root_node.path,is_root=True)
        self.tree_changed_flag=threading.Event();self.stop_event=threading.Event()
        self._start_background_threads()

    def _start_background_threads(self):
        threading.Thread(target=calculate_token_counts,args=(self.root_node,self.path_to_node,self.tree_changed_flag,self.lock),daemon=True).start()
        threading.Thread(target=watch_filesystem,args=(self.root_path,self.file_filter,self.path_to_node,self.tree_changed_flag,self.stop_event,self.lock),daemon=True).start()
        start_maintenance(token_count_manager,self.file_filter,120.0)

    def run(self):
        try:curses.wrapper(partial(run_application,root_node=self.root_node,path_to_node=self.path_to_node,fmt=self.copy_format,path_mode=self.path_mode,tree_changed_flag=self.tree_changed_flag,lock=self.lock))
        finally:self.stop_event.set()

def _parse_args():
    p=argparse.ArgumentParser(description='CodeMap - A file tree explorer for code')
    p.add_argument('directory',nargs='?',default='.',help='Directory to scan for code files.')
    p.add_argument('--copy-format',choices=['blocks','lines','raw','optimized','compact','dash'],default='dash',help='Format used for copying file segments.')
    p.add_argument('--path-mode',choices=['relative','basename'],default='relative',help='Display mode for file paths.')
    return p.parse_args()

def run():
    a=_parse_args()
    if not os.path.isdir(a.directory):
        print(f"Error: '{a.directory}' is not a directory.");sys.exit(1)
    CodeMap(os.path.abspath(a.directory),a.copy_format,a.path_mode).run()

if __name__=='__main__':run()
