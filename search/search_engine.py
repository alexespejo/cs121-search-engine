from indexer.inverted_index import InvertedIndex
from query import Query, QueryType
import utils.constants as const

from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)

class SearchEngine:
    def __init__(self, index_dir: str):
        self.inv_index: InvertedIndex = InvertedIndex()
        self.query: Query

        index_path: Path = Path(index_dir)
        self.doc_id_to_url, self.url_to_doc_id = self.inv_index.load_index(index_path)
    
    def accept_query(self, input_message: str) -> None:
        query_str: str = input(input_message)
        self.query = Query(query_str)

    def boolean_query(self) -> list[str]:
        self.query
        return []

    def get_search_results(self, type: QueryType = QueryType.boolean, top: int = const.TOP_RESULTS_DEFAULT) -> list[str]:
        results: list[str] = []
        match type:
            case QueryType.boolean:
                results = self.boolean_query()
            case _:
                results = self.boolean_query()

        if top < 0:
            logger.warning("top is negative, returning all results")
            return results
        elif top == 0:
            return results
        else:
            return results[:top]
        
    def display_results(self, result_url_list: list[str]):
        print("=" * 70)
        print(f"Search Results for query: \"{self.query}\"")
        print("=" * 70)
        result_len: int = len(result_url_list)
        if result_len == 0:
            print(f"There were no results for query: \"{self.query}\"")
        else:
            for i in range(len(result_url_list)):
                print(f"{i + 1}: {result_url_list[i]}")
        print("=" * 70)
        