from utils.file_io import is_valid_dir
import utils.constants as const

from collections import defaultdict
from typing import Dict, List
from pathlib import Path
import pickle
from logging import getLogger

logger = getLogger(__name__)

class InvertedIndex:
    def __init__(self):
        self.index_dict: Dict[str, List[tuple]] = defaultdict(list)
        self.doc_id_to_url: Dict[int, str] = {}
        self.url_to_doc_id: Dict[str, int] = {}

    def add_entry(self, term: str, doc_id: int, term_frequency: float) -> None:
        self.index_dict[term].append((doc_id, term_frequency))

    def get_analytics(self) -> Dict[str, int | float]:
        index = self.index_dict
        doc_map = self.doc_id_to_url

        num_documents = len(doc_map)
        num_unique_tokens = len(index)

        # postings_per_token: list of lengths of each postings list
        postings_per_token = [len(postings) for postings in index.values()]
        total_postings = sum(postings_per_token)

        # total occurrences counts frequency values inside postings lists
        total_token_occurrences = sum(freq for postings in index.values() for (_, freq) in postings)

        return {
            "num_documents": num_documents,
            "num_unique_tokens": num_unique_tokens,
            "total_postings": total_postings,
            "total_token_occurrences": total_token_occurrences,
            "avg_postings_per_token": (total_postings / num_unique_tokens) if num_unique_tokens else 0,
            "max_postings_per_token": max(postings_per_token) if postings_per_token else 0,
            "min_postings_per_token": min(postings_per_token) if postings_per_token else 0,
            "median_postings_per_token": (
                sorted(postings_per_token)[len(postings_per_token) // 2]
                if postings_per_token else 0
            ),
        }


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

    def save_index_pkl(self, index_path: Path, batch_num: int) -> None:
        if not is_valid_dir(index_path):
            error_message: str = f"index directory invalid / missing {index_path}."
            logger.error(error_message)
            raise IOError(error_message)

        # Save the inverted index
        index_file = index_path / f"{const.INDEX_FILENAME}_{str(batch_num)}.pkl"
        with open(index_file, 'wb') as f:
            pickle.dump(self, f)

        logger.info(f"Index {batch_num} saved to {index_file}")
    
    def get_document_count(inv_index_path: Path) -> int:
        """
        Gets the total number of documents in the index.
        Returns the count from the document-to-URL mapping section.
        """
        f, mm = open_mmap(inv_index_path)

        try:
            magic, _, _, url_offset = const.HEADER_STRUCT.unpack_from(mm, 0)
            if magic != b"MYDB":
                error_message : str = "Incorrect Magic Number, likely incorrect file."
                logger.error(error_message)
                raise IOError(error_message)
            
            ptr = url_offset
            url_count = struct.unpack_from("<I", mm, ptr)[0]
            return url_count if url_count > 0 else 1

        finally:
            mm.close()
            f.close()
    
    # DO NOT USE
    def load_index_pkl(self, index_path: Path) -> None:
        """Load index from disk"""
        if not is_valid_dir(index_path):
            error_message: str = f"index directory invalid / missing {index_path}."
            logger.error(error_message)
            raise IOError(error_message)

        index_file = index_path / const.INDEX_FILENAME # doesn't currently exist as this filename, splitting into per letter
        with open(index_file, 'rb') as f:
            loaded_obj: InvertedIndex = pickle.load(f)
        
        self.index_dict = loaded_obj.index_dict
        self.doc_id_to_url = loaded_obj.doc_id_to_url
        self.url_to_doc_id = loaded_obj.url_to_doc_id
