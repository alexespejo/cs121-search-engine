"""
PageRank Runner Script

Computes PageRank scores for the document corpus based on the link structure.
Assumes the index has already been built.
"""

import utils.constants as const
from utils.args import create_parser_pagerank
from utils.log_setup import setup_logging
from indexer.PageRank import PageRank

from logging import getLogger
from time import perf_counter_ns

if __name__ == '__main__':
    # Parse args
    parser = create_parser_pagerank()
    args = parser.parse_args()

    # Setup logging
    setup_logging(
        log_dir=const.LOG_DIR,
        level=const.LOG_LEVELS.get(args.log_level, const.LOG_LEVELS["info"] or 20)
    )
    logger = getLogger(__name__)

    # Interpret args
    data_dir = args.target_directory or const.DATA_DIR_DEFAULT
    if args.debug:
        index_dir = const.DEBUG_INDEX_DIR_DEFAULT
        logger.setLevel(const.LOG_LEVELS["debug"])
        logger.debug("Debug mode activated")
    else:
        index_dir = args.index_directory or const.INDEX_DIR_DEFAULT

    print(f"Data directory: {data_dir}")
    print(f"Index directory: {index_dir}")
    print(f"Damping factor: {args.damping}")
    print(f"Max iterations: {args.max_iterations}")
    print()

    # Run PageRank
    print("Initializing PageRank...")
    pr = PageRank(data_dir_str=data_dir, index_dir_str=index_dir)

    print("Computing PageRank...")
    before = perf_counter_ns()
    pr.run(
        damping=args.damping,
        max_iterations=args.max_iterations,
        save_graph=not args.no_save_graph
    )
    time_diff_ns = perf_counter_ns() - before

    hours = int(time_diff_ns // 3.6e12)
    minutes = int((time_diff_ns % 3.6e12) // 6e10)
    seconds = (time_diff_ns % 6e10) / 1e9

    print("PageRank computation complete")
    logger.info(f"PageRank computation time: {hours}h {minutes}m {seconds:.2f}s")
    print(f"PageRank computation time: {hours}h {minutes}m {seconds:.2f}s")
    print()

    # Display report
    pr.display_report(top_n=20)

