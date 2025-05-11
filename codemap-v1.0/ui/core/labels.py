import curses
from typing import Dict, Any, List, Optional, Callable, Union
from ui.rendering.text import safe_addnstr
from ui.rendering.colors import TOKEN_LABEL_COLOR, GENERAL_UI_COLOR
from config.ui_labels import TOKEN_LABEL, SEPARATOR

class StatusLabel:
    def __init__(self, key: str, name: str, value_getter: Callable[[Dict[str, Any]], Any] = None,
                 label_color: int = TOKEN_LABEL_COLOR, value_color: int = GENERAL_UI_COLOR):
        self.key = key
        self.name = name
        self.value_getter = value_getter
        self.label_color = label_color
        self.value_color = value_color

    def get_value(self, context: Optional[Dict[str, Any]] = None) -> str:
        if self.value_getter is None:
            return ""
        if context is None:
            context = {}
        try:
            value = self.value_getter(context)
            return str(value) if value is not None else ""
        except:
            return ""

class StatusLabelRegistry:
    def __init__(self):
        self.labels = {}

    def register(self, label: StatusLabel) -> None:
        self.labels[label.key] = label

    def get(self, key: str) -> Optional[StatusLabel]:
        return self.labels.get(key)

    def get_all(self) -> List[StatusLabel]:
        return list(self.labels.values())

registry = StatusLabelRegistry()

def render_status_label(stdscr, y: int, x: int, label: StatusLabel,
                        context: Optional[Dict[str, Any]] = None,
                        separator: str = SEPARATOR,
                        separator_color: int = GENERAL_UI_COLOR,
                        show_separator: bool = True) -> int:
    if context is None:
        context = {}
    if show_separator and x > 0:
        sep_text = f' {separator} '
        safe_addnstr(stdscr, y, x, sep_text, separator_color)
        x += len(sep_text)
    safe_addnstr(stdscr, y, x, label.name, label.label_color)
    x += len(label.name)
    value = label.get_value(context)
    if value:
        value_text = f': {value}'
        safe_addnstr(stdscr, y, x, value_text, label.value_color)
        x += len(value_text)
    return x

def render_status_labels(stdscr, y: int, x: int,
                         labels: List[Union[str, StatusLabel]],
                         context: Optional[Dict[str, Any]] = None,
                         separator: str = SEPARATOR,
                         separator_color: int = GENERAL_UI_COLOR) -> int:
    if context is None:
        context = {}
    for i, label_item in enumerate(labels):
        if isinstance(label_item, str):
            label = registry.get(label_item)
            if not label:
                continue
        else:
            label = label_item
        x = render_status_label(
            stdscr, y, x, label, context,
            separator, separator_color,
            show_separator=(i > 0)
        )
    return x

def render_single_label(stdscr, y: int, x: int, label_key: str,
                        context: Optional[Dict[str, Any]] = None,
                        separator: str = SEPARATOR,
                        separator_color: int = GENERAL_UI_COLOR,
                        show_separator: bool = True) -> int:
    label = registry.get(label_key)
    if label:
        return render_status_label(
            stdscr, y, x, label, context,
            separator, separator_color, show_separator
        )
    return x

def token_value_getter(context: Dict[str, Any]) -> str:
    if "node" in context and hasattr(context["node"], "token_count"):
        return context["node"].token_count
    if "node_tokens" in context:
        return context["node_tokens"]
    if "total_tokens" in context and context["total_tokens"] > 0:
        return context["total_tokens"]
    return ""

def register_default_labels():
    token_label = StatusLabel(
        key="tokens",
        name=TOKEN_LABEL,
        value_getter=token_value_getter,
        label_color=TOKEN_LABEL_COLOR,
        value_color=GENERAL_UI_COLOR
    )
    registry.register(token_label)

register_default_labels()
