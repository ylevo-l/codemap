import curses,re
from typing import Optional,List
from core.model import TreeNode
from ui.rendering.text import safe_addnstr
from ui.rendering.colors import GENERAL_UI_COLOR,UI_BRACKET_COLOR,DISABLED_COLOR
from ui.core.labels import render_single_label
from config.ui_labels import COPY_LABEL,PASTE_LABEL,TOGGLE_LABEL,TOGGLE_ALL_LABEL,ENABLE_LABEL,DISABLE_LABEL,NO_FILES_LABEL,NO_TOKENS_LABEL,SEPARATOR,REFACTOR_LABEL,REFACTOR_ALL_LABEL,SAVE_LABEL,LOAD_LABEL
from core.operations.tree_ops import are_all_files_enabled
from core.utils.snapshot import has_snapshot
from core.utils.clipboard import has_valid_paste

_BRACKET_PATTERN=re.compile(r'(\[[^\]]+\])(.*)')

def _split_label(t):
    m=_BRACKET_PATTERN.match(t)
    if m:
        return m.group(1),m.group(2)
    return None,t

def _compact(t,shift):
    if shift and t.endswith(" All"):
        return t[:-4]
    return t

def _upper_bracket(lbl):
    return re.sub(r'\[([a-z])\]',lambda m:f'[{m.group(1).upper()}]',lbl)

def _create_node_labels(current:Optional[TreeNode],shift:bool,delete_mode:bool)->List[str]:
    labels=[]
    if current:
        snap=has_snapshot(current.path)
        if current.is_dir:
            labels.append(_compact(TOGGLE_ALL_LABEL if shift else TOGGLE_LABEL,shift))
            if shift and current.expanded:
                labels.append(_compact(REFACTOR_ALL_LABEL,shift))
            if shift:
                dlabel=DISABLE_LABEL if are_all_files_enabled(current) else ENABLE_LABEL
                labels.append(_upper_bracket(dlabel))
            labels.append(LOAD_LABEL if snap else SAVE_LABEL)
            if current.expanded:
                labels.append(COPY_LABEL)
            if has_valid_paste(current.path,True):
                labels.append(PASTE_LABEL)
        else:
            labels.append(ENABLE_LABEL if current.disabled else DISABLE_LABEL)
            labels.append(REFACTOR_LABEL)
            labels.append(LOAD_LABEL if snap else SAVE_LABEL)
            if not current.disabled:
                labels.append(COPY_LABEL)
            if has_valid_paste(current.path,False):
                labels.append(PASTE_LABEL)
    else:
        labels.append(NO_FILES_LABEL)
    return labels

def render_node_labels(stdscr,y:int,x:int,node_labels:List[str],delete_mode:bool)->int:
    for i,text in enumerate(node_labels):
        br,rest=_split_label(text)
        if br:
            color=DISABLED_COLOR if delete_mode and text.startswith("[v]") else UI_BRACKET_COLOR
            safe_addnstr(stdscr,y,x,br,color)
            x+=len(br)
            safe_addnstr(stdscr,y,x,rest,GENERAL_UI_COLOR)
            x+=len(rest)
        else:
            safe_addnstr(stdscr,y,x,text,GENERAL_UI_COLOR)
            x+=len(text)
        if i<len(node_labels)-1:
            sep=f' {SEPARATOR} '
            safe_addnstr(stdscr,y,x,sep,GENERAL_UI_COLOR)
            x+=len(sep)
    return x

def render_token_info(stdscr,y:int,x:int,tokens_visible:bool,total_tokens:int,copy_visible:bool)->int:
    if not tokens_visible and total_tokens>0:
        ctx={'total_tokens':total_tokens}
        x=render_single_label(stdscr,y,x,'tokens',ctx,separator=SEPARATOR,separator_color=GENERAL_UI_COLOR,show_separator=True)
    elif not tokens_visible and total_tokens==0 and copy_visible:
        sep=f' {SEPARATOR} '
        safe_addnstr(stdscr,y,x,sep,GENERAL_UI_COLOR)
        x+=len(sep)
        safe_addnstr(stdscr,y,x,NO_TOKENS_LABEL,GENERAL_UI_COLOR)
        x+=len(NO_TOKENS_LABEL)
    return x
