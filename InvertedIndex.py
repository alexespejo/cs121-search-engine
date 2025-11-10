from collections import defaultdict
from typing import Dict, List

class InvertedIndex:
    # TODO: implement singleton
    def __init__(self):
        self.index = defaultdict[str, List[defaultdict[int, int]]]

    def addEntry(self) -> None:
        
