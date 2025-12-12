# cs121-search-engine

We wrote a Web search engine from the ground up that is capable of handling tens of thousands of Web pages, under harsh operational constraints and having a query response time under 300ms

## Contains Three Tools:
    Indexer
    Search Engine
    Page Rank
### Indexer
- indexes a dataset using an inverted index
- offloads inverted index to a custom binary file
- batches per 15,000 files

The dataset must be in the format:
```text
data
└─── *.json
...
```
### Search Engine
- accepts a query
- returns top 5 results

### Page Rank
- processes the dataset (assumedly in the same format as above) for inlinks and outlinks
- forms a graph structure
- computes PageRank per document
- Made easily accessible through a class
