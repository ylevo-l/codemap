import os,threading,curses
from typing import Optional,Dict,List,Tuple,Set
from core.model import TreeNode
from core.operations import toggle_node,toggle_subtree
from core.operations.tree_ops import are_all_files_enabled,toggle_folder_enable_state
from core.utils.clipboard import copy_files_subloop,copy_text_to_clipboard,has_valid_paste,paste_into
from core.refactor.ops  import refactor_file
from core.refactor.bulk import refactor_files
from core.utils.state   import gather_state,save_state
from core.utils.snapshot import save_snapshot,load_snapshot,delete_snapshot,has_snapshot
from core.utils.terminal import reset_terminal
from core.utils.debug import log
from config import STATE_FILE
from config.ui_labels import REFACTOR_SUCCESS_MESSAGE,REFACTOR_ALL_SUCCESS_MESSAGE,SUCCESS_MESSAGE
from ui.controls.events    import EventType
from ui.controls.navigation import NavigationHandler
from ui.core.state         import State

class ActionHandler:
    def __init__(self,stdscr,ui_state:State,root_node:TreeNode,path_to_node:Dict[str,TreeNode],fmt:str,path_mode:str,tree_changed_flag:threading.Event,lock:threading.Lock):
        self.stdscr=stdscr;self.ui_state=ui_state;self.root_node=root_node;self.path_to_node=path_to_node
        self.fmt=fmt;self.path_mode=path_mode;self.tree_changed_flag=tree_changed_flag;self.lock=lock
        self.current_node:Optional[TreeNode]=None;self.flattened_cache:List[Tuple[TreeNode,int,bool]]=[];self.selected_node_path:Optional[str]=None
        self.navigation_handler=NavigationHandler(ui_state)

    def update_context(self,c:Optional[TreeNode],flat:List[Tuple[TreeNode,int,bool]]):
        self.current_node=c;self.flattened_cache=flat
        if c:self.selected_node_path=c.path

    def _visible_enabled_descendants(self,folder:TreeNode)->List[TreeNode]:
        out=[]

        def walk(nd:TreeNode):
            if nd.is_dir:
                if nd is not folder and not nd.expanded:return
                for ch in nd.children:walk(ch)
            elif not nd.disabled:out.append(nd)
        walk(folder);return out

    def _file_content(self,p:str)->str:
        try:
            with open(p,"rb") as f:return f.read().decode("latin-1")
        except:return"<Could not read file>"
    canon=staticmethod(lambda p:os.path.normcase(os.path.abspath(p)))
    def _rel(self,p:str)->str:return os.path.relpath(p,self.root_node.path)
    def handle_navigation_up(self,e):s=self.ui_state.physical_shift_pressed;self.ui_state.current_index=self.navigation_handler.navigate(-1,self.flattened_cache,s);return True
    def handle_navigation_down(self,e):s=self.ui_state.physical_shift_pressed;self.ui_state.current_index=self.navigation_handler.navigate(1,self.flattened_cache,s);return True

    def handle_toggle_node(self,e):
        if not(self.current_node and self.current_node.is_dir):return False
        with self.lock:toggle_node(self.current_node);self.root_node.calculate_token_count();self.tree_changed_flag.set()
        return True

    def handle_toggle_subtree(self,e):
        if not(self.current_node and self.current_node.is_dir):return False
        with self.lock:toggle_subtree(self.current_node);self.root_node.calculate_token_count();self.tree_changed_flag.set()
        return True

    def handle_toggle_disable(self,e):
        if not(self.current_node and not self.current_node.is_dir):return False
        with self.lock:
            self.current_node.disabled=not self.current_node.disabled;self.current_node.update_render_name()
            self.root_node.calculate_token_count();self.tree_changed_flag.set();log("DISABLE" if self.current_node.disabled else "ENABLE",self._rel(self.current_node.path))
        return True

    def handle_copy_content(self,e):
        if not self.current_node:return False
        root_path=self.root_node.path;files=[]
        if self.current_node.is_dir:
            for nd in self._visible_enabled_descendants(self.current_node):
                files.append((os.path.relpath(nd.path,root_path),self._file_content(nd.path)))
        else:files.append((os.path.relpath(self.current_node.path,root_path),self._file_content(self.current_node.path)))
        if not files:return False
        copy_text=copy_files_subloop(self.stdscr,files,self.fmt);copy_text_to_clipboard(copy_text);self.ui_state.set_success(SUCCESS_MESSAGE);return True

    def _allowed_targets(self)->Set[str]:
        if self.current_node.is_dir:return{self.canon(n.path) for n in self._visible_enabled_descendants(self.current_node)}
        return{self.canon(self.current_node.path)}

    def handle_paste_content(self,e):
        if not self.current_node:return False
        if not has_valid_paste(self.current_node.path,self.current_node.is_dir):return False
        allowed=self._allowed_targets()
        if not allowed:return False
        if paste_into(self.current_node.path,self.current_node.is_dir,allowed):
            self.tree_changed_flag.set();self.ui_state.set_success("Pasted from Clipboard");return True
        return False

    def handle_refactor_content(self,e):
        if not self.current_node:return False
        if self.current_node.is_dir:
            if not(e.data and e.data.get("shift",False) and self.current_node.expanded):return False
            paths=[n.path for n in self._visible_enabled_descendants(self.current_node)]
            if not paths:return False
            refactor_files(paths);log("REFACTOR_ALL",len(paths),"file(s)",self._rel(self.current_node.path));self.ui_state.set_success(REFACTOR_ALL_SUCCESS_MESSAGE);return True
        if refactor_file(self.current_node.path):
            log("REFACTOR",self._rel(self.current_node.path));self.ui_state.set_success(REFACTOR_SUCCESS_MESSAGE);return True
        return False

    def handle_save_content(self,_):
        if not self.current_node or has_snapshot(self.current_node.path):return False
        if save_snapshot(self.current_node.path):
            log("SNAPSHOT_SAVE",self._rel(self.current_node.path));self.ui_state.set_success("Snapshot saved");return True
        return False

    def handle_load_content(self,_):
        if not self.current_node or not has_snapshot(self.current_node.path):return False
        if self.ui_state.physical_delete_pressed:
            if delete_snapshot(self.current_node.path):
                log("SNAPSHOT_DELETE",self._rel(self.current_node.path));self.ui_state.set_success("Snapshot deleted");return True
            return False
        if load_snapshot(self.current_node.path):
            log("SNAPSHOT_LOAD",self._rel(self.current_node.path));self.ui_state.set_success("Snapshot loaded");self.tree_changed_flag.set();return True
        return False
    def handle_enter_key(self,e):return self.handle_toggle_node(e)

    def handle_quit(self,_):
        with self.lock:
            state={};gather_state(self.root_node,state,self.root_node.path,True);save_state(STATE_FILE,state)
        reset_terminal(self.stdscr);self.ui_state.should_quit=True;return True
    def handle_shift_mode_changed(self,_):return True

    def handle_shift_disable_all(self,_):
        if not(self.current_node and self.current_node.is_dir):return False
        with self.lock:
            new_state=not are_all_files_enabled(self.current_node)
            toggle_folder_enable_state(self.current_node,new_state);self.root_node.calculate_token_count();self.tree_changed_flag.set();log("ENABLE_ALL" if new_state else "DISABLE_ALL",self._rel(self.current_node.path))
        return True

    def register_handlers(self,cm):
        cm.register_handler(EventType.NAVIGATION_UP,self.handle_navigation_up);cm.register_handler(EventType.NAVIGATION_DOWN,self.handle_navigation_down)
        cm.register_handler(EventType.TOGGLE_NODE,self.handle_toggle_node);cm.register_handler(EventType.TOGGLE_SUBTREE,self.handle_toggle_subtree)
        cm.register_handler(EventType.TOGGLE_DISABLE,self.handle_toggle_disable);cm.register_handler(EventType.COPY_CONTENT,self.handle_copy_content)
        cm.register_handler(EventType.PASTE_CONTENT,self.handle_paste_content);cm.register_handler(EventType.REFACTOR_CONTENT,self.handle_refactor_content)
        cm.register_handler(EventType.SAVE_CONTENT,self.handle_save_content);cm.register_handler(EventType.LOAD_CONTENT,self.handle_load_content)
        cm.register_handler(EventType.ENTER_KEY,self.handle_enter_key);cm.register_handler(EventType.QUIT,self.handle_quit)
        cm.register_handler(EventType.SHIFT_MODE_CHANGED,self.handle_shift_mode_changed);cm.register_handler(EventType.SHIFT_DISABLE_ALL,self.handle_shift_disable_all)
