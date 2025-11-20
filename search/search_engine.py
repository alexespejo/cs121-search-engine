from indexer.inverted_index import InvertedIndex
from search.query import Query, QueryType
import utils.constants as const
from utils.file_io import is_valid_file

import pickle
import bisect
from pathlib import Path
from logging import getLogger
from math import log
from typing import Dict
from collections import defaultdict

logger = getLogger(__name__)

class SearchEngine:
    def __init__(self, index_dir: str):
        self.query: Query
        self.index_path: Path = Path(index_dir)
        
        meta_path: Path = Path(f"{self.index_path}/{const.META_FILENAME}.pkl")
        if not is_valid_file(meta_path):
            error_message: str = f"Invalid meta path: {meta_path}"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        with open(meta_path, "rb") as f:
            self.meta: Dict[str, int | float] = pickle.load(f)
    
    def accept_query(self, input_message: str) -> None:
        query_str: str = input(input_message)
        self.query = Query(query_str)

    def boolean_query(self) -> list[tuple[str, float]]:
        return []

    def get_search_results(self, type: QueryType = QueryType.boolean, top: int = const.TOP_RESULTS_DEFAULT) -> list[str]:
        results_and_score: list[tuple[str, float]] = []
        match type:
            case QueryType.boolean:
                results_and_score = self.boolean_query()
            case _:
                results_and_score = self.boolean_query()

        results = [e[0] for e in results_and_score]
        if top < 0:
            logger.warning("top is negative, returning all results")
            return [e[0] for e in results]
        elif top == 0:
            logger.warning("top is zero, returning zero results")
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
        