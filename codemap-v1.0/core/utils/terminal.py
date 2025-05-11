import os, sys, curses

def reset_terminal(stdscr=None):
    try:
        if stdscr is not None:
            stdscr.keypad(False)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
    except:
        pass
    try:
        if sys.platform.startswith("win"):
            os.system("cls")
        else:
            os.system("clear")
    except:
        pass
