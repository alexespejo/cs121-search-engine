# cs121-search-engine

## Contains Two Tools:
    index_dataset.py
    search_engine.py
### Index Dataset
- indexes a dataset using an inverted index
- offloads inverted index to .pkl file
- batches on a per directory basis

The dataset must be in the format:
```text
data
└─── *.json
...
```
### Search Engine
- accepts a query
- returns top 5 results