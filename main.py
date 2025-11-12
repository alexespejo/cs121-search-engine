from pathlib import Path
from indexer import Indexer


def display_inverted_index(indexer: Indexer):
    print("\n" + "=" * 70)
    print("INVERTED INDEX DATA STRUCTURE")
    print("=" * 70)
    
    index = indexer.index.index
    
    sorted_terms = sorted(index.keys())
    
    for term in sorted_terms:
        postings = index[term]
        sorted_postings = sorted(postings, key=lambda x: x[0])
        print(f"'{term}' -> {sorted_postings}")
    
    print("=" * 70)


def main():
    # Process test-data/DEV with batch processing
    # Each folder in test-data/DEV is a batch
    test_data_dir = "test-data/DEV"
    index_dir = "index"
    
    # TODO: If you want to update the index after aggregating rethink this logic since it removes all .pkl files
    index_path = Path(index_dir)
    if index_path.exists() and index_path.is_dir():
        for pkl_file in index_path.glob("*.pkl"):
            try:
                pkl_file.unlink()
                print(f"Removed: {pkl_file}")
            except Exception as e:
                print(f"Could not remove {pkl_file}: {e}")

    indexer = Indexer()
    
    # Process all batches
    if Path(test_data_dir).exists():
        print(f"Processing batches from {test_data_dir}")
        indexer.process_batches(test_data_dir, index_dir)
    else:
        # sample run
        print(f"Warning: {test_data_dir} does not exist. Processing sample data instead.")
        # Fallback to sample data processing
        json_files = [
            "sample_data/example1.json",
            "sample_data/github.json",
            "sample_data/reddit.json",
            "sample_data/stackoverflow.json",
            "sample_data/wikipedia.json",
        ]
        
        for json_file in json_files:
            file_path = Path(json_file)
            if file_path.exists():
                print(f"Processing {json_file}...")
                indexer.process_json_file(file_path)
            else:
                print(f"Warning: File not found: {json_file}")
        
        print(f"\nSaving index to {index_dir}...")
        indexer.save_index(index_dir)
    
    # Generate final analytics and report
    analytics = indexer.get_analytics()
    print(f"\n{'='*70}")
    print("FINAL INDEX STATISTICS")
    print(f"{'='*70}")
    print(f"  Documents: {analytics['num_documents']}")
    print(f"  Unique tokens: {analytics['num_unique_tokens']}")
    print(f"  Total postings: {analytics['total_postings']}")
    print(f"  Average postings per token: {analytics['avg_postings_per_token']:.2f}")
    
    print(f"\nGenerating index report...")
    indexer.generate_report(index_dir, 'index_report.txt')

if __name__ == '__main__':
    main()
