from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import utils.constants as const
from search.search_engine import SearchEngine
from search.query import Query, QueryType
from time import perf_counter_ns


app = FastAPI(title="Search Engine API")

# Allow the frontend dev server to call this API from another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/search")
def search(q: str, top: int = const.TOP_RESULTS_DEFAULT) -> Dict[str, Any]:
    """
    HTTP search endpoint.

    - **q**: query string
    - **top**: max number of results to return (like `--num-results` in `run_search_engine.py`)

    Returns a dictionary payload containing:
    - query: the original query string
    - results: list of result URLs (same as printed by `run_search_engine.py`)
    - elapsed_ms: time taken to execute the search in milliseconds
    - timed_out: whether the query exceeded 300 ms (same threshold used in `run_search_engine.py`)
    - message: "Good job!" or "Query Timed Out" based on elapsed time
    """
    query_str = q.strip()
    if not query_str:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    if top < 0:
        raise HTTPException(status_code=400, detail="Parameter 'top' must be non-negative")

    # Create a fresh SearchEngine per request to avoid shared mutable state.
    search_engine = SearchEngine(const.INDEX_DIR_DEFAULT)
    try:
        search_engine.query = Query(query_str)

        before = perf_counter_ns()
        results: list[str] = search_engine.get_search_results(QueryType.boolean, top)
        time_diff_ns = perf_counter_ns() - before
    finally:
        # Close the underlying index file handle if present.
        if hasattr(search_engine, "index_fptr") and search_engine.index_fptr:
            search_engine.index_fptr.close()

    time_diff_ms: float = time_diff_ns / const.NS_TO_MS
    timed_out = time_diff_ms > 300.0

    return {
        "query": query_str,
        "results": results,
        "elapsed_ms": time_diff_ms,
        "timed_out": timed_out,
        "message": "Query Timed Out" if timed_out else "Good job!",
    }


