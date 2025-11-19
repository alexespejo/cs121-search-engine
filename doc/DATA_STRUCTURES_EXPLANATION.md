# An Explanation I totally wrote

TODO: Stemming

## Overview

This search engine uses an **inverted index** data structure, which is a fundamental data structure for information retrieval systems. Instead of storing documents and searching through them, it stores terms (words) and maps them to the documents where they appear.

---

## Core Data Structures

### 1. InvertedIndex (`InvertedIndex.py`)

**Structure:**

```python
Dict[str, List[tuple[int, int]]]
```

**Breakdown:**

- **Key**: `str` - A term/token (word) from the documents
- **Value**: `List[tuple[int, int]]` - A list of postings
  - Each posting is a tuple: `(doc_id, frequency)`
    - `doc_id`: Integer identifier for the document
    - `frequency`: Integer count of how many times the term appears in that document

**Example:**

```python
{
    "python": [(0, 3), (2, 1), (4, 5)],  # "python" appears in doc 0 (3 times), doc 2 (1 time), doc 4 (5 times)
    "code": [(0, 2), (1, 1)],            # "code" appears in doc 0 (2 times), doc 1 (1 time)
    "example": [(0, 1)]                   # "example" appears only in doc 0 (1 time)
}
```

**Why this structure?**

- **Fast lookup**: O(1) average time to find all documents containing a term
- **Space efficient**: Only stores terms that appear in documents (no empty entries)
- **Supports queries**: Easy to find documents containing specific terms

---

### 2. Document Mappings (`indexer.py`)

The Indexer class maintains two bidirectional mappings:

#### a) `doc_id_map: Dict[int, str]`

- **Key**: `int` - Document ID
- **Value**: `str` - URL of the document
- **Purpose**: Map document IDs to their URLs for retrieval

```python
{
    0: "https://www.example.com",
    1: "https://www.github.com",
    2: "https://www.reddit.com"
}
```

#### b) `url_to_doc_id: Dict[str, int]`

- **Key**: `str` - URL of the document
- **Value**: `int` - Document ID
- **Purpose**: Map URLs to document IDs (reverse lookup, prevents duplicates)

```python
{
    "https://www.example.com": 0,
    "https://www.github.com": 1,
    "https://www.reddit.com": 2
}
```

**Why both mappings?**

- `url_to_doc_id`: Quickly check if a URL has already been processed
- `doc_id_map`: Convert document IDs back to URLs when displaying results

---

## Data Flow

### Step 1: Input (JSON File)

```json
{
 "url": "https://www.example.com",
 "content": "<html>...</html>"
}
```

### Step 2: HTML Field Extraction (`extract_fields.py`)

Extracts structured data from HTML:

```python
{
    'title': 'Example Domain',
    'h1': ['Example Domain'],
    'h2': [],
    'h3': [],
    'meta_desc': 'Example description',
    'body': 'This domain is for use...',
    'links': [('IANA', 'https://www.iana.org/domains/example')],
    'alt_text': []
}
```

### Step 3: Tokenization (`tokenize.py` + `token.py`)

1. Combines all text fields into a single string
2. Tokenizes the text (splits into words, lowercases, filters non-ASCII)
3. Removes stop words (common words like "the", "a", "and")
4. Computes word frequencies

**Result:**

```python
{
    "example": 3,
    "domain": 2,
    "use": 1,
    "illustrative": 1
}
```

### Step 4: Index Building (`indexer.py`)

For each term and its frequency:

```python
index.addEntry("example", doc_id=0, frequency=3)
index.addEntry("domain", doc_id=0, frequency=2)
# etc.
```

This builds the inverted index:

```python
{
    "example": [(0, 3)],      # doc 0 has "example" 3 times
    "domain": [(0, 2)],       # doc 0 has "domain" 2 times
    "use": [(0, 1)]           # doc 0 has "use" 1 time
}
```

### Step 5: Storage

The index is saved to disk as three pickle files:

- `inverted_index.pkl` - The main inverted index
- `doc_id_map.pkl` - Document ID to URL mapping
- `url_to_doc_id.pkl` - URL to Document ID mapping

---

## Complete Example

### Input Documents:

1. Document 0: "Python is a programming language"
2. Document 1: "Python code examples"
3. Document 2: "Java is also a programming language"

### After Processing:

**Inverted Index:**

```python
{
    "python": [(0, 1), (1, 1)],           # appears in docs 0 and 1
    "programming": [(0, 1), (2, 1)],      # appears in docs 0 and 2
    "language": [(0, 1), (2, 1)],         # appears in docs 0 and 2
    "code": [(1, 1)],                     # appears only in doc 1
    "examples": [(1, 1)],                 # appears only in doc 1
    "java": [(2, 1)]                      # appears only in doc 2
}
```

**Document Mappings:**

```python
doc_id_map = {
    0: "https://example.com/doc1",
    1: "https://example.com/doc2",
    2: "https://example.com/doc3"
}

url_to_doc_id = {
    "https://example.com/doc1": 0,
    "https://example.com/doc2": 1,
    "https://example.com/doc3": 2
}
```

---

## Why Use an Inverted Index?

### Traditional Approach (Document-oriented):

- Store documents: `[doc1, doc2, doc3, ...]`
- To find "python": Search through ALL documents → O(N) where N = number of documents
- Slow for large collections

### Inverted Index Approach:

- Store terms: `{"python": [doc1, doc2], ...}`
- To find "python": Look up term directly → O(1) to get the list
- Fast even for millions of documents

### Benefits:

1. **Fast lookups**: Find all documents containing a term in O(1) average time
2. **Efficient storage**: Only store terms that exist (sparse representation)
3. **Supports complex queries**: Can combine results from multiple terms (AND, OR operations)
4. **Scalable**: Works well with large document collections

---

## Time Complexity

- **Building the index**: O(T) where T = total number of tokens across all documents
- **Looking up a term**: O(1) average case (hash table lookup)
- **Getting postings for a term**: O(P) where P = number of documents containing the term
- **Finding documents with multiple terms**: O(P1 + P2 + ... + Pn) where Pi = postings for term i

---

## Space Complexity

- **Inverted Index**: O(U × D_avg) where U = unique terms, D_avg = average documents per term
- **Document Mappings**: O(D) where D = number of documents
- **Total**: Typically much smaller than storing full documents, especially with stop word filtering
