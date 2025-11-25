import utils.constants as const
from utils.args import create_parser_indexer
from utils.log_setup import setup_logging
from indexer.indexer import Indexer

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
        logger.debug("Debug mode activated")
    else:
        index_dir = args.index_directory or const.INDEX_DIR_DEFAULT

    # Run indexer
    indexer = Indexer(data_dir, index_dir, args.batch_size)
    indexer.debug = args.debug
    if args.reset:
        indexer.delete_index()
    print("Starting indexing...")
    before = perf_counter_ns()
    indexer.run()
    time_diff_ns = perf_counter_ns() - before
    print("Indexing complete")

    hours = int(time_diff_ns // 3.6e12)
    minutes = int((time_diff_ns % 3.6e12) // 6e10)
    seconds = time_diff_ns % 6e10
    logger.info(f"indexing time: {hours}:{minutes}:{seconds}")
    print(f"indexing time: {hours}:{minutes}:{seconds}")
    
    indexer.display_report()
