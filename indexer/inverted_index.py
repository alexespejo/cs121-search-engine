from io import BufferedReader
import utils.constants as const

from collections import defaultdict
from pathlib import Path
import struct
import gc
import mmap
from logging import getLogger

logger = getLogger(__name__)

class Posting:
    def __init__(self, doc_id: int, term_frequency: float, importance: float):
        self.doc_id: int = doc_id
        self.term_frequency: float = term_frequency
        self.importance: float = importance
    def __lt__(self, other: "Posting"):
        return self.doc_id < other.doc_id

def validate_magic_num(magic: bytes):
    if magic != b"NIDX":
        error_message : str = f"Incorrect Magic Number, likely incorrect file. {magic.decode()}"
        logger.error(error_message)
        raise IOError(error_message)

def find_term_offset(filename: str, target_term: str):
    """Performs binary search on the term_offsets file, retrieving the offset for the target term

    Args:
        filename (str): file to search
        target (str): target term

    Returns:
        int | None: int offset if found, None if not found
    """
    with open(filename, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        n = len(mm)

        lo, hi = 0, n - 1

        while lo <= hi:
            mid = (lo + hi) // 2

            pos = mid
            while pos > 0 and mm[pos - 1] != ord('\n'):
                pos -= 1

            end = mm.find(b'\n', pos)
            if end == -1:
                end = n

            line = mm[pos:end]
            if not line:
                break

            parts = line.split()
            term = parts[0].decode()

            if term == target_term:
                return int(parts[1])

            if term < target_term:
                lo = end + 1
            else:
                hi = pos - 1

        return None

def get_postings(f: BufferedReader, term: str) -> list[Posting]:
    # read header
    magic, _, _, _ = struct.unpack_from(const.INDEX_HEADER_FMT, f.read(const.INDEX_HEADER_SIZE))
    validate_magic_num(magic)
    
    offset = find_term_offset("index/term_offsets.dat", term)
    if not offset:
        f.seek(0)
        return []
    
    f.seek(offset)
    term_len = struct.unpack_from(const.TERM_LEN_FMT, f.read(const.TERM_LEN_SIZE))[0]
    candidate_term = f.read(term_len)

    if candidate_term.decode() == term:
        postings = []
        p_len = struct.unpack_from(const.POSTING_COUNT_FMT, f.read(const.POSTING_COUNT_SIZE))[0]
        for _ in range(p_len):
            doc_id, tf, importance = struct.unpack_from(const.POSTING_FMT,f.read(const.POSTING_SIZE))
            postings.append(Posting(doc_id, tf, importance))
        f.seek(0)
        return postings

    f.seek(0)
    return []

def get_url(f: BufferedReader, doc_id: int) -> str:
    magic, _, _, doc_id_to_url_offset = struct.unpack_from(const.INDEX_HEADER_FMT, f.read(const.INDEX_HEADER_SIZE))
    validate_magic_num(magic)
    f.seek(doc_id_to_url_offset)

    doc_count = struct.unpack_from(const.URL_DICT_LEN_FMT, f.read(const.URL_DICT_LEN_SIZE))[0]
    for _ in range(doc_count):
        d_id: int = struct.unpack_from(const.DOC_ID_FMT, f.read(const.DOC_ID_SIZE))[0]

        url_len: int = struct.unpack_from(const.URL_FMT, f.read(const.URL_LEN_SIZE))[0]
        
        url_bytes: bytes = f.read(url_len)

        if d_id == doc_id:
            f.seek(0)
            return url_bytes.decode()
            
    f.seek(0)
    return ""

def get_document_count(f: BufferedReader) -> int:
    """
    Gets the total number of documents in the index.
    Returns the count from the document-to-URL mapping section.
    """
    magic, _, _, doc_id_to_url_offset = struct.unpack_from(const.INDEX_HEADER_FMT, f.read(const.INDEX_HEADER_SIZE))
    validate_magic_num(magic)
    f.seek(doc_id_to_url_offset)

    url_dict_len = struct.unpack_from(const.URL_DICT_LEN_FMT, f.read(const.URL_DICT_LEN_SIZE))[0]
    if url_dict_len < 0:
        raise IOError(f"url_dict_len invalid: {url_dict_len}")
    f.seek(0)
    return url_dict_len

def load_index_full(f: BufferedReader) -> "InvertedIndex":
    """
    Reads a full inverted index segment from disk into an InvertedIndex object.
    DO NOT USE IN SEARCH ENGINE; TESTING PURPOSES ONLY
    """
    index = InvertedIndex()
    try:
        magic, _, index_dict_offset, doc_id_to_url_offset = struct.unpack_from(const.INDEX_HEADER_FMT, f.read(const.INDEX_HEADER_SIZE))
        validate_magic_num(magic)
        f.seek(index_dict_offset)
        index_dict_len: int = struct.unpack_from(const.INDEX_DICT_LEN_FMT, f.read(const.INDEX_DICT_LEN_SIZE))[0]

        for _ in range(index_dict_len):
            term_len = struct.unpack_from(const.TERM_LEN_FMT, f.read(const.TERM_LEN_SIZE))[0]

            term = f.read(term_len).decode()

            p_len = struct.unpack_from(const.POSTING_COUNT_FMT, f.read(const.POSTING_COUNT_SIZE))[0]
            postings = []
            for _ in range(p_len):
                doc_id, tf, importance = struct.unpack_from(const.POSTING_FMT, f.read(const.POSTING_SIZE))
                postings.append(Posting(doc_id, tf, importance))

            index.index_dict[term].extend(postings)
            del postings

        f.seek(doc_id_to_url_offset)
        doc_count = struct.unpack_from(const.URL_DICT_LEN_FMT, f.read(const.URL_DICT_LEN_SIZE))[0]
        for _ in range(doc_count):
            doc_id = struct.unpack_from(const.DOC_ID_FMT, f.read(const.DOC_ID_SIZE))[0]
            
            url_len = struct.unpack_from(const.URL_FMT, f.read(const.URL_SIZE))[0]
            
            url = f.read(url_len).decode()
            index.doc_id_to_url[doc_id] = url

    finally:
        gc.collect()
    f.seek(0)
    return index

class InvertedIndex:
    def __init__(self):
        self.index_dict: dict[str, list[Posting]] = defaultdict(list)
        self.doc_id_to_url: dict[int, str] = {}

    def add_posting(self, term: str, posting: Posting) -> None:
        self.index_dict[term].append(posting)

    def save(self, inv_index_path: Path) -> dict[str, int]:
        term_offsets: dict[str, int] = {}
        with open(inv_index_path, "wb") as f:
            # Header
            f.write(struct.pack(const.INDEX_HEADER_FMT, 
                                const.INDEX_HEADER_MAGIC, 
                                const.INDEX_HEADER_VERSION, 
                                0, 0)) # two spots for offsets

            offsets = {}
            
            # index_dict
            offsets["index_dict"] = f.tell()

            f.write(struct.pack(const.INDEX_DICT_LEN_FMT, len(self.index_dict)))

            for term in sorted(self.index_dict):
                term_offsets[term] = f.tell()
                # write a term
                term_b = term.encode()
                f.write(struct.pack(const.TERM_LEN_FMT, len(term_b)))
                f.write(term_b)


                postings: list[Posting] = self.index_dict[term]
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
            f.seek(const.INDEX_HEADER_SIZE - const.OFFSETS_SIZE)
            f.write(struct.pack(
                const.OFFSETS_FMT,
                offsets["index_dict"],
                offsets["doc_id_to_url"],
            ))
        return term_offsets
    
    def get_analytics(self):
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
            "INVERTED INDEX",
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
