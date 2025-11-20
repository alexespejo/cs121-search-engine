import utils.constants as const
from utils.args import create_parser_indexer
from utils.log_setup import setup_logging
from indexer.indexer import Indexer, get_file_list, load_file_list, save_file_list
from utils.file_io import is_valid_file

from pathlib import Path
from logging import getLogger
from time import perf_counter_ns

if __name__ == '__main__':
    # Parse args
    parser = create_parser_indexer()
    args = parser.parse_args()

    # Interpret args
    setup_logging(
        log_dir = const.LOG_DIR,
        level = const.LOG_LEVELS.get(args.log_level, const.LOG_LEVELS["info"] or 20)
    )
    logger = getLogger(__name__)
    data_dir = args.target_directory or const.DATA_DIR_DEFAULT
    if args.debug:
        index_dir = const.DEBUG_INDEX_DIR_DEFAULT
        logger.setLevel(const.LOG_LEVELS["debug"])
        logger.debug(f"Debug mode activated")
    else:
        index_dir = args.index_directory or const.INDEX_DIR_DEFAULT

    # Run indexer
    indexer = Indexer(data_dir, index_dir, args.batch_size)
    indexer.debug = args.debug
    if not args.keep:
        indexer.delete_index()

    before = perf_counter_ns()
    
    indexer.run()

    time_diff_ns = perf_counter_ns() - before
    time_diff_ms: float = time_diff_ns / const.NS_TO_MS
    logger.info(f"TIME TO COMPLETE INDEXING: {time_diff_ms:.2f}ms")

    # indexer.split_index_by_letter() # DEPRECATED
    indexer.display_report()
