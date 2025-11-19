from utils.file_io import is_valid_dir

from collections import defaultdict
from typing import Dict, List
from pathlib import Path
import pickle
from logging import getLogger

logger = getLogger(__name__)

class InvertedIndex:
    def __init__(self):
        self.index_dict: Dict[str, List[tuple[int, int]]] = defaultdict(list)

    def addEntry(self, term: str, doc_id: int, frequency: int) -> None:
        self.index_dict[term].append((doc_id, frequency))

    def display(self, file_name = None) -> None:
        lines = [
            "",
            "=" * 70,
            f"INVERTED INDEX",
            "=" * 70,
        ]
        sorted_terms = sorted(self.index_dict.keys())
        for term in sorted_terms:
            postings = self.index_dict[term]
            sorted_postings = sorted(postings, key=lambda x: x[0])
            lines.append(f"'{term}' -> {sorted_postings}")
        lines.append("=" * 70)
        lines.append("")
        
        content = "\n".join(lines)
        
        if not file_name:
            print(content)
        else:
            file_path: Path = Path(file_name)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    def save_index_pkl(self, batch_num: int, index_path: Path, doc_id_to_url: dict[int, str], url_to_doc_id: dict[str, int]) -> None:
        if not is_valid_dir(index_path):
            error_message: str = f"index directory invalid / missing {index_path}."
            logger.error(error_message)
            raise IOError(error_message)

        batch_folder = index_path / str(batch_num)
        batch_folder.mkdir(parents=True, exist_ok=True)

        # Save the inverted index
        index_file = batch_folder / 'inverted_index.pkl'
        with open(index_file, 'wb') as f:
            pickle.dump(dict(self.index_dict), f)

        # Save doc_id_to_url mapping
        doc_map_file = batch_folder / 'doc_id_to_url.pkl'
        with open(doc_map_file, 'wb') as f:
            pickle.dump(doc_id_to_url, f)

        # Save url_to_doc_id mapping
        url_map_file = batch_folder / 'url_to_doc_id.pkl'
        with open(url_map_file, 'wb') as f:
            pickle.dump(url_to_doc_id, f)

        logger.info(f"Index {batch_num} saved to {batch_folder}")
    
    # @TODO fix so it aggregates indexes
    def load_index(self, index_path: Path) -> tuple[dict[int, str], dict[str, int]]:
        """Load index from disk"""
        if not is_valid_dir(index_path):
            error_message: str = f"index directory invalid / missing {index_path}."
            logger.error(error_message)
            raise IOError(error_message)
        
        index_file = index_path / 'inverted_index.pkl'
        with open(index_file, 'rb') as f:
            index_dict = pickle.load(f)
            self.index_dict = defaultdict(list, index_dict)
        
        doc_map_file = index_path / 'doc_id_to_url.pkl'
        with open(doc_map_file, 'rb') as f:
            doc_id_to_url: dict[int, str] = pickle.load(f)
        
        url_map_file = index_path / 'url_to_doc_id.pkl'
        with open(url_map_file, 'rb') as f:
            url_to_doc_id: dict[str, int] = pickle.load(f)
        return doc_id_to_url, url_to_doc_id