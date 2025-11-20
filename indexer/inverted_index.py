from utils.file_io import is_valid_dir
import utils.constants as const

from collections import defaultdict
from typing import Dict, List
from pathlib import Path
import struct
import mmap
from logging import getLogger

logger = getLogger(__name__)

def open_mmap(inv_index_path: Path):
    f = open(inv_index_path, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    return f, mm

def get_posting(inv_index_path: Path, term: str) -> List[tuple[int, float]]:
    f, mm = open_mmap(inv_index_path)
    
    try:
        # read header
        magic, _, index_dict_offset, _ = const.HEADER_STRUCT.unpack_from(mm, 0)
        if magic != b"MYDB":
            error_message : str = "Incorrect Magic Number, likely incorrect file."
            logger.error(error_message)
            raise IOError(error_message)
        ptr = index_dict_offset
        term_count = struct.unpack_from("<I", mm, ptr)[0]
        ptr += 4

        term_b = term.encode()

        for _ in range(term_count):
            term_len = const.TERM_LEN_STRUCT.unpack_from(mm, ptr)[0]
            ptr += 2

            t_bytes = mm[ptr : ptr + term_len]
            ptr += term_len

            p_len = const.POSTING_COUNT_STRUCT.unpack_from(mm, ptr)[0]
            ptr += 4

            if t_bytes == term_b:
                postings = []
                for _ in range(p_len):
                    doc_id, tf = const.DOC_TF_STRUCT.unpack_from(mm, ptr)
                    ptr += const.DOC_TF_STRUCT.size
                    postings.append((doc_id, tf))
                return postings

            ptr += p_len * const.DOC_TF_STRUCT.size

        return []

    finally:
        mm.close()
        f.close()

def get_url(inv_index_path: Path, doc_id: int) -> str:
    f, mm = open_mmap(inv_index_path)

    try:
        magic, _, _, url_offset = const.HEADER_STRUCT.unpack_from(mm, 0)
        if magic != b"MYDB":
            error_message : str = "Incorrect Magic Number, likely incorrect file."
            logger.error(error_message)
            raise IOError(error_message)
        ptr = url_offset

        url_count = struct.unpack_from("<I", mm, ptr)[0]
        ptr += 4

        for _ in range(url_count):
            did = struct.unpack_from("<I", mm, ptr)[0]
            ptr += 4
            url_len = const.URL_LEN_STRUCT.unpack_from(mm, ptr)[0]
            ptr += 2

            url_bytes = mm[ptr : ptr + url_len]
            ptr += url_len

            if did == doc_id:
                return url_bytes.decode()
        
        return ""

    finally:
        mm.close()
        f.close()

def load_index_from_mmap(segment_file: Path) -> "InvertedIndex":
    """
    Reads a full inverted index segment from disk into an InvertedIndex object.
    """
    index = InvertedIndex()
    f, mm = open_mmap(segment_file)
    try:
        magic, _, index_dict_offset, doc_id_to_url_offset = const.HEADER_STRUCT.unpack_from(mm, 0)
        if magic != b"MYDB":
            raise IOError(f"Incorrect Magic Number in {segment_file}")

        ptr = index_dict_offset
        term_count = struct.unpack_from("<I", mm, ptr)[0]
        ptr += 4
        for _ in range(term_count):
            term_len = const.TERM_LEN_STRUCT.unpack_from(mm, ptr)[0]
            ptr += 2
            term_bytes = mm[ptr : ptr + term_len]
            term = term_bytes.decode()
            ptr += term_len

            postings_len = const.POSTING_COUNT_STRUCT.unpack_from(mm, ptr)[0]
            ptr += 4

            postings = [const.DOC_TF_STRUCT.unpack_from(mm, ptr + i*8) for i in range(postings_len)]
            ptr += postings_len * 8

            index.index_dict[term].extend(postings)
            del postings

        ptr = doc_id_to_url_offset
        doc_count = struct.unpack_from("<I", mm, ptr)[0]
        ptr += 4
        for _ in range(doc_count):
            doc_id = struct.unpack_from("<I", mm, ptr)[0]
            ptr += 4
            url_len = struct.unpack_from("<H", mm, ptr)[0]
            ptr += 2
            url = mm[ptr : ptr + url_len].decode()
            ptr += url_len
            index.doc_id_to_url[doc_id] = url

    finally:
        mm.close()
        f.close()
        import gc
        gc.collect()

    return index

class InvertedIndex:
    def __init__(self):
        self.index_dict: Dict[str, List[tuple[int, float]]] = defaultdict(list)
        self.doc_id_to_url: Dict[int, str] = {}

    def add_entry(self, term: str, doc_id: int, term_frequency: float) -> None:
        self.index_dict[term].append((doc_id, term_frequency))

    def save_index(self, inv_index_path: Path) -> None:
        with open(inv_index_path, "wb") as f:
            # Header
            f.write(b"MYDB")
            f.write(struct.pack("<I", 1))
            f.write(b"\x00" * 16)

            offsets = {}
            
            # index_dict
            offsets["index_dict"] = f.tell()

            f.write(struct.pack("<I", len(self.index_dict)))

            for term in sorted(self.index_dict):
                posting = self.index_dict[term]

                term_b = term.encode()
                f.write(struct.pack("<H", len(term_b)))
                f.write(term_b)

                f.write(struct.pack("<I", len(posting)))

                for doc_id, tf in posting:
                    f.write(struct.pack("<If", doc_id, tf))

            # doc_id_to_url
            offsets["doc_id_to_url"] = f.tell()
            f.write(struct.pack("<I", len(self.doc_id_to_url)))
            for doc_id in sorted(self.doc_id_to_url):
                url = self.doc_id_to_url[doc_id]

                f.write(struct.pack("<I", doc_id))
                
                url_b = url.encode()
                f.write(struct.pack("<H", len(url_b)))
                f.write(url_b)
                            
            # adding offsets to header
            f.seek(8)
            f.write(struct.pack(
                "<QQ",
                offsets["index_dict"],
                offsets["doc_id_to_url"],
            ))
    
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
