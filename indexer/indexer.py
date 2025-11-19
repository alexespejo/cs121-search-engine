import json
import mimetypes
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from collections import defaultdict
from urllib.parse import urlparse

import utils.constants as const
from utils.text_processing import extract_fields, tokenize_fields
from utils.file_io import is_valid_dir, is_valid_file, get_dir_size, rm_dir
from inverted_index import InvertedIndex

logger = logging.getLogger(__name__)

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
            total_docs (int): Total number of processed documents.
            skipped_urls (int): Number of skipped URLs due to errors or invalid format.
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
        self.tmp_indexes_path = Path(const.TMP_INDEX_DIR_DEFAULT)
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
        
        self.next_doc_id: int = 0 
        self.total_docs: int = 0
        self.skipped_urls: int = 0
        self.batch_size: int = batch_size
        self.batch_counter = 0
        logger.info("Variables initialized")

    def run(self) -> None:
        logger.info("Running Indexer...")
        if (self.batch_size < 0):
            logger.info("Processing in batches of 1 directory each")
            self.process_batches(0)
        else:
            logger.info(f"Processing in batches of {self.batch_size} JSON files each")
            self.process_batches(self.batch_size)
        logger.info("Indexer done")

    def reset_index(self) -> None:
        """
        Delete current index on file.
        """
        if not is_valid_dir(self.data_path):
            error_message: str = f"data directory {self.data_path} is invalid."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        logger.info("Deleting current index...")
        rm_dir(self.index_path, only_contents=True)
        logger.info("Index deleted")
        
    def process_document(self, url: str, content: str, assign_new_doc_id: bool = False) -> int:
        """
        Process a document and add it to the index.
        
        Args:
            url: The document URL
            content: The document content (HTML)
            assign_new_doc_id: If True, always assign a new doc_id regardless of URL.
                              If False, reuse doc_id for duplicate URLs.
        
        Returns:
            The doc_id assigned to this document
        """
        if assign_new_doc_id or url not in self.url_to_doc_id:
            doc_id = self.next_doc_id
            self.next_doc_id += 1
            self.url_to_doc_id[url] = doc_id # map url to doc_id
            self.doc_id_to_url[doc_id] = url # map doc_id to url
        else:
            doc_id = self.url_to_doc_id[url]
        
        try:
            fields: dict[str, Union[str, List[str], List[tuple]]] = extract_fields(content)
        except Exception as e:
            logger.warning(f"Failed to extract fields from {url}: {e}")
            return doc_id

        # tokenize the fields
        try:
            term_frequencies = tokenize_fields(fields)
        except Exception as e:
            logger.warning(f"Failed to tokenize {url}: {e}")
            return doc_id
        
        # add the term frequencies to the index
        for term, frequency in term_frequencies.items():
            self.inv_index.addEntry(term, doc_id, frequency)
        
        return doc_id

    def is_url_skippable(self, url: str) -> Tuple[bool, str]:
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

    def process_json_file(self, file_path: Path, assign_new_doc_id: bool = False) -> Optional[int]:
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
                return None
            
            should_skip, reason = self.is_url_skippable(url)
            if should_skip:
                self.skipped_urls += 1
                logger.debug(f"Skipping URL (reason: {reason}): {url}")
                logger.debug(f"Skipping file: {file_path}")
                return None

            doc_id = self.process_document(url, content, assign_new_doc_id=assign_new_doc_id)
            self.total_docs += 1
            return doc_id
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return None
    
    def process_directory(self, directory_path: str) -> None:
        directory = Path(directory_path)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        json_files = list(directory.rglob('*.json'))
        logger.debug(f"Found {len(json_files)} JSON files in {directory_path}")
        
        for i, json_file in enumerate(json_files, 1):
            if i % 100 == 0:
                logger.debug(f"Processing file {i}/{len(json_files)}...")
            self.process_json_file(json_file)
        
        logger.info(f"Processed {self.total_docs} documents")
    
    def process_folder_batch(self, folder_path: Path) -> int:
        """
        Process a single folder (batch) containing JSON files.
        Files are processed in sorted order to ensure consistent doc_id assignment.
        
        Args:
            folder_path: Path to the folder containing JSON files
        
        Returns:
            Number of documents processed in this batch
        """
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError(f"Folder does not exist or is not a directory: {folder_path}")
        
        # Get all JSON files in the folder and sort them for consistent ordering
        json_files = folder_path.glob('*.json')
        
        if not json_files:
            logger.warning(f"No JSON files found in {folder_path}")
            return 0
        
        logger.info(f"Processing batch: {folder_path.name}")
        
        docs_before = self.total_docs
        doc_id_before = self.next_doc_id
        
        for i, json_file in enumerate(json_files, 1):
            # Print folder and file being processed
            # logger.debug(f"  [{i}/{len(json_files)}] Folder: {folder_path.name} | File: {json_file.name}")
            # Assign new doc_id for each file (sequential by order)
            self.process_json_file(json_file, assign_new_doc_id=True)
        
        docs_processed = self.total_docs - docs_before
        logger.info(f"  Batch complete: {docs_processed} documents processed (doc_ids {doc_id_before} to {self.next_doc_id - 1})")
        
        return docs_processed
    
    def process_batches(self, batch_size: int) -> None:
        """
        Process multiple folders as batches. Each folder is a batch.
        After each batch, the index is saved to disk.
        doc_ids continue sequentially across batches.
        
        Args:
            batch_size: how many documents to process before saving to disk.
        """
        if (not is_valid_dir(self.data_path)):
            error_message: str = f"data directory {self.data_path} is invalid."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        # Get all subdirectories (folders that represent batches)
        # Process folders in the order they appear in the directory
        # Note: iterdir() order is filesystem-dependent and not guaranteed
        folders = [f for f in self.data_path.iterdir() if f.is_dir()]
        
        if not folders:
            error_message = f"data directory {self.data_path} does not contain any directories."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        logger.info(f"Found {len(folders)} batches to process")
        logger.info(f"Processing order:")
        for i, folder in enumerate(folders, 1):
            logger.info(f"  {i}. {folder.name}")
        
        # Try to load existing index if it exists
        if (self.index_path / 'inverted_index.pkl').exists():
            logger.info(f"Loading existing index from {self.index_path}...")
            self.inv_index.load_index(self.index_path)
            # Calculate next_doc_id: max doc_id + 1, or 0 if empty
            if self.doc_id_to_url:
                self.next_doc_id = max(self.doc_id_to_url.keys()) + 1
            else:
                self.next_doc_id = 0
            
            self.total_docs = len(self.doc_id_to_url)
            
            logger.info(f"Index loaded from {self.index_path}")
            logger.info(f"  Documents: {self.total_docs}")
            logger.info(f"  Next doc_id: {self.next_doc_id}")

            logger.info(f"Resuming from doc_id {self.next_doc_id}")
        else:
            logger.info("No existing index found. Starting fresh.")
        
        # Process each folder as a batch
        for batch_num, folder in enumerate(folders, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing Batch {batch_num}/{len(folders)}: {folder.name}")
            logger.info(f"{'='*70}")
            
            try:
                docs_processed = self.process_folder_batch(folder)
                
                # Save index after each batch
                logger.info(f"\nSaving index after batch {batch_num}...")
                self.inv_index.save_index(self.index_path, self.doc_id_to_url, self.url_to_doc_id)
                
                # Print inverted index to file after each batch
                logger.info(f"Saving inverted index for batch {batch_num}...")
                self.save_tmp_index()
                
                # Print batch summary
                analytics = self.get_analytics()
                logger.info(f"Batch {batch_num} summary:")
                logger.info(f"  Documents in batch: {docs_processed}")
                logger.info(f"  Total documents: {analytics['num_documents']}")
                logger.info(f"  Total unique tokens: {analytics['num_unique_tokens']}")
                
            except Exception as e:
                logger.error(f"failed to process batch {folder.name}: {e}")
                logger.info(f"Index saved up to batch {batch_num - 1}")
                raise
        
        logger.info(f"\n{'='*70}")
        logger.info("All batches processed successfully!")
        logger.info(f"{'='*70}")
        
    def get_analytics(self) -> Dict[str, int | float]:
        unique_tokens = len(self.inv_index.index_dict)
        total_documents = len(self.doc_id_to_url)
        
        total_postings = sum(len(postings) for postings in self.inv_index.index_dict.values())
        
        return {
            'num_documents': total_documents,
            'num_unique_tokens': unique_tokens,
            'total_postings': total_postings,
            'avg_postings_per_token': total_postings / unique_tokens if unique_tokens > 0 else 0,
            'skipped_urls': self.skipped_urls
        }

    def save_tmp_index(self) -> None:
        """Print the inverted index to a text file."""        
        file_path: Path = self.tmp_indexes_path / f"tmp_index_{self.batch_counter}.txt"
        
        self.inv_index.display(file_path.name)

        logger.info(f"Inverted index saved to: {file_path}")

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
            f"{'Number of skipped URLs'.ljust(40)} | {analytics['skipped_urls']}",
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
