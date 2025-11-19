from enum import Enum

class QueryType(Enum):
    boolean = "boolean",
    
class Query:
    def __init__(self, query_str: str):
        self.original_str: str = query_str
        self.parsed_query = self.parse_query()
    def __repr__(self):
        return self.original_str
    def parse_query(self):
        pass