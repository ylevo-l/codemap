from concurrent.futures import ThreadPoolExecutor
from typing import List
from .ops import refactor_file

def refactor_files(files: List[str], max_workers: int = 8):
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(refactor_file, files))
