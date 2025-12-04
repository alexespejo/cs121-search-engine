import utils.constants as const
from argparse import ArgumentParser

def create_parser_indexer() -> ArgumentParser:
    parser = ArgumentParser(description="Indexer tool")

    parser.add_argument(
        "-t", "--target-directory",
        type=str,
        default=const.DATA_DIR_DEFAULT,
        help="Directory containing input documents."
    )

    parser.add_argument(
        "-i", "--index-directory",
        type=str,
        default=const.INDEX_DIR_DEFAULT,
        help="Directory where the index will be stored."
    )

    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=const.BATCH_SIZE_DEFAULT,
        help="Number of documents to process before flushing to disk."
    )

    parser.add_argument(
        "-l", "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warn", "error"],
        help="Set log output level."
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode with debug paths and debug logging."
    )

    parser.add_argument(
        "-r", "--reset",
        action="store_true",
        help="Enable reset of index before program start."
    )

    return parser

def create_parser_search() -> ArgumentParser:
    parser = ArgumentParser(description="Search Engine")

    parser.add_argument(
        "-n", "--num-results",
        type=int,
        default=const.TOP_RESULTS_DEFAULT,
        help="Set how many of the top results are shown."
    )

    parser.add_argument(
        "-i", "--index-directory",
        type=str,
        default=const.INDEX_DIR_DEFAULT,
        help="Directory where the index is stored."
    )

    parser.add_argument(
        "-l", "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warn", "error"],
        help="Set log output level."
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode with debug paths and debug logging."
    )
    
    return parser


def create_parser_pagerank() -> ArgumentParser:
    parser = ArgumentParser(description="PageRank computation tool")

    parser.add_argument(
        "-t", "--target-directory",
        type=str,
        default=const.DATA_DIR_DEFAULT,
        help="Directory containing input documents."
    )

    parser.add_argument(
        "-i", "--index-directory",
        type=str,
        default=const.INDEX_DIR_DEFAULT,
        help="Directory where the index is stored and PageRank will be saved."
    )

    parser.add_argument(
        "-l", "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warn", "error"],
        help="Set log output level."
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode with debug paths and debug logging."
    )

    parser.add_argument(
        "--damping",
        type=float,
        default=0.85,
        help="Damping factor for PageRank (default: 0.85)."
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Maximum iterations for PageRank convergence (default: 100)."
    )

    parser.add_argument(
        "--no-save-graph",
        action="store_true",
        default=False,
        help="Don't save the link graph to disk."
    )

    return parser
