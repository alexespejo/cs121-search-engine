import utils.constants as const

class Posting:
    def __init__(self, doc_id: int):
        self.doc_id = doc_id
        self.counts = {
            "body": 0,
            "title": 0,
            "h1": 0,
            "h2": 0,
            "h3": 0,
            "bold": 0,
            "anchor": 0
        }
        self.weighted_tf = 0.0

    def add(self, kind: str):
        if kind not in self.counts:
            self.counts[kind] = 0
        self.counts[kind] += 1

    def get_weighted_tf(self):
        if self.weighted_tf != 0:
            return self.weighted_tf
        return sum(self.counts[k] * const.TAG_WEIGHTS.get(k, 1.0) for k in self.counts)

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.doc_id < other
        else:
            return self.doc_id < other.doc_id