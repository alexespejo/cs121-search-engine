import utils.constants as const
from utils.args import create_parser_indexer
from utils.log_setup import setup_logging
from indexer.indexer import Indexer

from logging import getLogger

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
    if (args.reset):
        indexer.delete_index()
    indexer.run()
    indexer.merge_indexes()
    indexer.display_report()
