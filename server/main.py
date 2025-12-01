from fastapi import FastAPI, HTTPException

import utils.constants as const
from search.search_engine import SearchEngine
from search.query import Query, QueryType


app = FastAPI(title="Search Engine API")

# Initialize the search engine once, reusing the same index on every request.
search_engine = SearchEngine(const.INDEX_DIR_DEFAULT)


@app.get("/search", response_model=list[str])
def search(q: str, top: int = const.TOP_RESULTS_DEFAULT) -> list[str]:
    query_str = q.strip()
    if not query_str:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    # Set the query on the existing search engine and fetch results.
    search_engine.query = Query(query_str)
    results = search_engine.get_search_results(QueryType.boolean, top)
    return results


