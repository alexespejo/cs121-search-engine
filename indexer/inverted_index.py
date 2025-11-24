from utils.file_io import is_valid_file
import utils.constants as const

from dataclasses import dataclass
from collections import defaultdict
from typing import Dict, List
from pathlib import Path
import struct
import mmap
import gc
from logging import getLogger

logger = getLogger(__name__)

class Posting:
    def __init__(self, doc_id: int, term_frequency: float, importance: float):
        self.doc_id: int = doc_id
        self.term_frequency: float = term_frequency
        self.importance: float = importance
    def __lt__(self, other: "Posting"):
        return self.doc_id < other.doc_id

def validate_magic_num(magic):
    if magic != b"NIDX":
        error_message : str = "Incorrect Magic Number, likely incorrect file."
        logger.error(error_message)
        raise IOError(error_message)

def open_mmap(inv_index_path: Path):
    if not is_valid_file(inv_index_path):
            error_message = f"index directory invalid / missing {inv_index_path}."
            logger.error(error_message)
            raise IOError(error_message)
    f = open(inv_index_path, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    return f, mm

def get_postings(inv_index_path: Path, term: str) -> List[Posting]:
    f, mm = open_mmap(inv_index_path)
    
    try:
        # read header
        ptr = 0
        magic, _, index_dict_offset, _ = struct.unpack_from(const.HEADER_FMT, mm, ptr)
        validate_magic_num(magic)
        ptr = index_dict_offset
        index_dict_len: int = struct.unpack_from(const.INDEX_DICT_LEN_FMT, mm, ptr)[0]
        ptr += const.INDEX_DICT_LEN_SIZE

        term_b = term.encode()

        for _ in range(index_dict_len):
            term_len = struct.unpack_from(const.TERM_LEN_FMT, mm, ptr)[0]
            ptr += const.TERM_LEN_SIZE

            t_bytes = mm[ptr : ptr + term_len]
            ptr += term_len

            p_len = struct.unpack_from(const.POSTING_COUNT_FMT, mm, ptr)[0]
            ptr += const.POSTING_COUNT_SIZE

            if t_bytes == term_b:
                postings = []
                for _ in range(p_len):
                    doc_id, tf, importance = struct.unpack_from(const.POSTING_FMT,mm, ptr)
                    ptr += const.POSTING_SIZE
                    postings.append(Posting(doc_id, tf, importance))
                return postings

            ptr += p_len * const.POSTING_SIZE

        return []

    finally:
        mm.close()
        f.close()

def get_url(inv_index_path: Path, doc_id: int) -> str:
    f, mm = open_mmap(inv_index_path)

    try:
        ptr = 0
        magic, _, _, doc_id_to_url_offset = struct.unpack_from(const.HEADER_FMT, mm, ptr)
        validate_magic_num(magic)
        
        ptr = doc_id_to_url_offset

        doc_count = struct.unpack_from(const.URL_DICT_LEN_FMT, mm, ptr)[0]
        ptr += const.URL_DICT_LEN_SIZE

        for _ in range(doc_count):
            d_id = struct.unpack_from(const.DOC_ID_FMT, mm, ptr)[0]
            ptr += const.DOC_ID_SIZE

            url_len = struct.unpack_from(const.URL_FMT, mm, ptr)[0]
            ptr += const.URL_SIZE
            
            url_bytes = mm[ptr : ptr + url_len]
            ptr += url_len

            if d_id == doc_id:
                return url_bytes.decode()            
                
        return ""

    finally:
        mm.close()
        f.close()

def get_document_count(inv_index_path: Path) -> int:
    """
    Gets the total number of documents in the index.
    Returns the count from the document-to-URL mapping section.
    """
    f, mm = open_mmap(inv_index_path)

    try:
        ptr = 0
        magic, _, _, doc_id_to_url_offset = struct.unpack_from(const.HEADER_FMT, mm, ptr)
        validate_magic_num(magic)
        
        ptr = doc_id_to_url_offset
        url_dict_len = struct.unpack_from(const.URL_DICT_LEN_FMT, mm, ptr)[0]
        return url_dict_len if url_dict_len > 0 else 1

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
        ptr = 0
        magic, _, index_dict_offset, doc_id_to_url_offset = struct.unpack_from(const.HEADER_FMT, mm, ptr)
        validate_magic_num(magic)

        ptr = index_dict_offset
        
        index_dict_len: int = struct.unpack_from(const.INDEX_DICT_LEN_FMT, mm, ptr)[0]
        ptr += const.INDEX_DICT_LEN_SIZE
        for _ in range(index_dict_len):
            term_len = struct.unpack_from(const.TERM_LEN_FMT, mm, ptr)[0]
            ptr += const.TERM_LEN_SIZE

            t_bytes = mm[ptr : ptr + term_len]
            term = t_bytes.decode()
            ptr += term_len

            p_len = struct.unpack_from(const.POSTING_COUNT_FMT, mm, ptr)[0]
            ptr += const.POSTING_COUNT_SIZE

            postings = []
            for i in range(p_len):
                doc_id, tf, importance = struct.unpack_from(const.POSTING_FMT, mm, ptr + (i * const.POSTING_SIZE))
                postings.append(Posting(doc_id, tf, importance))
            ptr += p_len * const.POSTING_SIZE

            index.index_dict[term].extend(postings)
            del postings

        ptr = doc_id_to_url_offset
        doc_count = struct.unpack_from(const.URL_DICT_LEN_FMT, mm, ptr)[0]
        ptr += const.URL_DICT_LEN_SIZE
        for _ in range(doc_count):
            doc_id = struct.unpack_from(const.DOC_ID_FMT, mm, ptr)[0]
            ptr += const.DOC_ID_SIZE
            
            url_len = struct.unpack_from(const.URL_FMT, mm, ptr)[0]
            ptr += const.URL_SIZE
            
            url = mm[ptr : ptr + url_len].decode()
            index.doc_id_to_url[doc_id] = url
            ptr += url_len

    finally:
        mm.close()
        f.close()
        gc.collect()

    return index

class InvertedIndex:
    def __init__(self):
        self.index_dict: Dict[str, List[Posting]] = defaultdict(list)
        self.doc_id_to_url: Dict[int, str] = {}

    def add_posting(self, term: str, posting: Posting) -> None:
        self.index_dict[term].append(posting)

    def save_index(self, inv_index_path: Path) -> None:
        with open(inv_index_path, "wb") as f:
            # Header
            f.write(struct.pack(const.HEADER_FMT, 
                                const.HEADER_MAGIC, 
                                const.HEADER_VERSION, 
                                0, 0)) # two spots for offsets

            offsets = {}
            
            # index_dict
            offsets["index_dict"] = f.tell()

            f.write(struct.pack(const.INDEX_DICT_LEN_FMT, len(self.index_dict)))

            for term in sorted(self.index_dict):
                postings: list[Posting] = self.index_dict[term]

                term_b = term.encode()
                f.write(struct.pack(const.TERM_LEN_FMT, len(term_b)))
                f.write(term_b)

                f.write(struct.pack(const.POSTING_COUNT_FMT, len(postings)))
                for posting in postings:
                    f.write(struct.pack(const.POSTING_FMT, 
                                        posting.doc_id, 
                                        posting.term_frequency, 
                                        posting.importance
                                        ))

            # doc_id_to_url
            offsets["doc_id_to_url"] = f.tell()
            f.write(struct.pack(const.URL_DICT_LEN_FMT, len(self.doc_id_to_url)))
            for doc_id in sorted(self.doc_id_to_url):
                f.write(struct.pack(const.DOC_ID_FMT, doc_id))
                
                url_b = self.doc_id_to_url[doc_id].encode()
                f.write(struct.pack(const.URL_FMT, len(url_b)))
                f.write(url_b)
                            
            # adding offsets to header
            f.seek(const.HEADER_SIZE - const.OFFSETS_SIZE)
            f.write(struct.pack(
                const.OFFSETS_FMT,
                offsets["index_dict"],
                offsets["doc_id_to_url"],
            ))
    
    def get_analytics(self) -> Dict[str, int | float]:
        index = self.index_dict
        doc_map = self.doc_id_to_url

        num_documents = len(doc_map)
        num_unique_tokens = len(index)

        postings_per_token = [len(postings) for postings in index.values()]
        total_postings = sum(postings_per_token)

        return {
            "num_documents": num_documents,
            "num_unique_tokens": num_unique_tokens,
            "total_postings": total_postings,
            "avg_postings_per_token": (total_postings / num_unique_tokens) if num_unique_tokens else 0,
            "max_postings_per_token": max(postings_per_token) if postings_per_token else 0,
            "min_postings_per_token": min(postings_per_token) if postings_per_token else 0,
            "median_postings_per_token": (
                sorted(postings_per_token)[len(postings_per_token) // 2]
                if postings_per_token else 0
            ),
        }

    def display(self, file_name: str | None = None) -> None:
        lines = [
            "",
            "=" * 70,
            f"INVERTED INDEX",
            "=" * 70,
        ]
        sorted_terms = sorted(self.index_dict.keys())
        for term in sorted_terms:
            postings = self.index_dict[term]
            sorted_postings = sorted(postings, key=lambda x: x.doc_id)
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
