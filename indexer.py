import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import pickle
from urllib.parse import urlparse
import mimetypes

from extract_fields import extract_fields
from tokenize import tokenize
from InvertedIndex import InvertedIndex


class Indexer:
    
    def __init__(self):
        self.index = InvertedIndex()
        self.doc_id_map: Dict[int, str] = {} # doc_id to url
        self.url_to_doc_id: Dict[str, int] = {} # url to doc_id
        self.next_doc_id = 0 # doc_ids will be assigned sequentially
        self.total_docs = 0
        self.skipped_urls = 0  # Track skipped URLs
        
        # Initialize mimetypes (ensures all common types are loaded)
        mimetypes.init()
        
        # Define file extensions to skip (non-HTML content)
        self.skip_extensions = {
            '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
            '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flv',
            '.exe', '.dll', '.bin', '.dmg', '.iso',
            '.css', '.js', '.json', '.xml', '.csv'
        }
        
        # Define MIME types to skip (non-HTML content types)
        self.skip_mime_types = {
            'text/plain', 'text/css', 'text/javascript', 'application/javascript',
            'application/json', 'application/xml', 'text/xml', 'text/csv',
            'application/pdf', 'application/zip', 'application/x-rar-compressed',
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/svg+xml',
            'video/mp4', 'video/mpeg', 'audio/mpeg', 'audio/wav',
            'application/octet-stream'
        }
    
    def should_skip_url(self, url: str) -> Tuple[bool, str]:
        """
        Check if a URL should be skipped based on file extension or content type.
        
        Args:
            url: The URL to check
            
        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        try:
            # Parse the URL
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Check if the path has a file extension we should skip
            for ext in self.skip_extensions:
                if path.endswith(ext):
                    return True, f"File extension {ext}"
                # Also check for extension in query parameters (e.g., ?file=something.txt)
                if ext in path:
                    return True, f"File extension {ext} in path"
            
            # Check if URL has query parameters that suggest non-HTML content
            query = parsed.query.lower()
            if any(ext in query for ext in self.skip_extensions):
                for ext in self.skip_extensions:
                    if ext in query:
                        return True, f"File extension {ext} in query"
            
            # Use mimetypes to guess content type from URL
            guessed_type, _ = mimetypes.guess_type(url)
            if guessed_type and guessed_type in self.skip_mime_types:
                return True, f"MIME type {guessed_type}"
            
            return False, ""
            
        except Exception as e:
            # If there's an error parsing the URL, skip it to be safe
            return True, f"URL parsing error: {e}"
        
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
            self.doc_id_map[doc_id] = url # map doc_id to url
        else:
            doc_id = self.url_to_doc_id[url]
        
        # extract the fields from the content
        try:
            fields = extract_fields(content)
        except Exception as e:
            print(f"Warning: Failed to extract fields from {url}: {e}")
            return doc_id
        
        # tokenize the fields
        try:
            term_frequencies = tokenize(fields)
        except Exception as e:
            print(f"Warning: Failed to tokenize {url}: {e}")
            return doc_id
        
        # add the term frequencies to the index
        for term, frequency in term_frequencies.items():
            self.index.addEntry(term, doc_id, frequency)
        
        return doc_id
    
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
                print(f"Warning: Missing url or content in {file_path}")
                return None
            
            # Check if URL should be skipped (e.g., .txt files, PDFs, images, etc.)
            should_skip, reason = self.should_skip_url(url)
            if should_skip:
                self.skipped_urls += 1
                print(f"Skipping URL (reason: {reason}): {url}")
                return None
            
            doc_id = self.process_document(url, content, assign_new_doc_id=assign_new_doc_id)
            self.total_docs += 1
            return doc_id
            
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON file {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error: Failed to process file {file_path}: {e}")
            return None
    
    def process_directory(self, directory_path: str) -> None:
        directory = Path(directory_path)
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        json_files = list(directory.rglob('*.json'))
        # print(f"Found {len(json_files)} JSON files in {directory_path}")
        
        for i, json_file in enumerate(json_files, 1):
            # if i % 100 == 0:
            #     print(f"Processing file {i}/{len(json_files)}...")
            self.process_json_file(json_file)
        
        print(f"Processed {self.total_docs} documents")
    
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
            print(f"No JSON files found in {folder_path}")
            return 0
        
        print(f"Processing batch: {folder_path.name}")
        
        docs_before = self.total_docs
        doc_id_before = self.next_doc_id
        
        for i, json_file in enumerate(json_files, 1):
            # Print folder and file being processed
            # print(f"  [{i}/{len(json_files)}] Folder: {folder_path.name} | File: {json_file.name}")
            # Assign new doc_id for each file (sequential by order)
            self.process_json_file(json_file, assign_new_doc_id=True)
        
        docs_processed = self.total_docs - docs_before
        print(f"  Batch complete: {docs_processed} documents processed (doc_ids {doc_id_before} to {self.next_doc_id - 1})")
        
        return docs_processed
    
    def process_batches(self, parent_directory: str, index_dir: str) -> None:
        """
        Process multiple folders as batches. Each folder is a batch.
        After each batch, the index is saved to disk.
        doc_ids continue sequentially across batches.
        
        Args:
            parent_directory: Path to the parent directory containing folder batches
            index_dir: Directory where the index is saved after each batch
        """
        parent_path = Path(parent_directory)
        if not parent_path.exists():
            raise ValueError(f"Parent directory does not exist: {parent_directory}")
        
        # Get all subdirectories (folders that represent batches)
        # Process folders in the order they appear in the directory
        # Note: iterdir() order is filesystem-dependent and not guaranteed
        folders = [f for f in parent_path.iterdir() if f.is_dir()]
        
        if not folders:
            print(f"No folders found in {parent_directory}")
            return
        
        print(f"Found {len(folders)} batches to process")
        print(f"Processing order:")
        for i, folder in enumerate(folders, 1):
            print(f"  {i}. {folder.name}")
        
        # Try to load existing index if it exists
        index_path = Path(index_dir)
        if (index_path / 'inverted_index.pkl').exists():
            print(f"Loading existing index from {index_dir}...")
            self.load_index(index_dir)
            print(f"Resuming from doc_id {self.next_doc_id}")
        else:
            print("No existing index found. Starting fresh.")
        
        # Process each folder as a batch
        for batch_num, folder in enumerate(folders, 1):
            print(f"\n{'='*70}")
            print(f"Processing Batch {batch_num}/{len(folders)}: {folder.name}")
            print(f"{'='*70}")
            
            try:
                docs_processed = self.process_folder_batch(folder)
                
                # Save index after each batch
                print(f"\nSaving index after batch {batch_num}...")
                self.save_index(index_dir)
                
                # Print inverted index to file after each batch
                inverted_index_dir = "inverted-indexes"
                print(f"Printing inverted index for batch {batch_num}...")
                self.print_inverted_index_to_file(inverted_index_dir, folder.name)
                
                # Print batch summary
                analytics = self.get_analytics()
                print(f"Batch {batch_num} summary:")
                print(f"  Documents in batch: {docs_processed}")
                print(f"  Total documents: {analytics['num_documents']}")
                print(f"  Total unique tokens: {analytics['num_unique_tokens']}")
                
            except Exception as e:
                print(f"Error processing batch {folder.name}: {e}")
                print(f"Index saved up to batch {batch_num - 1}")
                raise
        
        print(f"\n{'='*70}")
        print("All batches processed successfully!")
        print(f"{'='*70}")
    
    def get_analytics(self) -> Dict[str, any]:
        unique_tokens = len(self.index.index)
        total_documents = len(self.doc_id_map)
        
        total_postings = sum(len(postings) for postings in self.index.index.values())
        
        return {
            'num_documents': total_documents,
            'num_unique_tokens': unique_tokens,
            'total_postings': total_postings,
            'avg_postings_per_token': total_postings / unique_tokens if unique_tokens > 0 else 0,
            'skipped_urls': self.skipped_urls
        }
    
    def save_index(self, index_dir: str) -> None:
        index_path = Path(index_dir)
        index_path.mkdir(parents=True, exist_ok=True)
        
        index_file = index_path / 'inverted_index.pkl'
        with open(index_file, 'wb') as f:
            index_dict = dict(self.index.index)
            pickle.dump(index_dict, f)
        
        doc_map_file = index_path / 'doc_id_map.pkl'
        with open(doc_map_file, 'wb') as f:
            pickle.dump(self.doc_id_map, f)
        
        url_map_file = index_path / 'url_to_doc_id.pkl'
        with open(url_map_file, 'wb') as f:
            pickle.dump(self.url_to_doc_id, f)
        
        print(f"Index saved to {index_dir}")
    
    def load_index(self, index_dir: str) -> None:
        """Load index from disk and resume doc_id assignment."""
        index_path = Path(index_dir)
        
        index_file = index_path / 'inverted_index.pkl'
        with open(index_file, 'rb') as f:
            index_dict = pickle.load(f)
            self.index.index = defaultdict(list, index_dict)
        
        doc_map_file = index_path / 'doc_id_map.pkl'
        with open(doc_map_file, 'rb') as f:
            self.doc_id_map = pickle.load(f)
        
        url_map_file = index_path / 'url_to_doc_id.pkl'
        with open(url_map_file, 'rb') as f:
            self.url_to_doc_id = pickle.load(f)
        
        # Calculate next_doc_id: max doc_id + 1, or 0 if empty
        if self.doc_id_map:
            self.next_doc_id = max(self.doc_id_map.keys()) + 1
        else:
            self.next_doc_id = 0
        
        self.total_docs = len(self.doc_id_map)
        
        print(f"Index loaded from {index_dir}")
        print(f"  Documents: {self.total_docs}")
        print(f"  Next doc_id: {self.next_doc_id}")
    
    def get_index_size_kb(self, index_dir: str) -> float:
        """Calculate the total size of the index on disk in KB."""
        index_path = Path(index_dir)
        if not index_path.exists():
            return 0.0
        
        total_size_bytes = 0
        
        # Sum the size of all .pkl files in the index directory
        for pkl_file in index_path.glob('*.pkl'):
            if pkl_file.is_file():
                total_size_bytes += pkl_file.stat().st_size
        
        # Convert bytes to KB
        total_size_kb = total_size_bytes / 1024.0
        return total_size_kb
    
    def print_inverted_index_to_file(self, output_dir: str, batch_name: str) -> None:
        """
        Print the inverted index to a text file.
        
        Args:
            output_dir: Directory where the inverted index file will be saved
            batch_name: Name of the batch (used for the filename)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename from batch name (sanitize for filesystem)
        safe_batch_name = batch_name.replace('/', '_').replace('\\', '_')
        filename = f"inverted_index_{safe_batch_name}.txt"
        file_path = output_path / filename
        
        # Get the inverted index
        index = self.index.index
        sorted_terms = sorted(index.keys())
        
        # Build the content
        lines = [
            "=" * 70,
            f"INVERTED INDEX - BATCH: {batch_name}",
            "=" * 70,
            f"Total documents: {len(self.doc_id_map)}",
            f"Total unique tokens: {len(sorted_terms)}",
            "=" * 70,
            "",
        ]
        
        # Add each term and its postings
        for term in sorted_terms:
            postings = index[term]
            sorted_postings = sorted(postings, key=lambda x: x[0])
            lines.append(f"'{term}' -> {sorted_postings}")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"End of inverted index for batch: {batch_name}")
        lines.append("=" * 70)
        
        # Write to file
        content = "\n".join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  Inverted index saved to: {file_path}")
    
    def generate_report(self, index_dir: str, output_file: str = 'index_report.txt') -> None:
        """Generate a report with analytics about the index and save it to a .txt file."""
        analytics = self.get_analytics()
        index_size_kb = self.get_index_size_kb(index_dir)
        
        # Create report content in table format
        report_lines = [
            "=" * 70,
            "INDEX ANALYTICS REPORT",
            "=" * 70,
            "",
            "Metric                                    | Value",
            "-" * 70,
            f"Number of indexed documents              | {analytics['num_documents']}",
            f"Number of unique tokens                  | {analytics['num_unique_tokens']}",
            f"Total size of index on disk (KB)         | {index_size_kb:.2f}",
            f"Number of skipped URLs                   | {analytics['skipped_urls']}",
            "",
            "=" * 70,
        ]
        
        report_content = "\n".join(report_lines)
        
        # Save report to file
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\nReport saved to {output_file}")
        print("\n" + report_content)