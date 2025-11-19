from logging import DEBUG, INFO, WARNING, ERROR

NS_TO_MS = 1e+6

DATA_DIR_DEFAULT = "data/DEV"

INDEX_DIR_DEFAULT = "index"
DEBUG_INDEX_DIR_DEFAULT = "debug_index"
TMP_DIR = "tmp"

TOP_RESULTS_DEFAULT = 5

LOG_DIR = "log"

LOG_LEVELS = {
    "debug": DEBUG,
    "info": INFO,
    "warn": WARNING,
    "error": ERROR,
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
