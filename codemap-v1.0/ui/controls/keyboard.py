import keyboard,curses
from ui.controls.manager import ControlManager
from ui.controls.events import Event,EventType
from ui.core.state import State

class KeyboardEventHandler:
    def __init__(self,control_manager:ControlManager,ui_state:State):
        self.control_manager=control_manager
        self.ui_state=ui_state
        self._keyboard_hooked=False
        self._callback_fn=None

    def setup(self,callback_fn=None):
        if self._keyboard_hooked:
            return True
        try:
            self._callback_fn=callback_fn
            keyboard.hook(self._key_handler)
            self._keyboard_hooked=True
            return True
        except:
            return False

    def cleanup(self):
        if self._keyboard_hooked:
            keyboard.unhook_all()
            self._keyboard_hooked=False

    def handle_key(self,key:int):
        if key==-1:
            return False
        evt=self.control_manager.get_event_from_key(key)
        if evt:
            return self.control_manager.handle_event(evt)
        return False

    def _key_handler(self,event:keyboard.KeyboardEvent):
        name=event.name
        ev_down=event.event_type==keyboard.KEY_DOWN
        if name in ("shift","left shift","right shift"):
            if self.ui_state.physical_shift_pressed!=ev_down:
                self.ui_state.set_shift(ev_down)
                self.control_manager.handle_event(Event(EventType.SHIFT_MODE_CHANGED,"keyboard",{"shift":ev_down}))
                if self._callback_fn:
                    self._callback_fn()
        if name in ("delete","del"):
            if self.ui_state.physical_delete_pressed!=ev_down:
                self.ui_state.set_delete(ev_down)
                if self._callback_fn:
                    self._callback_fn()
