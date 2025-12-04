import utils.constants as const
from utils.text_processing import extract_fields_html, tokenize_fields, calculate_postings
from utils.file_io import FilePointer, is_valid_dir, is_valid_file, get_dir_size, rm_dir, save_file_list, load_file_list, get_json_file_list
from indexer.inverted_index import InvertedIndex, load_index_full
from indexer.posting import Posting
from indexer.simhash import simhash, hamming

import json
import mimetypes
import gc
from pathlib import Path
from urllib.parse import urlparse, urlunparse, urljoin
from logging import getLogger

logger = getLogger(__name__)
    
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
        self.doc_fingerprints: dict[int, int] = {}
        self.file_ptr = FilePointer()
        
        self.debug = False
        self.next_doc_id: int = 0
        self.batch_size: int = batch_size

        file_list_path = Path(f"{const.FILE_LIST_FILENAME}.pkl")
        if is_valid_file(file_list_path):
            self.file_list: list[Path] = load_file_list(f"{const.FILE_LIST_FILENAME}.pkl")
        else:
            self.file_list: list[Path] = get_json_file_list(str(self.data_path))
            save_file_list(self.file_list)

        logger.info("Variables initialized")

    def run(self) -> None:
        logger.info("Running Indexer...")
        if (self.batch_size <= 0):
            error_message: str = f"batch_size cannot be <= 0: {self.batch_size}"
            logger.error(error_message)
            raise ValueError(error_message)
        logger.info(f"Processing in batches of {self.batch_size} JSON files each")
        self._process_files_in_batches(self.batch_size)
        self._merge_indexes()
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

    def _get_next_doc_id(self):
        doc_id = self.next_doc_id
        self.next_doc_id += 1
        return doc_id

    def _is_dupe(self, new_fp: int) -> int | None:
        for doc_id, fp in self.doc_fingerprints.items():
            if hamming(new_fp, fp) <= const.HAMMING_THRESHOLD:
                return doc_id
        return None

    def _normalize_url(self, base, link):
        abs_url = urljoin(base, link)
        parts = urlparse(abs_url)
        netloc = parts.netloc.lower()
        path = parts.path.rstrip("/")
        return urlunparse((parts.scheme.lower(), netloc, path, "", "", ""))

    def _index_document(self, url: str, content: str, reuse_doc_id: bool = False) -> None:
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

        url = self._normalize_url(url, url)

        fields = extract_fields_html(content)

        tokens = []
        zone_tokens = tokenize_fields(fields)
        for _, tok_list in zone_tokens.items():
            if tok_list and isinstance(tok_list[0], str):
                tokens.extend(tok_list)

        fp = simhash(tokens)
        dup_id = self._is_dupe(fp)
        if dup_id is not None:
            logger.info(f"Skipping {url}: near-duplicate of doc {dup_id}")
            return

        if reuse_doc_id:
            doc_id = next((key for key, value in self.inv_index.doc_id_to_url.items() if value == url), None)
            if doc_id is None:
                doc_id = self._get_next_doc_id()
        else:
            doc_id = self._get_next_doc_id()
        self.inv_index.doc_id_to_url[doc_id] = url

        postings = calculate_postings(doc_id, zone_tokens)

        for term, posting in postings.items():
            self.inv_index.add_posting(term, posting)

        self.doc_fingerprints[doc_id] = fp

    def _is_file_skippable(self, url: str) -> tuple[bool, str]:
        """
        Check if a URL should be skipped based on file extension or content type.
        
        Args:
            url: The URL to check
            
        Returns:
            tuple of (should_skip: bool, reason: str)
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

    def _process_file(self, file_path: Path, reuse_doc_id: bool = False) -> None:
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
            
            should_skip, reason = self._is_file_skippable(url)
            if should_skip:
                logger.debug(f"Skipping URL (reason: {reason}): {url}")
                logger.debug(f"Skipping file: {file_path}")
                return

            self._index_document(url, content, reuse_doc_id=reuse_doc_id)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
    
    def _process_files_in_batches(self, batch_size: int) -> None:
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
            error_message = "File list not found"
            logger.error(error_message)
            raise IOError(error_message)
        
        if self.file_ptr.exists_on_disk():
            self.file_ptr = self.file_ptr.load_pointer()

        file_list_len = len(self.file_list)
        logger.info(f"Starting batch processing from file {self.file_ptr.file_idx} / {file_list_len}...")

        dirty_count = 0
        while self.file_ptr.file_idx < file_list_len:
            logger.info(f"Processing file {self.file_ptr.file_idx} / {file_list_len}...")
            self._process_file(self.file_list[self.file_ptr.file_idx], reuse_doc_id=False)
            dirty_count += 1
            self.file_ptr.file_idx += 1

            if batch_size > 0 and dirty_count >= batch_size:
                self.inv_index.save(Path(f"{self.tmp_indexes_path}/inverted_index_{str(self.file_ptr.batch_counter)}.nidx"))
                self.file_ptr.save_pointer()
                
                # CLEARS INDEX FROM RAM
                self.reset_index()

                dirty_count = 0
                self.file_ptr.batch_counter += 1
            logger.info(f"File {self.file_ptr.file_idx} / {file_list_len} processed")

        logger.info("Final save after all files processed...")
        self.inv_index.save(Path(f"{self.tmp_indexes_path}/inverted_index_{str(self.file_ptr.batch_counter)}.nidx"))

        logger.info("All files processed successfully")

    def _merge_indexes(self):
        if not is_valid_dir(self.index_path):
            error_message: str = f"index directory {self.index_path} is invalid."
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        tmp_index_files = sorted(self.tmp_indexes_path.rglob("*.nidx"))

        if not tmp_index_files:
            logger.warning("No index files found to merge.")
            return

        temp_count = 0

        while len(tmp_index_files) > 1:
            seg_a = tmp_index_files.pop(0)
            seg_b = tmp_index_files.pop(0)

            merged_index: InvertedIndex = InvertedIndex()

            for segment_file in [seg_a, seg_b]:
                with open(segment_file, "rb") as f:
                    segment_index = load_index_full(f)
                    for term, postings in segment_index.index_dict.items():
                        merged_index.index_dict[term].extend(postings)
                    merged_index.doc_id_to_url.update(segment_index.doc_id_to_url)
                del segment_index
                gc.collect()


            for term, postings in merged_index.index_dict.items():
                postings.sort()

            merged_file = self.tmp_indexes_path / f"tmp_merged_{temp_count}.nidx"
            merged_index.save(merged_file)
            
            del merged_index
            gc.collect()

            tmp_index_files.append(merged_file)
            tmp_index_files = sorted(tmp_index_files)
            temp_count += 1

        final_file = tmp_index_files[0]
        with open(final_file, "rb") as f:
            final_index = load_index_full(f)

        final_index_file = self.index_path / f"main_{const.INDEX_FILENAME}.nidx"
        term_offsets = final_index.save(final_index_file)
        logger.info(f"Merged index saved to {final_index_file}")
        with open("term_offsets.dat", "w") as f:
            for term, offset in term_offsets.items():
                f.write(f"{term} {offset}\n")

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
        with open(self.index_path / f"main_{const.INDEX_FILENAME}.nidx", "rb") as f:
            self.inv_index = load_index_full(f)
        analytics = self.inv_index.get_analytics()
        index_size_kb = get_dir_size(self.index_path, unit="KB")
        index_size_mb = get_dir_size(self.index_path, unit="MB")
        index_size_gb = get_dir_size(self.index_path, unit="GB")

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
            line("Average postings per token", f"{analytics['avg_postings_per_token']:.2f}"),
            line("Median postings per token", analytics["median_postings_per_token"]),
            line("Max postings per token", analytics["max_postings_per_token"]),
            line("Min postings per token", analytics["min_postings_per_token"]),
            line("Total size of index on disk KB | MB | GB", f"{index_size_kb:.2f} | {index_size_mb:.2f} | {index_size_gb:.2f}"),
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
