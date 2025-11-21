from indexer.inverted_index import InvertedIndex
from query import Query, QueryType
import utils.constants as const
from utils.file_io import is_valid_file
from indexer.inverted_index import get_posting, get_url, get_document_count

import pickle
import bisect
from pathlib import Path
from logging import getLogger
from math import log
from typing import Dict

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
        """
        Performs a boolean AND query on the inverted index.
        Returns documents containing ALL query terms, ranked by TF-IDF score.
        """
        if not self.query.parsed_query:
            logger.warning("Empty query provided")
            return []
        
        # get postings
        term_postings: dict[str, list[tuple[int, float]]] = {}
        for term in self.query.parsed_query:
            postings = get_posting(self.index_file, term)
            if not postings:
                logger.info(f"Term '{term}' not found in index")
                return []
            term_postings[term] = postings
        
        doc_id_sets = []
        for term, postings in term_postings.items():
            doc_id_set = {doc_id for doc_id, _ in postings}
            doc_id_sets.append(doc_id_set)
        
        # query intersection
        common_doc_ids = set.intersection(*doc_id_sets)
        
        if not common_doc_ids:
            logger.info("No documents contain all query terms")
            return []
        
        # tf-idf
        total_docs = get_document_count(self.index_file)
      
        term_idf: dict[str, float] = {}
        for term, postings in term_postings.items():
            df = len(postings)  # document frequency
            idf = log(total_docs / df) if df > 0 else 0
            term_idf[term] = idf
        
        doc_scores: dict[int, float] = {}
        for doc_id in common_doc_ids:
            score = 0.0
            for term, postings in term_postings.items():
                tf = next((freq for did, freq in postings if did == doc_id), 0)
                idf = term_idf[term]
                score += tf * idf
            doc_scores[doc_id] = score
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        
        results: list[tuple[str, float]] = []
        for doc_id, score in sorted_docs:
            url = get_url(self.index_file, doc_id)
            if url:
                results.append((url, score))
            else:
                logger.warning(f"Could not find URL for doc_id {doc_id}")
        
        return results

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
        