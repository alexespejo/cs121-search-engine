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
        """
        Tokenize the raw query string and return a list of unique, stemmed tokens.

        This implementation avoids NLTK's word_tokenize so we don't depend on
        external 'punkt' / 'punkt_tab' resources, which are hard to download
        in some environments.
        """
        if not query_str:
            return []

        allowed_chars = set(string.ascii_letters + string.digits + " ")
        if not all(char in allowed_chars for char in query_str):
            return []

        stemmer = PorterStemmer()
        tokens = [
            word.lower()
            for word in query_str.split()
            if word.isalnum()
        ]

        unique_query_words = {
            stemmer.stem(word, to_lowercase=False) for word in tokens
        }
        return list(unique_query_words)
    