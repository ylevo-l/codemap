import curses

FILE_COLOR=1

DIRECTORY_COLOR=2

DISABLED_COLOR=3

UI_LABEL_COLOR=4

TOKEN_LABEL_COLOR=5

GENERAL_UI_COLOR=7

STRUCTURE_COLOR=8

UI_BRACKET_COLOR=9

SELECTED_FILE_COLOR=10

SELECTED_DIRECTORY_COLOR=11

SELECTED_DISABLED_COLOR=12

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(DIRECTORY_COLOR,curses.COLOR_GREEN,-1)
    curses.init_pair(FILE_COLOR,curses.COLOR_WHITE,-1)
    curses.init_pair(DISABLED_COLOR,curses.COLOR_RED,-1)
    curses.init_pair(UI_LABEL_COLOR,curses.COLOR_YELLOW,-1)
    curses.init_pair(TOKEN_LABEL_COLOR,curses.COLOR_GREEN,-1)
    curses.init_pair(GENERAL_UI_COLOR,curses.COLOR_WHITE,-1)
    curses.init_pair(STRUCTURE_COLOR,curses.COLOR_WHITE,-1)
    curses.init_pair(UI_BRACKET_COLOR,curses.COLOR_GREEN,-1)
    curses.init_pair(SELECTED_FILE_COLOR,curses.COLOR_WHITE,-1)
    curses.init_pair(SELECTED_DIRECTORY_COLOR,curses.COLOR_GREEN,-1)
    curses.init_pair(SELECTED_DISABLED_COLOR,curses.COLOR_RED,-1)
