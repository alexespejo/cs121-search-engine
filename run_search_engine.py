import utils.constants as const
from utils.args import create_parser_search
from utils.log_setup import setup_logging
from search.search_engine import SearchEngine
from search.query import QueryType

from logging import getLogger
from time import perf_counter_ns
import sys

if __name__ == '__main__':
    # Parse args
    parser = create_parser_search()
    args = parser.parse_args()

    # Interpret args
    setup_logging(
        log_dir=const.LOG_DIR,
        level = const.LOG_LEVELS.get(args.log_level, const.LOG_LEVELS["info"] or 20)
    )
    logger = getLogger(__name__)
    if args.debug:
        logger.setLevel(const.LOG_LEVELS["debug"])
    index_dir: str = args.index_directory or const.INDEX_DIR_DEFAULT
    num_results: int = args.num_results or const.TOP_RESULTS_DEFAULT
    if num_results < 0:
        raise ValueError(f"Invalid Argument: {args.num_results}")
    
    search_engine: SearchEngine = SearchEngine(index_dir)
    search_times: dict[str, float] = {}

    # Run search engine
    try:
        while True:
            # Prompt user indefinitely until Ctrl C
            search_engine.accept_query("Enter Query: ")
            before = perf_counter_ns()

            search_results: list[str] = search_engine.get_search_results(QueryType.boolean, num_results)
            search_engine.display_results(search_results)
            
            time_diff_ns = perf_counter_ns() - before
            time_diff_ms: float = time_diff_ns / const.NS_TO_MS
            print(f"\nsearch time: {time_diff_ms:.2f}ms")
            search_times[search_engine.query.original_str] = time_diff_ms
    except EOFError:
        print("\nEOF found, exiting...")
        for query, time in search_times.items():
            if time > 300:
                print(f"Query Timed Out: \"{query}\"", file=sys.stderr)
            else:
                print(f"Good job!: \"{query}\"", file=sys.stderr)

        exit(0)