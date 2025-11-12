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
    json_files = [
        "sample_data/example1.json",
        "sample_data/github.json",
        "sample_data/reddit.json",
        "sample_data/stackoverflow.json",
        "sample_data/wikipedia.json",
    ]
    
    indexer = Indexer()
    
    for json_file in json_files:
        file_path = Path(json_file)
        if file_path.exists():
            print(f"Processing {json_file}...")
            indexer.process_json_file(file_path)
        else:
            print(f"Warning: File not found: {json_file}")
    
    index_dir = "index"
    print(f"\nSaving index to {index_dir}...")
    indexer.save_index(index_dir)
    
    analytics = indexer.get_analytics()
    print(f"\nIndex built successfully!")
    print(f"  Documents: {analytics['num_documents']}")
    print(f"  Unique tokens: {analytics['num_unique_tokens']}")
    print(f"  Total postings: {analytics['total_postings']}")
    
    # Generate and save report
    print(f"\nGenerating index report...")
    indexer.generate_report(index_dir, 'index_report.txt')
    
    display_inverted_index(indexer)


if __name__ == '__main__':
    main()
