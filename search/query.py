from enum import Enum
import string

class QueryType(Enum):
    boolean = "boolean",

def is_valid(query_str: str) -> bool:
    if not query_str or not isinstance(query_str, str):
        return False

    allowed_chars = set(string.ascii_letters + string.digits + " ")
    return all(char in allowed_chars for char in query_str)

class Query:
    def __init__(self, query_str: str):
        self.original_str: str = query_str
        self.parsed_query = self.parse_query()
    
    def __repr__(self):
        return self.original_str
    
    def parse_query(self) -> list[str]:
        split_list = self.original_str.split(" ")
        filtered_list = []
        for element in split_list:
            if not is_valid(element):
                # @TODO decide what to do with invalid query terms, currently ignoring them.
                pass
            else:
                filtered_list.append(element.lower())

        return filtered_list