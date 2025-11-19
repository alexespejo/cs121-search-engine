from argparse import ArgumentParser

def create_parser_indexer() -> ArgumentParser:
    parser = ArgumentParser(description="Indexer tool")

    parser.add_argument(
        "-t", "--target-directory",
        type=str,
        default=None,
        help="Directory containing input documents."
    )

    parser.add_argument(
        "-i", "--index-directory",
        type=str,
        default=None,
        help="Directory where the index will be stored."
    )

    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=100,
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
        default=5,
        help="Set how many of the top results are shown."
    )

    parser.add_argument(
        "-i", "--index-directory",
        type=str,
        default=None,
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
        help="Enable debug mode with debug paths and debug logging."
    )
    
    return parser
