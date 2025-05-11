import os, re
from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token

def get_lexer(language: str, source: str):
    try:
        return get_lexer_by_name(language)
    except:
        return guess_lexer(source)

def filter_tokens(source: str, lexer):
    return "".join(v for t, v in lex(source, lexer) if t not in Token.Comment and t not in Token.Literal.String.Doc)

def remove_extra_whitespace(code: str):
    code = re.sub(r"\n\s*\n+", "\n\n", code)
    code = re.sub(r"[ \t]+$", "", code, flags=re.M)
    return code.strip()

def determine_language(file_path: str):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    mapping = {".py": "python", ".js": "javascript", ".html": "html", ".css": "css", ".java": "java", ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".cs": "csharp", ".php": "php", ".rb": "ruby", ".go": "go", ".rs": "rust", ".ts": "typescript", ".tsx": "typescript", ".jsx": "jsx", ".sql": "sql", ".sh": "bash", ".json": "json", ".yaml": "yaml", ".yml": "yaml"}
    return mapping.get(ext, "text")

def strip_comments_and_docstrings(source: str, language: str = "python"):
    return remove_extra_whitespace(filter_tokens(source, get_lexer(language, source)))
