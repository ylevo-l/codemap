import curses
from typing import Optional
from core.model import TreeNode
from ui.rendering.text import safe_addnstr
from ui.rendering.colors import DIRECTORY_COLOR
from config.ui_labels import SUCCESS_MESSAGE,COPY_LABEL
from ui.rendering.labels import _create_node_labels,render_node_labels,render_token_info

def render_success_message(stdscr,message=SUCCESS_MESSAGE):
    y,_=stdscr.getmaxyx()
    stdscr.move(y-1,0)
    stdscr.clrtoeol()
    safe_addnstr(stdscr,y-1,0,message,DIRECTORY_COLOR,curses.A_BOLD)

def render_status_bar(stdscr,current:Optional[TreeNode],shift:bool,delete_mode:bool,total_tokens:int,tokens_visible:bool):
    y,xmax=stdscr.getmaxyx()
    stdscr.move(y-1,0)
    stdscr.clrtoeol()
    x=0
    labels=_create_node_labels(current,shift,delete_mode)
    copy_visible=COPY_LABEL in labels
    x=render_node_labels(stdscr,y-1,x,labels,delete_mode)
    x=render_token_info(stdscr,y-1,x,tokens_visible,total_tokens,copy_visible)
    if x<xmax:
        stdscr.move(y-1,x)
        stdscr.clrtoeol()
