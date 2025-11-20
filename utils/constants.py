from logging import DEBUG, INFO, WARNING, ERROR
from struct import Struct

BATCH_SIZE_DEFAULT = 1 # 15_000

DATA_DIR_DEFAULT = "data/DEV"
INDEX_DIR_DEFAULT = "index"
DEBUG_INDEX_DIR_DEFAULT = "index_debug"
TMP_DIR = "index_tmp"
LOG_DIR = "log"

FILE_LIST_FILENAME = "file_list.pkl"
INDEX_FILENAME = "inverted_index"

HEADER_STRUCT = Struct("<4sIQQ")   # magic, version, index_dict_off, url_map_offset
TERM_LEN_STRUCT = Struct("<H")
POSTING_COUNT_STRUCT = Struct("<I")
DOC_TF_STRUCT = Struct("<If")
URL_LEN_STRUCT = Struct("<H")

NS_TO_MS = 1e+6
BYTES_TO_KB = 1024
BYTES_TO_MB = 1024**2
BYTES_TO_GB = 1024**3
BYTES_TO_TB = 1024**4

TOP_RESULTS_DEFAULT = 5

LOG_LEVELS = {
    "debug": DEBUG,
    "info": INFO,
    "warn": WARNING,
    "error": ERROR,
}

SUB_INDEX_MAPPING = {
    "a" : "sub_inverted_index_a_e.pkl",
    "b" : "sub_inverted_index_a_e.pkl",
    "c" : "sub_inverted_index_a_e.pkl",
    "d" : "sub_inverted_index_a_e.pkl",
    "e" : "sub_inverted_index_a_e.pkl",

    "f" : "sub_inverted_index_f_j.pkl",
    "g" : "sub_inverted_index_f_j.pkl",
    "h" : "sub_inverted_index_f_j.pkl",
    "i" : "sub_inverted_index_f_j.pkl",
    "j" : "sub_inverted_index_f_j.pkl",

    "k" : "sub_inverted_index_k_o.pkl",
    "l" : "sub_inverted_index_k_o.pkl",
    "m" : "sub_inverted_index_k_o.pkl",
    "n" : "sub_inverted_index_k_o.pkl",
    "o" : "sub_inverted_index_k_o.pkl",

    "p" : "sub_inverted_index_p_t.pkl",
    "q" : "sub_inverted_index_p_t.pkl",
    "r" : "sub_inverted_index_p_t.pkl",
    "s" : "sub_inverted_index_p_t.pkl",
    "t" : "sub_inverted_index_p_t.pkl",

    "u" : "sub_inverted_index_u_z.pkl",
    "v" : "sub_inverted_index_u_z.pkl",
    "w" : "sub_inverted_index_u_z.pkl",
    "x" : "sub_inverted_index_u_z.pkl",
    "y" : "sub_inverted_index_u_z.pkl",
    "z" : "sub_inverted_index_u_z.pkl",

    "0" : "sub_inverted_index_0_9.pkl",
    "1" : "sub_inverted_index_0_9.pkl",
    "2" : "sub_inverted_index_0_9.pkl",
    "3" : "sub_inverted_index_0_9.pkl",
    "4" : "sub_inverted_index_0_9.pkl",
    "5" : "sub_inverted_index_0_9.pkl",
    "6" : "sub_inverted_index_0_9.pkl",
    "7" : "sub_inverted_index_0_9.pkl",
    "8" : "sub_inverted_index_0_9.pkl",
    "9" : "sub_inverted_index_0_9.pkl",
}

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
