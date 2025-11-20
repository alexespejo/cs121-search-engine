import json
import mimetypes
import logging
import gc
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Union
from urllib.parse import urlparse

import utils.constants as const
from utils.text_processing import extract_fields_html, tokenize_fields
from utils.file_io import is_valid_dir, is_valid_file, get_dir_size, rm_dir, FilePointer
from indexer.inverted_index import InvertedIndex, open_mmap, load_index_from_mmap

logger = logging.getLogger(__name__)

def get_file_list(data_dir_str: str) -> list[Path]:
    """Return list of all JSON files in a directory."""
    data_path: Path = Path(data_dir_str)
    if (not is_valid_dir(data_path)):
        error_message: str = f"Data directory {data_path} is invalid"
        logger.error(error_message)
        raise FileNotFoundError(error_message)
    file_list = sorted([p for p in data_path.rglob("*.json") if p.is_file()])
    return file_list

def save_file_list(file_list: list[Path]):
    with open("file_list.pkl", "wb") as f:
        pickle.dump(file_list, f)

def load_file_list(file_list_str: str) -> list[Path]:
    file_list_path = Path(file_list_str)
    if (not is_valid_file(file_list_path)):
        error_message: str = f"File list path: {file_list_path} is invalid"
        logger.error(error_message)
        raise FileNotFoundError(error_message)
    
    with open(file_list_path, "rb") as f:
        file_list: list[Path] = pickle.load(f)
        return file_list
    
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
        self.file_ptr = FilePointer()
        
        self.debug = False
        self.next_doc_id: int = 0
        self.batch_size: int = batch_size

        file_list_path = Path(const.FILE_LIST_FILENAME)
        if is_valid_file(file_list_path):
            self.file_list: list[Path] = load_file_list(const.FILE_LIST_FILENAME)
        else:
            self.file_list: list[Path] = get_file_list(str(self.data_path))
            save_file_list(self.file_list)

        logger.warning("File list is empty")

        logger.info("Variables initialized")

    def run(self) -> None:
        logger.info("Running Indexer...")
        if (self.batch_size <= 0):
            error_message: str = f"batch_size cannot be <= 0: {self.batch_size}"
            logger.error(error_message)
            raise ValueError(error_message)
        logger.info(f"Processing in batches of {self.batch_size} JSON files each")
        self.process_files_in_batches(self.batch_size)
        self.merge_indexes()
        rm_dir(self.tmp_indexes_path)
        logger.info("Indexer done")

    def delete_index(self) -> None:
        """
        Delete current index on file.
        """
        if not is_valid_dir(self.index_path):
            error_message: str = f"data directory {self.data_path} is invalid."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        logger.info("Deleting current index...")
        rm_dir(self.index_path, only_contents=True)
        rm_dir(self.tmp_indexes_path, only_contents=True)
        logger.info("Index deleted")

    def reset_index(self) -> None:
        del self.inv_index
        gc.collect()
        self.inv_index = InvertedIndex()

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
        if reuse_doc_id:
            doc_id = next((key for key, value in self.inv_index.doc_id_to_url.items() if value == url), None)
            if doc_id is None:
                doc_id = self.next_doc_id
                self.next_doc_id += 1
                self.inv_index.doc_id_to_url[doc_id] = url # map doc_id to url

        else:
            doc_id = self.next_doc_id
            self.next_doc_id += 1
            self.inv_index.doc_id_to_url[doc_id] = url # map doc_id to url
        
        try:
            fields = {}
            fields: dict[str, Union[str, List[str], List[tuple]]] = extract_fields_html(content)
        except Exception as e:
            logger.warning(f"Failed to extract fields from {url}: {e}")
            return

        # tokenize the fields
        try:
            term_frequencies, word_total = tokenize_fields(fields)
        except Exception as e:
            logger.warning(f"Failed to tokenize {url}: {e}")
            return
        # add the term frequencies to the index
        for term, frequency in term_frequencies.items():
            self.inv_index.add_entry(term, doc_id, float(frequency) / float(word_total))

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
                return
            
            should_skip, reason = self.is_file_skippable(url)
            if should_skip:
                logger.debug(f"Skipping URL (reason: {reason}): {url}")
                logger.debug(f"Skipping file: {file_path}")
                return

            self.index_document(url, content, reuse_doc_id=reuse_doc_id)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
    
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
                self.inv_index.save_index(Path(f"{self.tmp_indexes_path}/inverted_index_{str(self.file_ptr.batch_counter)}.idx"))
                self.file_ptr.save_pointer()
                
                # CLEARS INDEX FROM RAM
                self.reset_index()

                dirty_count = 0
                self.file_ptr.batch_counter += 1

        logger.info("Final save after all files processed...")
        self.inv_index.save_index(Path(f"{self.tmp_indexes_path}/inverted_index_{str(self.file_ptr.batch_counter)}.idx"))

        logger.info("All files processed successfully.")

    def merge_indexes(self):
        if not is_valid_dir(self.index_path):
            error_message: str = f"index directory {self.index_path} is invalid."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        tmp_index_files = sorted(self.tmp_indexes_path.rglob("*.idx"))

        if not tmp_index_files:
            logger.warning("No index files found to merge.")
            return

        temp_count = 0

        while len(tmp_index_files) > 1:
            seg_a = tmp_index_files.pop(0)
            seg_b = tmp_index_files.pop(0)

            merged_index: InvertedIndex = InvertedIndex()

            for segment_file in [seg_a, seg_b]:
                segment_index = load_index_from_mmap(segment_file)
                for term, postings in segment_index.index_dict.items():
                    merged_index.index_dict[term].extend(postings)
                merged_index.doc_id_to_url.update(segment_index.doc_id_to_url)

                del segment_index
                gc.collect()


            for term, postings in merged_index.index_dict.items():
                postings.sort(key=lambda x: x[0])

            merged_file = self.tmp_indexes_path / f"tmp_merged_{temp_count}.idx"
            merged_index.save_index(merged_file)
            
            del merged_index
            gc.collect()

            tmp_index_files.append(merged_file)
            tmp_index_files = sorted(tmp_index_files)
            temp_count += 1

        final_file = tmp_index_files[0]
        final_index = load_index_from_mmap(final_file)

        final_index_file = self.index_path / "main_inverted_index.idx"
        final_index.save_index(final_index_file)
        logger.info(f"Merged index saved to {final_index_file}")

    def display_report(self, report_output_file: str | None = None) -> None:
        """
        Generate a report with analytics about the index.

        Args:
            report_output_file (str | None): Path to save the report. 
                                            If None, prints to stdout.
        """
        if not is_valid_dir(self.index_path):
            error_message = f"index directory invalid / missing {self.index_path}."
            logger.error(error_message)
            raise IOError(error_message)

        logger.info("Displaying report...")
        analytics = self.inv_index.get_analytics()
        index_size_kb = get_dir_size(self.index_path, unit="KB")

        # Helper for aligned lines
        def line(label: str, value: str | int | float) -> str:
            return f"{label.ljust(40)} | {value}"

        report_lines = [
            "=" * 70,
            "INDEX ANALYTICS REPORT",
            "=" * 70,
            "",
            line("Metric", "Value"),
            "-" * 70,
            line("Number of indexed documents", analytics["num_documents"]),
            line("Number of unique tokens", analytics["num_unique_tokens"]),
            line("Total postings", analytics["total_postings"]),
            line("Total token occurrences", analytics["total_token_occurrences"]),
            line("Average postings per token", f"{analytics['avg_postings_per_token']:.2f}"),
            line("Median postings per token", analytics["median_postings_per_token"]),
            line("Max postings per token", analytics["max_postings_per_token"]),
            line("Min postings per token", analytics["min_postings_per_token"]),
            line("Total size of index on disk (KB)", f"{index_size_kb:.2f}"),
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
