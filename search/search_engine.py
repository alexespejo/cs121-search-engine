from search.query import Query, QueryType
import utils.constants as const
from indexer.inverted_index import Posting, get_postings, get_url, get_document_count
from indexer.PageRank import get_page_rank

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

    def boolean_query_tf_idf(self, top: int) -> list[tuple[int, str, float]]:
        """
        Performs a boolean AND query on the inverted index.
        Returns documents containing ALL query terms, ranked by TF-IDF score.
        
        Returns:
            List of (doc_id, url, tfidf_score) tuples.
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
        
        results: list[tuple[int, str, float]] = []
        for doc_id, score in sorted_docs:
            url = get_url(self.index_fptr, doc_id)
            if url:
                results.append((doc_id, url, score))
            else:
                logger.warning(f"Could not find URL for doc_id {doc_id}")
        
        return results

    def get_search_results(self, type: QueryType = QueryType.boolean, top: int = const.TOP_RESULTS_DEFAULT) -> list[tuple[int, str, float]]:
        """
        Get search results with doc_id, url, and tfidf score.
        
        Returns:
            List of (doc_id, url, tfidf_score) tuples.
        """
        results = self.boolean_query_tf_idf(top)
        # match type:
        #     case QueryType.boolean:
        #     case _:
        #         results = self.boolean_query(top)

        if top < 0:
            logger.warning("top is negative, returning all results")
            return results
        elif top == 0:
            logger.warning("top is zero, returning zero results")
            return []
        else:
            return results[:top]

    def display_results(self, results: list[tuple[int, str, float]]):
        """
        Display search results with PageRank scores.
        
        Args:
            results: List of (doc_id, url, tfidf_score) tuples.
        """
        print()
        print("=" * 70)
        print(f"Search Results for query: \"{self.query}\"")
        print("=" * 70)
        if len(results) == 0:
            print(f"There were no results for query: \"{self.query}\"")
        else:
            print(f"{'#':<3} {'URL':<45} {'TF-IDF':<10} {'PageRank':<10}")
            print("-" * 70)
            for i, (doc_id, url, tfidf_score) in enumerate(results, 1):
                pagerank = get_page_rank(doc_id)
                # Truncate URL if too long
                display_url = url if len(url) <= 45 else url[:42] + "..."
                print(f"{i:<3} {display_url:<45} {tfidf_score:<10.4f} {pagerank:<10.6f}")
        print("=" * 70)
