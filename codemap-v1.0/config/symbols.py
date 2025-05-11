import os,sys

def _fits(char:str)->bool:
    enc=sys.stdout.encoding or "utf-8"
    try:
        char.encode(enc)
        return True
    except UnicodeEncodeError:
        return False

def _pick(preferred:str,ascii_fallback:str)->str:
    return preferred if _fits(preferred) else ascii_fallback

CURSOR_SYMBOL_SELECTED="> "

CURSOR_SYMBOL_UNSELECTED="  "

CURSOR_SYMBOL=CURSOR_SYMBOL_SELECTED

ARROW_COLLAPSED=_pick("▸ ","+ ")

ARROW_EXPANDED=_pick("▾ ","- ")

BRANCH_SYMBOL=_pick("╎ ","| ")

__all__=[
    "CURSOR_SYMBOL_SELECTED","CURSOR_SYMBOL_UNSELECTED","CURSOR_SYMBOL",
    "ARROW_COLLAPSED","ARROW_EXPANDED","BRANCH_SYMBOL"

]
