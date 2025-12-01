from search.query import Query, QueryType
import utils.constants as const
from indexer.inverted_index import Posting, get_postings, get_url, get_document_count

from pathlib import Path
from logging import getLogger
from math import log

logger = getLogger(__name__)

class SearchEngine:
    def __init__(self, index_dir: str):
        self.query: Query
        self.index_fptr = open(Path(index_dir) / "main_inverted_index.nidx", "rb")
            
    def accept_query(self, input_message: str) -> None:
        query_str: str = input(input_message)
        self.query = Query(query_str)

    def boolean_query(self, top: int) -> list[tuple[str, float]]:
        """
        Performs a boolean AND query on the inverted index.
        Returns documents containing ALL query terms, ranked by TF-IDF score.
        """
        if not self.query.parsed_query:
            return []
        
        # get postings
        term_postings: dict[str, list[Posting]] = {}
        for term in self.query.parsed_query:
            postings = get_postings(self.index_fptr, term)
            if not postings:
                return []
            term_postings[term] = postings
        
        doc_id_sets = []
        for term, postings in term_postings.items():
            doc_id_set = {posting.doc_id for posting in postings}
            doc_id_sets.append(doc_id_set)
        
        # query intersection
        common_doc_ids = set.intersection(*doc_id_sets)
        
        if not common_doc_ids:
            return []
        
        # tf-idf
        total_docs = get_document_count(self.index_fptr)
      
        term_idf: dict[str, float] = {}
        for term, postings in term_postings.items():
            df = len(postings)  # document frequency
            idf = log(total_docs / df) if df > 0 else 0
            term_idf[term] = idf
        
        doc_scores: dict[int, float] = {}
        term_postings_by_doc = {
            term: {p.doc_id: p.term_frequency for p in postings}
            for term, postings in term_postings.items()
        }
        for doc_id in common_doc_ids:
            score = 0.0
            for term, doc_tf_map in term_postings_by_doc.items():
                tf = doc_tf_map.get(doc_id, 0)
                score += tf * term_idf[term]
            doc_scores[doc_id] = score
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:top]
        
        results: list[tuple[str, float]] = []
        for doc_id, score in sorted_docs:
            url = get_url(self.index_fptr, doc_id)
            if url:
                results.append((url, score))
            else:
                logger.warning(f"Could not find URL for doc_id {doc_id}")
        
        return results

    def get_search_results(self, type: QueryType = QueryType.boolean, top: int = const.TOP_RESULTS_DEFAULT) -> list[str]:
        results_and_score: list[tuple[str, float]] = []
        match type:
            case QueryType.boolean:
                results_and_score = self.boolean_query(top)
            case _:
                results_and_score = self.boolean_query(top)

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
        print()
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
        