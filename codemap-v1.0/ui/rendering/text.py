import curses

_COLOR_CACHE:dict[int,int]={}

def _color_attr(c:int)->int:
    a=_COLOR_CACHE.get(c)
    if a is None:
        a=curses.color_pair(c)
        _COLOR_CACHE[c]=a
    return a

def safe_addnstr(stdscr,y,x,text,color,attr=0):
    if not text:
        return
    try:
        max_y,max_x=stdscr.getmaxyx()
        if y<0 or y>=max_y or x<0 or x>=max_x:
            return
        max_chars=max_x-x-1
        if max_chars<=0:
            return
        display=text if len(text)<=max_chars else text[:max_chars]
        stdscr.addstr(y,x,display,_color_attr(color)|attr)
    except:
        pass

def clear_line(stdscr,y,x):
    try:
        max_y,max_x=stdscr.getmaxyx()
        if 0<=y<max_y and 0<=x<max_x:
            stdscr.move(y,x)
            stdscr.clrtoeol()
    except:
        try:
            max_y,max_x=stdscr.getmaxyx()
            if 0<=y<max_y and 0<=x<max_x:
                stdscr.addstr(y,x," "*(max_x-x-1))
        except:
            pass
