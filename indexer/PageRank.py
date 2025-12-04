"""
PageRank Module

Builds a link graph from the document corpus and computes PageRank scores.
Uses the existing index for URL-to-ID mappings to store the graph efficiently
with integer IDs rather than raw URLs.
"""

import utils.constants as const
from utils.file_io import is_valid_dir, is_valid_file, get_json_file_list, load_file_list, save_file_list
from indexer.inverted_index import load_index_full

import json
import pickle
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag
from collections import defaultdict
from logging import getLogger

logger = getLogger(__name__)


class LinkGraph:
    """
    Represents a web graph as an adjacency list using integer doc IDs.
    """
    def __init__(self):
        # Adjacency list: doc_id -> list of doc_ids it links to
        self.outlinks: dict[int, list[int]] = defaultdict(list)
        # Reverse adjacency: doc_id -> list of doc_ids that link to it
        self.inlinks: dict[int, list[int]] = defaultdict(list)
        # Set of all doc_ids in the graph
        self.nodes: set[int] = set()
    
    def add_edge(self, from_id: int, to_id: int) -> None:
        """Add a directed edge from from_id to to_id."""
        if to_id not in self.outlinks[from_id]:
            self.outlinks[from_id].append(to_id)
            self.inlinks[to_id].append(from_id)
        self.nodes.add(from_id)
        self.nodes.add(to_id)
    
    def get_outlink_count(self, doc_id: int) -> int:
        """Return the number of outgoing links from a document."""
        return len(self.outlinks.get(doc_id, []))
    
    def get_inlinks(self, doc_id: int) -> list[int]:
        """Return list of documents that link to this document."""
        return self.inlinks.get(doc_id, [])
    
    def save(self, filepath: Path) -> None:
        """Save the graph to a pickle file."""
        data = {
            'outlinks': dict(self.outlinks),
            'inlinks': dict(self.inlinks),
            'nodes': self.nodes
        }
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Link graph saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path) -> "LinkGraph":
        """Load a graph from a pickle file."""
        graph = cls()
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        graph.outlinks = defaultdict(list, data['outlinks'])
        graph.inlinks = defaultdict(list, data['inlinks'])
        graph.nodes = data['nodes']
        return graph


