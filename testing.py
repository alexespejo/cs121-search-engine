import utils.constants as const
from indexer.inverted_index import Posting, get_postings, get_document_count, get_url
from search.search_engine import SearchEngine

from time import perf_counter_ns
from math import log

if __name__ == "__main__":
    term = "help"
    with open("index/main_inverted_index.nidx", "rb") as f:        
        search_engine = SearchEngine("index")
        num_results = 5
        try:
            while True:
                # Prompt user indefinitely until Ctrl C
                search_engine.accept_query("Enter Query: ")
                term_postings: dict[str, list[Posting]] = {}
                for term in search_engine.query.parsed_query:
                    before = perf_counter_ns()

                    postings = get_postings(f, term)
                    if not postings:
                        pass
                    term_postings[term] = postings
                    
                    time_diff_ns = perf_counter_ns() - before
                    time_diff_ms: float = time_diff_ns / const.NS_TO_MS
                    print(f"\nposting search time \"{term}\": {time_diff_ms:.2f}ms")

                doc_id_sets = []
                for term, postings in term_postings.items():
                    before = perf_counter_ns()

                    doc_id_set = {posting.doc_id for posting in postings}
                    doc_id_sets.append(doc_id_set)
                    
                    time_diff_ns = perf_counter_ns() - before
                    time_diff_ms: float = time_diff_ns / const.NS_TO_MS
                    print(f"\ndoc_id search time \"{term}\": {time_diff_ms:.2f}ms")

                before = perf_counter_ns()
                common_doc_ids = set.intersection(*doc_id_sets)
                time_diff_ns = perf_counter_ns() - before
                time_diff_ms: float = time_diff_ns / const.NS_TO_MS
                print(f"\nintersection time: {time_diff_ms:.2f}ms")

                before = perf_counter_ns()
                total_docs = get_document_count(search_engine.index_fptr)
                time_diff_ns = perf_counter_ns() - before
                time_diff_ms: float = time_diff_ns / const.NS_TO_MS
                print(f"\ntotal_docs time: {time_diff_ms:.2f}ms")
            
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
                before = perf_counter_ns()

                for doc_id in common_doc_ids:
                    score = 0.0
                    for term, doc_tf_map in term_postings_by_doc.items():
                        tf = doc_tf_map.get(doc_id, 0)  # O(1)
                        score += tf * term_idf[term]
                    doc_scores[doc_id] = score

                time_diff_ms = (perf_counter_ns() - before) / 1_000_000
                print(f"\nscoring doc_ids time: {time_diff_ms:.2f}ms")
                
                sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:5]
                
                results: list[tuple[str, float]] = []
                for doc_id, score in sorted_docs:
                    before = perf_counter_ns()
                    url = get_url(search_engine.index_fptr, doc_id)
                    time_diff_ns = perf_counter_ns() - before
                    time_diff_ms: float = time_diff_ns / const.NS_TO_MS
                    print(f"\nget_url time: {time_diff_ms:.2f}ms")
                    if url:
                        results.append((url, score))

                results: list[tuple[str, float]] = []
                for doc_id, score in sorted_docs:
                    url = get_url(search_engine.index_fptr, doc_id)
                    if url:
                        results.append((url, score))
                print(results)                
        except EOFError:
            print("\nEOF found, exiting...")
            exit(0)