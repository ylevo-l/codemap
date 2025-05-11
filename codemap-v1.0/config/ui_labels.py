KEY_BINDINGS={"copy":"c","paste":"p","save":"b","load":"v","toggle":"e","toggle_all":"E","enable":"d","disable":"d","refactor":"r","refactor_all":"R"}

LABEL_NAMES={"copy":"Copy","paste":"Paste","save":"Save","load":"Load","toggle":"Toggle","toggle_all":"Toggle All","enable":"Enable","disable":"Disable","refactor":"Refactor","refactor_all":"Refactor All"}

def _make(n):
    k=KEY_BINDINGS[n]
    return f'[{k}] {LABEL_NAMES[n]}'

TOKEN_LABEL="Tokens"

COPY_LABEL=_make("copy")

PASTE_LABEL=_make("paste")

SAVE_LABEL=_make("save")

LOAD_LABEL=_make("load")

TOGGLE_LABEL=_make("toggle")

TOGGLE_ALL_LABEL=_make("toggle_all")

ENABLE_LABEL=_make("enable")

DISABLE_LABEL=_make("disable")

REFACTOR_LABEL=_make("refactor")

REFACTOR_ALL_LABEL=_make("refactor_all")

NO_FILES_LABEL="No files to display."

NO_TOKENS_LABEL="No tokens to copy."

SUCCESS_MESSAGE="Successfully Copied to Clipboard"

REFACTOR_SUCCESS_MESSAGE="File refactored successfully."

REFACTOR_ALL_SUCCESS_MESSAGE="All included files refactored successfully."

SEPARATOR="·"

__all__=["TOKEN_LABEL","COPY_LABEL","PASTE_LABEL","SAVE_LABEL","LOAD_LABEL","TOGGLE_LABEL","TOGGLE_ALL_LABEL","ENABLE_LABEL","DISABLE_LABEL","REFACTOR_LABEL","REFACTOR_ALL_LABEL","NO_FILES_LABEL","NO_TOKENS_LABEL","SUCCESS_MESSAGE","REFACTOR_SUCCESS_MESSAGE","REFACTOR_ALL_SUCCESS_MESSAGE","SEPARATOR","KEY_BINDINGS","LABEL_NAMES"]
