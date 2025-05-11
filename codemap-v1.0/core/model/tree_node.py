import os
from typing import List,Optional,Dict

class TreeNode:
    _basename_cache:Dict[str,str]={}
    _MAX_CACHE=10_000

    def __init__(self,path:str,is_dir:bool,parent:Optional["TreeNode"]=None):
        self.path=path
        self.is_dir=is_dir
        self.expanded=False if is_dir else None
        if path in TreeNode._basename_cache:
            self.display_name=TreeNode._basename_cache[path]
        else:
            self.display_name=os.path.basename(path)
            TreeNode._basename_cache[path]=self.display_name
            if len(TreeNode._basename_cache)>TreeNode._MAX_CACHE:
                TreeNode._basename_cache.clear()
        self.render_name=self.display_name
        self.disabled=False if not is_dir else None
        self.children:List["TreeNode"]=[]
        self.token_count=0
        self.parent=parent
    def add_child(self,child:"TreeNode")->None:self.children.append(child)
    def sort_children(self)->None:self.children.sort(key=lambda n:(not n.is_dir,n.display_name.lower()))

    def calculate_token_count(self)->int:
        if not self.is_dir:return 0 if self.disabled else self.token_count
        if not self.expanded:
            self.token_count=0
            return 0
        self.token_count=sum(c.calculate_token_count() for c in self.children if(c.is_dir and c.expanded)or(not c.is_dir and not c.disabled))
        return self.token_count

    def update_token_count(self,delta:int)->None:
        if delta==0:return
        self.token_count+=delta
        if self.parent and self.parent.expanded:
            self.parent.update_token_count(delta)
    def update_render_name(self)->None:self.render_name=self.display_name
    @staticmethod
    def clear_caches()->None:TreeNode._basename_cache.clear()