class PageRank:
    """
    Computes PageRank scores for documents in the corpus.
    
    Uses the existing index for URL-to-ID mapping and parses documents
    to build a link graph.
    """
    
    def __init__(self, 
                 data_dir_str: str = const.DATA_DIR_DEFAULT, 
                 index_dir_str: str = const.INDEX_DIR_DEFAULT):
        """
        Initialize PageRank with paths to data and index directories.
        
        Args:
            data_dir_str: Path to the directory containing input documents.
            index_dir_str: Path to the directory where the index is stored.
        """
        logger.info("Initializing PageRank...")
        
        # Validate data directory
        self.data_path: Path = Path(data_dir_str)
        if not is_valid_dir(self.data_path):
            error_message = f"Data directory {self.data_path} is invalid"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        # Validate index directory
        self.index_path: Path = Path(index_dir_str)
        if not is_valid_dir(self.index_path):
            error_message = f"Index directory {self.index_path} is invalid"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        # Load URL mappings from existing index
        logger.info("Loading URL mappings from index...")
        index_file = self.index_path / f"main_{const.INDEX_FILENAME}.nidx"
        if not is_valid_file(index_file):
            error_message = f"Index file {index_file} not found"
            logger.error(error_message)
            raise FileNotFoundError(error_message)
        
        with open(index_file, 'rb') as f:
            inv_index = load_index_full(f)
        
        # Create URL to doc_id mapping (reverse of doc_id_to_url)
        self.doc_id_to_url: dict[int, str] = inv_index.doc_id_to_url
        self.url_to_doc_id: dict[str, int] = {url: doc_id for doc_id, url in self.doc_id_to_url.items()}
        
        logger.info(f"Loaded {len(self.url_to_doc_id)} URL mappings")
        
        # Initialize graph and file list
        self.graph = LinkGraph()
        
        # Load or create file list
        file_list_path = Path(f"{const.FILE_LIST_FILENAME}.pkl")
        if is_valid_file(file_list_path):
            self.file_list: list[Path] = load_file_list(f"{const.FILE_LIST_FILENAME}.pkl")
        else:
            self.file_list: list[Path] = get_json_file_list(str(self.data_path))
            save_file_list(self.file_list)
        
        # PageRank scores
        self.pagerank_scores: dict[int, float] = {}
        
        logger.info("PageRank initialized")
    
    def normalize_url(self, url: str, base_url: str = "") -> str:
        """
        Normalize a URL for consistent matching.
        
        - Removes fragments (#...)
        - Resolves relative URLs against base
        - Strips trailing slashes
        - Lowercases the domain
        """
        # Remove fragment
        url, _ = urldefrag(url)
        
        # Handle relative URLs
        if base_url and not urlparse(url).netloc:
            url = urljoin(base_url, url)
        
        # Parse and normalize
        parsed = urlparse(url)
        
        # Lowercase domain
        netloc = parsed.netloc.lower()
        
        # Reconstruct URL
        normalized = f"{parsed.scheme}://{netloc}{parsed.path}"
        
        # Remove trailing slash (except for root)
        if normalized.endswith('/') and parsed.path != '/':
            normalized = normalized.rstrip('/')
        
        return normalized
    
    def extract_links(self, html_content: str, base_url: str) -> list[str]:
        """
        Extract all valid outgoing links from HTML content.
        
        Args:
            html_content: The HTML content to parse.
            base_url: The URL of the page (for resolving relative links).
            
        Returns:
            List of normalized URLs found in the document.
        """
        links = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all anchor tags with href
            for anchor in soup.find_all('a', href=True):
                href: str = str(anchor['href'])
                
                # Skip empty, javascript, mailto, and anchor-only links
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    continue
                
                # Normalize the URL
                normalized = self.normalize_url(href, base_url)
                
                # Only include http/https links
                if normalized.startswith(('http://', 'https://')):
                    links.append(normalized)
                    
        except Exception as e:
            logger.warning(f"Failed to extract links from {base_url}: {e}")
        
        return links
    
    def get_doc_id_for_url(self, url: str) -> int | None:
        """
        Get the doc_id for a URL, trying various normalizations.
        
        Args:
            url: The URL to look up.
            
        Returns:
            The doc_id if found, None otherwise.
        """
        # Try exact match first
        if url in self.url_to_doc_id:
            return self.url_to_doc_id[url]
        
        # Try with/without trailing slash
        if url.endswith('/'):
            alt_url = url.rstrip('/')
        else:
            alt_url = url + '/'
        
        if alt_url in self.url_to_doc_id:
            return self.url_to_doc_id[alt_url]
        
        # Try http <-> https
        if url.startswith('https://'):
            http_url = 'http://' + url[8:]
            if http_url in self.url_to_doc_id:
                return self.url_to_doc_id[http_url]
        elif url.startswith('http://'):
            https_url = 'https://' + url[7:]
            if https_url in self.url_to_doc_id:
                return self.url_to_doc_id[https_url]
        
        return None
    
    def process_file(self, file_path: Path) -> None:
        """
        Process a single JSON file to extract links.
        
        Args:
            file_path: Path to the JSON file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            url = data.get('url', '')
            content = data.get('content', '')
            
            if not url or not content:
                return
            
            # Remove fragment from URL
            if '#' in url:
                url = url.split('#')[0]
            
            # Get the doc_id for this URL
            source_id = self.get_doc_id_for_url(url)
            if source_id is None:
                # This URL isn't in our index, skip
                return
            
            # Add the node to the graph (even if no outlinks)
            self.graph.nodes.add(source_id)
            
            # Extract outgoing links
            links = self.extract_links(content, url)
            
            # Add edges for each link that exists in our index
            for link_url in links:
                target_id = self.get_doc_id_for_url(link_url)
                if target_id is not None and target_id != source_id:
                    self.graph.add_edge(source_id, target_id)
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
    
    def build_graph(self) -> None:
        """
        Build the link graph by processing all documents.
        """
        logger.info("Building link graph...")
        
        total_files = len(self.file_list)
        for i, file_path in enumerate(self.file_list):
            if i % 5000 == 0:
                logger.info(f"Processing file {i}/{total_files}...")
            self.process_file(file_path)
        
        logger.info(f"Graph built: {len(self.graph.nodes)} nodes, "
                   f"{sum(len(v) for v in self.graph.outlinks.values())} edges")
    
    def compute_pagerank(self, 
                         damping: float = 0.85, 
                         max_iterations: int = 100, 
                         tolerance: float = 1e-6) -> dict[int, float]:
        """
        Compute PageRank scores using the power iteration method.
        
        Args:
            damping: The damping factor (probability of following a link).
            max_iterations: Maximum number of iterations.
            tolerance: Convergence threshold.
            
        Returns:
            Dictionary mapping doc_id to PageRank score.
        """
        logger.info(f"Computing PageRank (damping={damping}, max_iter={max_iterations})...")
        
        nodes = list(self.graph.nodes)
        n = len(nodes)
        
        if n == 0:
            logger.warning("No nodes in graph, cannot compute PageRank")
            return {}
        
        # Initialize all nodes with equal probability
        scores = {node: 1.0 / n for node in nodes}
        
        # Precompute outlink counts (handle dangling nodes)
        outlink_counts = {node: max(self.graph.get_outlink_count(node), 1) for node in nodes}
        
        for iteration in range(max_iterations):
            new_scores = {}
            
            # Calculate the dangling node contribution
            # (nodes with no outlinks distribute their rank to all nodes)
            dangling_sum = sum(
                scores[node] for node in nodes 
                if self.graph.get_outlink_count(node) == 0
            )
            dangling_contribution = damping * dangling_sum / n
            
            max_diff = 0.0
            
            for node in nodes:
                # Base rank (random jump probability)
                rank = (1 - damping) / n + dangling_contribution
                
                # Add contribution from incoming links
                for in_node in self.graph.get_inlinks(node):
                    rank += damping * scores[in_node] / outlink_counts[in_node]
                
                new_scores[node] = rank
                max_diff = max(max_diff, abs(rank - scores[node]))
            
            scores = new_scores
            
            if max_diff < tolerance:
                logger.info(f"PageRank converged after {iteration + 1} iterations")
                break
        else:
            logger.info(f"PageRank reached max iterations ({max_iterations})")
        
        self.pagerank_scores = scores
        return scores
    
    def save_pagerank(self, filepath: Path | None = None) -> None:
        """
        Save PageRank scores to a file.
        
        Args:
            filepath: Path to save the scores. Defaults to index/pagerank.pkl
        """
        if filepath is None:
            filepath = self.index_path / "pagerank.pkl"
        
        data = {
            'scores': self.pagerank_scores,
            'num_nodes': len(self.graph.nodes),
            'num_edges': sum(len(v) for v in self.graph.outlinks.values())
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"PageRank scores saved to {filepath}")
    
    def save_graph(self, filepath: Path | None = None) -> None:
        """
        Save the link graph to a file.
        
        Args:
            filepath: Path to save the graph. Defaults to index/link_graph.pkl
        """
        if filepath is None:
            filepath = self.index_path / "link_graph.pkl"
        
        self.graph.save(filepath)
    
    def run(self, 
            damping: float = 0.85, 
            max_iterations: int = 100,
            save_graph: bool = True) -> dict[int, float]:
        """
        Run the full PageRank computation pipeline.
        
        Args:
            damping: The damping factor for PageRank.
            max_iterations: Maximum iterations for PageRank computation.
            save_graph: Whether to save the link graph to disk.
            
        Returns:
            Dictionary mapping doc_id to PageRank score.
        """
        logger.info("Running PageRank pipeline...")
        
        # Build the link graph
        self.build_graph()
        
        # Optionally save the graph
        if save_graph:
            self.save_graph()
        
        # Compute PageRank
        scores = self.compute_pagerank(damping=damping, max_iterations=max_iterations)
        
        # Save PageRank scores
        self.save_pagerank()
        
        logger.info("PageRank pipeline complete")
        return scores
    
    def display_report(self, top_n: int = 20) -> None:
        """
        Display a report of the PageRank computation.
        
        Args:
            top_n: Number of top-ranked pages to display.
        """
        if not self.pagerank_scores:
            print("No PageRank scores computed yet.")
            return
        
        sorted_scores = sorted(self.pagerank_scores.items(), key=lambda x: x[1], reverse=True)
        
        print("\n" + "=" * 70)
        print("PAGERANK REPORT")
        print("=" * 70)
        print(f"Total nodes: {len(self.graph.nodes)}")
        print(f"Total edges: {sum(len(v) for v in self.graph.outlinks.values())}")
        print(f"\nTop {top_n} pages by PageRank:")
        print("-" * 70)
        
        for i, (doc_id, score) in enumerate(sorted_scores[:top_n], 1):
            url = self.doc_id_to_url.get(doc_id, "Unknown URL")
            # Truncate URL if too long
            if len(url) > 50:
                url = url[:47] + "..."
            print(f"{i:3}. [{score:.6f}] {url}")
        
        print("=" * 70)


def load_pagerank(index_dir: str = const.INDEX_DIR_DEFAULT) -> dict[int, float]:
    """
    Load PageRank scores from disk.
    
    Args:
        index_dir: Directory where pagerank.pkl is stored.
        
    Returns:
        Dictionary mapping doc_id to PageRank score.
    """
    filepath = Path(index_dir) / "pagerank.pkl"
    if not is_valid_file(filepath):
        raise FileNotFoundError(f"PageRank file not found: {filepath}")
    
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    
    return data['scores']


# Module-level cache for scores
_pagerank_cache: dict[int, float] | None = None


def get_page_rank(doc_id: int, index_dir: str = const.INDEX_DIR_DEFAULT) -> float:
    """
    Get the PageRank score for a document.
    
    Args:
        doc_id: The document ID to look up.
        index_dir: Directory where pagerank.pkl is stored.
        
    Returns:
        PageRank score (float), or 0.0 if not found or PageRank not computed.
    """
    global _pagerank_cache
    
    if _pagerank_cache is None:
        try:
            _pagerank_cache = load_pagerank(index_dir)
        except FileNotFoundError:
            logger.warning("PageRank file not found. Run run_pagerank.py first to compute PageRank scores.")
            _pagerank_cache = {}
    
    return _pagerank_cache.get(doc_id, 0.0)


def load_link_graph(index_dir: str = const.INDEX_DIR_DEFAULT) -> LinkGraph:
    """
    Load the link graph from disk.
    
    Args:
        index_dir: Directory where link_graph.pkl is stored.
        
    Returns:
        LinkGraph instance.
    """
    filepath = Path(index_dir) / "link_graph.pkl"
    if not is_valid_file(filepath):
        raise FileNotFoundError(f"Link graph file not found: {filepath}")
    
    return LinkGraph.load(filepath)


# Entry point for running PageRank standalone
if __name__ == "__main__":
    import sys
    from utils.log_setup import setup_logging
    
    setup_logging()
    
    # Parse command line args
    data_dir = const.DATA_DIR_DEFAULT
    index_dir = const.INDEX_DIR_DEFAULT
    
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    if len(sys.argv) > 2:
        index_dir = sys.argv[2]
    
    print(f"Data directory: {data_dir}")
    print(f"Index directory: {index_dir}")
    
    # Run PageRank
    pr = PageRank(data_dir_str=data_dir, index_dir_str=index_dir)
    pr.run()
    pr.display_report()

