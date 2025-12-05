from search.query import Query, QueryType
import utils.constants as const
from indexer.inverted_index import get_postings, get_document_count, load_doc_id_to_url
from indexer.PageRank import get_page_rank
from utils.text_processing import tokenize_url

from pathlib import Path
from logging import getLogger
from math import log
from collections import defaultdict
import bisect
import time

logger = getLogger(__name__)

class Score:
    def __init__(self):
        self.doc_id: int = 0
        self.url: str = ""
        self.scores = defaultdict(float)
    @property
    def total_score(self):
        total_score: float = 0.0
        for key, score in self.scores.items():
            total_score += score * const.SCORING_DICT[key]
        return total_score

class SearchEngine:
    def __init__(self, index_dir: str):
        self.query: Query
        self.index_fptr = open(Path(index_dir) / "main_inverted_index.nidx", "rb")
        self.doc_id_to_url = load_doc_id_to_url(self.index_fptr)

        # hack workaround, loads page_rank to RAM
        get_page_rank(0)
        
    def accept_query(self, input_message: str) -> None:
        query_str: str = input(input_message)
        self.query = Query(query_str)

    def minmax(self, x, mn, mx):
        return (x - mn) / (mx - mn) if mx > mn else 0.0


    def boolean_query(self, top: int) -> list[tuple[int, str, Score]]:

        start_total = time.time()

        if not self.query.parsed_query:
            return []

        # -----------------------------
        # Load postings for each term
        t0 = time.time()
        term_postings = {}
        for term in self.query.parsed_query:
            postings = get_postings(self.index_fptr, term)
            if not postings:
                return []
            term_postings[term] = postings
        t1 = time.time()
        print(f"[Timing] Loaded postings: {(t1 - t0) * 1000:.4f} ms")

        # -----------------------------
        # Intersect doc IDs
        t0 = time.time()
        common_doc_ids = set.intersection(
            *[{p.doc_id for p in postings} for postings in term_postings.values()]
        )
        t1 = time.time()
        print(f"[Timing] Intersected doc IDs: {(t1 - t0) * 1000:.4f} ms")
        if not common_doc_ids:
            return []

        # -----------------------------
        # Compute IDF
        t0 = time.time()
        total_docs = get_document_count(self.index_fptr)
        term_idf = {
            term: log(total_docs / len(postings))
            for term, postings in term_postings.items()
        }
        t1 = time.time()
        print(f"[Timing] Computed IDF: {(t1 - t0) * 1000:.4f} ms")

        # -----------------------------
        # Compute TF-IDF + store pagerank
        t0 = time.time()
        doc_scores = defaultdict(Score)
        for doc_id in common_doc_ids:
            doc_scores[doc_id].doc_id = doc_id
            doc_scores[doc_id].scores["pagerank"] = get_page_rank(doc_id)

            for term in self.query.parsed_query:
                postings = term_postings[term]
                idx = bisect.bisect_left(postings, doc_id)
                if idx < len(postings) and postings[idx].doc_id == doc_id:
                    tf = postings[idx].weighted_tf
                    doc_scores[doc_id].scores["tf-idf"] += tf * term_idf[term]
        t1 = time.time()
        print(f"[Timing] Computed TF-IDF & pagerank: {(t1 - t0) * 1000:.4f} ms")

        # -----------------------------
        # Normalization
        t0 = time.time()
        tfidf_vals = [s.scores["tf-idf"] for s in doc_scores.values()]
        pr_vals = [s.scores["pagerank"] for s in doc_scores.values()]

        tfidf_min, tfidf_max = min(tfidf_vals), max(tfidf_vals)
        pr_min, pr_max = min(pr_vals), max(pr_vals)

        for s in doc_scores.values():
            s.scores["tf-idf"] = self.minmax(s.scores["tf-idf"], tfidf_min, tfidf_max)
            s.scores["pagerank"] = self.minmax(s.scores["pagerank"], pr_min, pr_max)
        t1 = time.time()
        print(f"[Timing] Normalized scores: {(t1 - t0) * 1000:.4f} ms")

        # -----------------------------
        # URL boosting
        # t0 = time.time()

        # query_terms_set = set(self.query.parsed_query)

        # for doc_id, score_obj in doc_scores.items():
        #     url = self.doc_id_to_url.get(doc_id)
        #     if not url:
        #         continue

        #     url_tokens = set(tokenize_url(url))
        #     if query_terms_set & url_tokens:  # intersection check
        #         score_obj.scores["url"] += 1.0  # boost

        # t1 = time.time()
        # print(f"[Timing] URL boosting: {(t1 - t0) * 1000:.4f} ms")

        # -----------------------------
        # Final sort
        t0 = time.time()
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1].total_score,
            reverse=True
        )[:top]
        t1 = time.time()
        print(f"[Timing] Sorted docs: {(t1 - t0) * 1000:.4f} ms")

        # -----------------------------
        # Build final results
        t0 = time.time()
        results = []
        for doc_id, score in sorted_docs:
            url = self.doc_id_to_url[doc_id]
            if url:
                results.append((doc_id, url, score))
        t1 = time.time()
        print(f"[Timing] Built final results: {(t1 - t0) * 1000:.4f} ms")

        print(f"[Timing] Total boolean_query time: {(time.time() - start_total) * 1000:.4f} ms")
        return results



    def get_search_results(self, type: QueryType = QueryType.boolean, top: int = const.TOP_RESULTS_DEFAULT) -> list[tuple[int, str, Score]]:
        """
        Get search results with doc_id, url, and score.
        
        Returns:
            List of (doc_id, url, score) tuples.
        """
        match type:
            case QueryType.boolean:
                results = self.boolean_query(top)
            case _:
                results = self.boolean_query(top)

        if top < 0:
            logger.warning("top is negative, returning all results")
            return results
        elif top == 0:
            logger.warning("top is zero, returning zero results")
            return []
        else:
            return results[:top]

    def display_results(self, results: list[tuple[int, str, Score]]):
        print()
        print("=" * 70)
        print(f"Search Results for query: \"{self.query}\"")
        print("=" * 70)
        if not results:
            print(f"There were no results for query: \"{self.query}\"")
        else:
            print(f"{'#':<3} {'URL':<50} {'total':<10} {'TF-IDF':<10} {'PageRank':<10}")
            print("-" * 70)
            for i, (doc_id, url, score) in enumerate(results, 1):
                tfidf = score.scores.get('tf-idf', 0.0)
                pr = score.scores.get('pagerank', 0.0)
                print(f"{i:<3} {url:<50} {score.total_score:<10.4f} {tfidf:<10.4f} {pr:<10.4f}")
        print("=" * 70)

