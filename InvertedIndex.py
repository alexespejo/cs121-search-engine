from collections import defaultdict
from typing import Dict, List

class InvertedIndex:
    def __init__(self):
        self.index: Dict[str, List[tuple[int, int]]] = defaultdict(list)

    def addEntry(self, term: str, doc_id: int, frequency: int) -> None:
        self.index[term].append((doc_id, frequency))
