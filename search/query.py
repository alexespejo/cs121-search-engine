from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

from enum import Enum
import string

class QueryType(Enum):
    boolean = "boolean",

class Query:
    def __init__(self, query_str: str):
        self.original_str: str = query_str
        self.parsed_query = self.parse_query(query_str)
    
    def __repr__(self):
        return self.original_str

    def parse_query(self, query_str: str) -> list[str]:
        if not query_str:
            return []
        allowed_chars = set(string.ascii_letters + string.digits + " ")
        if not all(char in allowed_chars for char in query_str):
            return []
        
        stemmer = PorterStemmer()
        unique_query_words = set([stemmer.stem(word.lower(), to_lowercase=True) for word in word_tokenize(self.original_str)])
        return list(unique_query_words)
    