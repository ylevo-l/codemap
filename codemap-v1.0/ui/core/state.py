import threading,time
from typing import Set
from config import SCROLL_SPEED
from config.ui_labels import SUCCESS_MESSAGE

class State:
    def __init__(self):
        self.current_index=0
        self.scroll_offset=0
        self.physical_shift_pressed=False
        self.physical_delete_pressed=False
        self.copying_success=False
        self.success_message_time=0.0
        self.success_message=SUCCESS_MESSAGE
        self.should_quit=False
        self.redraw_needed=threading.Event()
        self.step_normal=SCROLL_SPEED["normal"]
        self.step_accel=SCROLL_SPEED["accelerated"]
        self._changed:Set[str]=set()
        self._lock=threading.RLock()

    def _mark(self,p:str):
        self._changed.add(p)
        self.redraw_needed.set()

    def update_selected_index(self,d:int,s:int,shift:bool=False):
        if not s:
            self.current_index=0
            return
        step=self.step_accel if shift else self.step_normal
        idx=self.current_index+(-step if d<0 else step if d>0 else 0)
        idx=max(0,min(s-1,idx))
        if idx!=self.current_index:
            self.current_index=idx
            self._mark("current_index")

    def ensure_visible(self,l:int,s:int):
        if not s:
            self.scroll_offset=0
            self.current_index=0
            return
        if self.current_index<self.scroll_offset:
            self.scroll_offset=self.current_index
            self._mark("scroll_offset")
        elif self.current_index>=self.scroll_offset+l:
            self.scroll_offset=self.current_index-l+1
            self._mark("scroll_offset")

    def set_success(self,m:str):
        self.copying_success=True
        self.success_message=m
        self.success_message_time=time.time()
        self._mark("copying_success")

    def clear_success_if_expired(self,d:float)->bool:
        if self.copying_success and time.time()-self.success_message_time>d:
            self.copying_success=False
            self._mark("copying_success")
            return True
        return False

    def set_shift(self,p:bool):
        if p!=self.physical_shift_pressed:
            self.physical_shift_pressed=p
            self._mark("shift")

    def set_delete(self,p:bool):
        if p!=self.physical_delete_pressed:
            self.physical_delete_pressed=p
            self._mark("delete")

    def has_changes(self)->bool:
        return bool(self._changed)

    def reset_changes(self):
        self._changed.clear()
