from logging import DEBUG, INFO, WARNING, ERROR
from struct import calcsize

# ======================================== CONFIG ========================================
SCORING_WEIGHTS = {
    "tf-idf" : 6.0,       # weighting of TF-IDF scoring method
    "pagerank" : 1.5,     # weighting of PageRank scoring method
    "url" : 1.0           # weighting of the query terms all being in the URL
}
TAG_WEIGHTS = {
    "body": 1.0,
    "title": 5.5,
    "h1": 4.0,
    "h2": 2.5,
    "h3": 1.75,
    "bold": 1.25,
    "anchor": 4.5
}
HAMMING_THRESHOLD = 5

BATCH_SIZE_DEFAULT = 15_000
TOP_RESULTS_DEFAULT = 5
ZONES = {
    "body_tokens":   "body",
    "title_tokens":  "title",
    "h1_tokens":     "h1",
    "h2_tokens":     "h2",
    "h3_tokens":     "h3",
    "bold_tokens":   "bold",
    "anchor_tokens": "anchor"
}
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}


# ======================================== CONFIG END ========================================

# ======================================== FILE ========================================
DATA_DIR_DEFAULT = "data/DEV"
INDEX_DIR_DEFAULT = "index"
DEBUG_INDEX_DIR_DEFAULT = "index_debug"
TMP_DIR = "index_tmp"
LOG_DIR = "log"
FILE_LIST_FILENAME = "file_list"
INDEX_FILENAME = "inverted_index"
# ======================================== FILE END ========================================

# ======================================== MMAP ========================================
# quick reference
# #s => char[#]
# I => uint32
# Q => uint64
# H => unsigned short
# f => float

# INDEX
INDEX_HEADER_MAGIC = b"NIDX" # should be 4 bytes
INDEX_HEADER_MAGIC_SIZE = len(INDEX_HEADER_MAGIC)
if INDEX_HEADER_MAGIC_SIZE != 4:
    raise TypeError("INDEX: Inappropriate header magic number")
INDEX_HEADER_VERSION = 2

# magic, version, index_dict_offset, url_map_offset
INDEX_HEADER_FMT = f"<{INDEX_HEADER_MAGIC_SIZE}sIQQ"
INDEX_HEADER_SIZE = calcsize(INDEX_HEADER_FMT)

# length of the index_dict
INDEX_DICT_LEN_FMT = "<I" 
INDEX_DICT_LEN_SIZE = calcsize(INDEX_DICT_LEN_FMT)

# length of the term
TERM_LEN_FMT = "<H" 
TERM_LEN_SIZE = calcsize(TERM_LEN_FMT)

# postings count
POSTING_COUNT_FMT = "<I"
POSTING_COUNT_SIZE = calcsize(POSTING_COUNT_FMT)

# posting itself
POSTING_FMT = "<IIIIIIII" # @TODO MAY CHANGE
POSTING_SIZE = calcsize(POSTING_FMT)

# length of the doc_id to url dict 
URL_DICT_LEN_FMT = "<I"
URL_DICT_LEN_SIZE = calcsize(URL_DICT_LEN_FMT)

# doc_id itself
DOC_ID_FMT = "<I"
DOC_ID_SIZE = calcsize(DOC_ID_FMT)

# length of the doc_id
DOC_ID_LEN_FMT = "<I"
DOC_ID_LEN_SIZE = calcsize(DOC_ID_LEN_FMT)

# url itself
URL_FMT = "<H"
URL_SIZE = calcsize(URL_FMT)

# length of the url
URL_LEN_FMT = "<H"
URL_LEN_SIZE = calcsize(URL_LEN_FMT)

OFFSETS_FMT = "<QQ"
OFFSETS_SIZE = calcsize(OFFSETS_FMT)

# ======================================== MMAP END ========================================


# ======================================== TYPE CONVERSION ========================================
NS_TO_MS = 1e+6
BYTES_TO_KB = 1024
BYTES_TO_MB = 1024**2
BYTES_TO_GB = 1024**3
BYTES_TO_TB = 1024**4
# ======================================== TYPE CONVERSION END ========================================

# ======================================== LOG LEVEL ========================================
LOG_LEVELS = {
    "debug": DEBUG,
    "info": INFO,
    "warn": WARNING,
    "error": ERROR,
}
# ======================================== LOG LEVEL END ========================================

# ======================================== SETS ========================================
SKIP_EXTENSIONS = {
    '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
    '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
    '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flv',
    '.exe', '.dll', '.bin', '.dmg', '.iso',
    '.css', '.js', '.json', '.xml', '.csv'
}

SKIP_MIME_TYPES = {
    'text/plain', 'text/css', 'text/javascript', 'application/javascript',
    'application/json', 'application/xml', 'text/xml', 'text/csv',
    'application/pdf', 'application/zip', 'application/x-rar-compressed',
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/svg+xml',
    'video/mp4', 'video/mpeg', 'audio/mpeg', 'audio/wav',
    'application/octet-stream'
}

INVALID_TAGS = {
    'script', 'style', 'noscript', 'link', 'meta', 
    'nav', 'header', 'footer', 'aside', 'form', 
    'input', 'button', 'select', 'textarea', 
    'label', 'iframe', 'svg', 'canvas', 'template',
    'object', 'embed', 'applet', 'picture', 'source'
}
# ======================================== SETS END ========================================

