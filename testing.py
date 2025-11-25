import utils.constants as const
from indexer.inverted_index import InvertedIndex, load_index_from_mmap

from pathlib import Path

if __name__ == "__main__":
    idx: InvertedIndex = load_index_from_mmap(Path(const.INDEX_DIR_DEFAULT) / "main_inverted_index.nidx")
    idx.display("tests/print_idx_full.result")
