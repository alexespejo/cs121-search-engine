import sys
from typing import List, Dict, Set
from utils.constants import STOP_WORDS

def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    current: List[str] = []
    for ch in text:
        if ch.isascii() and (ch.isalpha() or ch.isdigit()):
            current.append(ch.lower())
        else:
            if current:
                tokens.append("".join(current))
                current.clear()
    if current:
        tokens.append("".join(current))
    return tokens

def compute_word_frequencies(tokens: List[str]) -> Dict[str, int]:
    res = {}
    for token in tokens:
        if (token not in STOP_WORDS):
            if token in res:
                res[token] += 1
            else:
                res[token] = 1
    return res

def print_frequencies(frequencies: Dict[str, int]) -> None:
    sorted_items = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    for word, count in sorted_items:
        print(f"{word} = {count}")

def get_tokens_set(text_file_path: str) -> Set[str]:
    return set(tokenize(text_file_path))

def count_common_tokens(file1_path: str, file2_path: str) -> int:
    tokens_file1 = get_tokens_set(file1_path)
    tokens_file2 = get_tokens_set(file2_path)
    
    common_tokens = tokens_file1.intersection(tokens_file2)
    
    return len(common_tokens)
