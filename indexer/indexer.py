import json
import mimetypes
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict
from urllib.parse import urlparse
from dataclasses import dataclass

import utils.constants as const
from utils.text_processing import extract_fields_html, tokenize_fields
from utils.file_io import is_valid_dir, is_valid_file, get_dir_size, rm_dir
from indexer.inverted_index import InvertedIndex

logger = logging.getLogger(__name__)

class FilePointer:
    def __init__(self, file_idx: int = 0, batch_counter: int = 0):
        self.file_idx: int = file_idx
        self.batch_counter: int = batch_counter

    def exists_on_disk(self) -> bool:
        path: Path = const.TMP_DIR / Path("cursor.pkl")
        return path.exists()
    
    def save_pointer(self) -> None:
        path: Path = const.TMP_DIR / Path("cursor.pkl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load_pointer(cls) -> "FilePointer":
        """Load the pointer from disk. Returns a FilePointer instance."""
        path: Path = const.TMP_DIR / Path("cursor.pkl")
        if not path.exists():
            raise FileNotFoundError(f"No pointer file found at {path}")
        with open(path, "rb") as f:
            obj = pickle.load(f)
        if not isinstance(obj, cls):
            raise TypeError(f"Expected a FilePointer object, got {type(obj)}")
        return obj
    
class Indexer:
    def __init__(self, data_dir_str: str = const.DATA_DIR_DEFAULT, index_dir_str: str = const.INDEX_DIR_DEFAULT, batch_size: int = 0):
        """
        Initialize the Indexer with the data and index directories.

        Args:
            data_dir_str (str, optional): Path to the directory containing input documents.
                Defaults to `const.DATA_DIR_DEFAULT`. Must exist, otherwise a FileNotFoundError
                is raised.
            index_dir_str (str, optional): Path to the directory where the index will be stored.
                Defaults to `const.INDEX_DIR_DEFAULT`. Will be created if it does not exist.
                Raises IOError if creation or validation fails.

        Raises:
            FileNotFoundError: If the provided data directory does not exist or is invalid.
            IOError: If the index directory cannot be created or validated.

        Attributes:
            data_path (Path): Path object for the data directory.
            index_path (Path): Path object for the index directory.
            inv_index (InvertedIndex): Empty inverted index instance.
            doc_id_to_url (Dict[int, str]): Mapping from document IDs to URLs.
            url_to_doc_id (Dict[str, int]): Mapping from URLs to document IDs.
            next_doc_id (int): Counter for assigning new document IDs.
            file_ptr (FilePointer): Default FilePointer instance (0, 0)
        """
        logger.info("Verifying data directory...")
        self.data_path: Path = Path(data_dir_str)
        if (not is_valid_dir(self.data_path)):
            error_message: str = f"Data directory {self.data_path} is invalid"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        logger.info("Data directory verified")

        logger.info("Creating index directory...")
        self.index_path: Path = Path(index_dir_str)
        self.index_path.mkdir(exist_ok=True, parents=True)
        if (not is_valid_dir(self.index_path)):
            error_message: str = f"There was a problem creating index directory \"{self.index_path}\""
            logger.error(error_message)
            raise IOError(error_message)
        logger.info("Index directory created")
        
        logger.info("Creating temporary indexes directory...")
        self.tmp_indexes_path = Path(const.TMP_DIR)
        self.tmp_indexes_path.mkdir(parents=True, exist_ok=True)
        if (not is_valid_dir(self.tmp_indexes_path)):
            error_message: str = f"problem creating tmp_indexes directory \"{self.tmp_indexes_path}\""
            logger.error(error_message)
            raise IOError(error_message)
        logger.info("Temporary indexes directory created")

        logger.info("Initializing Indexer variables...")
        
        self.inv_index: InvertedIndex = InvertedIndex()
        self.doc_id_to_url: Dict[int, str] = {}
        self.url_to_doc_id: Dict[str, int] = {}
        self.file_ptr = FilePointer()
        
        self.debug = False
        self.next_doc_id: int = 0
        self.batch_size: int = batch_size
        self.file_ptr = FilePointer()

        self.file_list: list[Path] = self.load_file_list()

        logger.info("Variables initialized")

    def run(self) -> None:
        logger.info("Running Indexer...")
        if (self.batch_size <= 0):
            logger.info("Processing in batches of 1 directory each")
            self.process_files_in_batches(0)
        else:
            logger.info(f"Processing in batches of {self.batch_size} JSON files each")
            self.process_files_in_batches(self.batch_size)
        rm_dir(self.tmp_indexes_path)
        logger.info("Indexer done")

    def load_file_list(self) -> list[Path]:
        """Return list of all JSON files one level deep in data_dir."""
        file_list = []
        for subdir in self.data_path.iterdir():
            if subdir.is_dir():
                file_list.extend(sorted(subdir.glob("*.json")))
        return file_list

    def delete_index(self) -> None:
        """
        Delete current index on file.
        """
        if not is_valid_dir(self.data_path):
            error_message: str = f"data directory {self.data_path} is invalid."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        logger.info("Deleting current index...")
        rm_dir(self.index_path, only_contents=True)
        rm_dir(self.tmp_indexes_path)
        logger.info("Index deleted")

    def reset_index(self) -> None:
        self.inv_index = InvertedIndex()
        self.doc_id_to_url = {}
        self.url_to_doc_id = {}

    def index_document(self, url: str, content: str, reuse_doc_id: bool = False) -> None:
        """
        Process a document and add it to the index.
        
        Args:
            url: The document URL
            content: The document content (HTML)
            reuse_doc_id: If True, reuse doc_id for duplicate URLs.
                          If False, always assign a new doc_id regardless of URL.
        
        Returns:
            None
        """
        if not reuse_doc_id or url not in self.url_to_doc_id:
            doc_id = self.next_doc_id
            self.next_doc_id += 1
            self.url_to_doc_id[url] = doc_id # map url to doc_id
            self.doc_id_to_url[doc_id] = url # map doc_id to url
        else:
            doc_id = self.url_to_doc_id[url]
        
        try:
            fields = {}
            fields: dict[str, Union[str, List[str], List[tuple]]] = extract_fields_html(content)
        except Exception as e:
            logger.warning(f"Failed to extract fields from {url}: {e}")
            return

        # tokenize the fields
        try:
            term_frequencies = tokenize_fields(fields)
        except Exception as e:
            logger.warning(f"Failed to tokenize {url}: {e}")
            return
        # add the term frequencies to the index
        for term, frequency in term_frequencies.items():
            self.inv_index.addEntry(term, doc_id, frequency)

    def is_file_skippable(self, url: str) -> Tuple[bool, str]:
        """
        Check if a URL should be skipped based on file extension or content type.
        
        Args:
            url: The URL to check
            
        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            for ext in const.SKIP_EXTENSIONS:
                if path.endswith(ext):
                    return True, f"File extension {ext}"
                if ext in path:
                    return True, f"File extension {ext} in path"
            
            query = parsed.query.lower()
            if any(ext in query for ext in const.SKIP_EXTENSIONS):
                for ext in const.SKIP_EXTENSIONS:
                    if ext in query:
                        return True, f"File extension {ext} in query"
            
            # Use mimetypes to guess content type from URL
            guessed_type, _ = mimetypes.guess_type(url)
            if guessed_type and guessed_type in const.SKIP_MIME_TYPES:
                return True, f"MIME type {guessed_type}"
            
            return False, ""
            
        except Exception as e:
            return True, f"URL parsing error: {e}"

    def process_file(self, file_path: Path, reuse_doc_id: bool = False) -> None:
        """
        Process a single JSON file.
        
        Args:
            file_path: Path to the JSON file
            assign_new_doc_id: If True, always assign a new doc_id (for batch processing)
        
        Returns:
            The doc_id assigned, or None if processing failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            url = data.get('url', '')
            content = data.get('content', '')
            
            if '#' in url:
                url = url.split('#')[0]
            
            if not url or not content:
                logger.warning(f"Missing url or content in {file_path}")
            
            should_skip, reason = self.is_file_skippable(url)
            if should_skip:
                logger.debug(f"Skipping URL (reason: {reason}): {url}")
                logger.debug(f"Skipping file: {file_path}")

            self.index_document(url, content, reuse_doc_id=reuse_doc_id)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
    
    # @TODO
    def process_files_in_batches(self, batch_size: int) -> None:
        """
        Process JSON files one-by-one, saving the index and clearing RAM every `batch_size` files.
        
        Args:
            batch_size: Number of files to process before saving the index.
        """
        if not is_valid_dir(self.data_path):
            error_message = f"Data directory {self.data_path} is invalid"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        if not self.file_list:
            error_message = f"File list not found"
            logger.error(error_message)
            raise IOError(error_message)
        
        if self.file_ptr.exists_on_disk():
            self.file_ptr = self.file_ptr.load_pointer()

        file_list_len = len(self.file_list)
        logger.info(f"Starting batch processing from file {self.file_ptr.file_idx} / {file_list_len}...")

        dirty_count = 0
        while self.file_ptr.file_idx < file_list_len:
            self.process_file(self.file_list[self.file_ptr.file_idx], reuse_doc_id=False)
            dirty_count += 1
            self.file_ptr.file_idx += 1

            if batch_size > 0 and dirty_count >= batch_size:
                self.inv_index.save_index_pkl(self.file_ptr.batch_counter, self.index_path, self.doc_id_to_url, self.url_to_doc_id)
                self.file_ptr.save_pointer()
                if self.debug:
                    file_path: Path = self.tmp_indexes_path / f"tmp_index_{self.file_ptr.batch_counter}.txt"
                    self.inv_index.display(file_path)
                    logger.debug(f"Inverted index saved to: {file_path}")
                
                # CLEARS INDEX FROM RAM
                self.reset_index()

                dirty_count = 0
                self.file_ptr.batch_counter += 1

        logger.info("Final save after all files processed...")
        self.inv_index.save_index_pkl(self.file_ptr.batch_counter, self.index_path, self.doc_id_to_url, self.url_to_doc_id)

        logger.info("All files processed successfully.")
    
    def merge_indexes(self):
        pass

    # @TODO
    def get_analytics(self) -> Dict[str, int | float]:
        unique_tokens = len(self.inv_index.index_dict)
        total_documents = len(self.doc_id_to_url)
        
        total_postings = sum(len(postings) for postings in self.inv_index.index_dict.values())
        
        return {
            'num_documents': total_documents,
            'num_unique_tokens': unique_tokens,
            'total_postings': total_postings,
            'avg_postings_per_token': total_postings / unique_tokens if unique_tokens > 0 else 0,
        }        

    # @TODO
    def display_report(self, report_output_file: str | None = None) -> None:
        """
        Generate a report with analytics about the index.

        Args:
            output_file (str | None): Path to save the report. If None, prints to stdout.
        """
        if (not is_valid_dir(self.index_path)):
            error_message: str = f"index directory invalid / missing {self.index_path}."
            logger.error(error_message)
            raise IOError(error_message)
        logger.info("Displaying report...")
        analytics = self.get_analytics()
        index_size_kb = get_dir_size(self.index_path, unit="KB")

        # Format report
        report_lines = [
            "=" * 70,
            "INDEX ANALYTICS REPORT",
            "=" * 70,
            "",
            f"{'Metric'.ljust(40)} | Value",
            "-" * 70,
            f"{'Number of indexed documents'.ljust(40)} | {analytics['num_documents']}",
            f"{'Number of unique tokens'.ljust(40)} | {analytics['num_unique_tokens']}",
            f"{'Total size of index on disk (KB)'.ljust(40)} | {index_size_kb:.2f}",
            f"{'Average postings per token'.ljust(40)} | {analytics['avg_postings_per_token']:.2f}",
            "",
            "=" * 70,
        ]

        report_content = "\n".join(report_lines)

        if report_output_file:
            output_path = Path(report_output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Report saved to {report_output_file}")
        else:
            print("\n" + report_content)
            logger.info("Report printed to stdout")
        logger.info("Report displayed")
