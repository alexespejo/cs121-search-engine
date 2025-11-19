# How Indexing Works Per JSON File

## Step-by-Step Flow

```
JSON File (e.g., stackoverflow.json)
    │
    │ { "url": "...", "content": "<html>..." }
    │
    ▼
process_json_file(file_path)
    │
    │ 1. Parse JSON
    │ 2. Extract url and content
    │ 3. Remove URL fragment (#anchor)
    │
    ▼
process_document(url, content)
    │
    │ 1. Assign doc_id (or reuse if URL exists)
    │    - New URL → next_doc_id (0, 1, 2, ...)
    │    - Store: url_to_doc_id[url] = doc_id
    │    - Store: doc_id_map[doc_id] = url
    │
    ▼
extract_fields(content)
    │
    │ 1. Parse HTML with BeautifulSoup
    │ 2. Remove <script>, <style>, <nav>, <footer>
    │ 3. Extract fields:
    │    - title
    │    - h1, h2, h3 (arrays)
    │    - meta_desc
    │    - body (main content or entire body)
    │    - links (text + href pairs)
    │    - alt_text (from images)
    │
    ▼
tokenize(fields)
    │
    │ 1. Combine text from: title, meta_desc, body, h1/h2/h3, alt_text, link text
    │ 2. Tokenize combined text:
    │    - Split on non-alphanumeric
    │    - Convert to lowercase
    │    - Keep only ASCII alphanumeric
    │ 3. Count frequencies (excluding stop words)
    │
    ▼ Returns: { "term": frequency, ... }
    │
    ▼
index.addEntry(term, doc_id, frequency)
    │
    │ For each (term, frequency) pair:
    │    self.index[term].append((doc_id, frequency))
    │
    ▼
Inverted Index Structure:
    {
        "term1": [(doc_id, freq), (doc_id, freq), ...],
        "term2": [(doc_id, freq), ...],
        ...
    }
```

## Example

### Input JSON:
```json
{
  "url": "https://stackoverflow.com",
  "content": "<html><title>Stack Overflow</title><body><h1>Stack Overflow</h1><p>programming questions</p></body></html>"
}
```

### Processing:
1. **doc_id assignment**: URL → doc_id = 0
2. **Field extraction**: 
   - title: "Stack Overflow"
   - h1: ["Stack Overflow"]
   - body: "Stack Overflow programming questions"
3. **Tokenization**:
   - Combined: "Stack Overflow Stack Overflow programming questions"
   - Tokens: ["stack", "overflow", "stack", "overflow", "programming", "questions"]
   - Frequencies (no stop words): {"stack": 2, "overflow": 2, "programming": 1, "questions": 1}
4. **Index Updates**:
   - `index["stack"].append((0, 2))`
   - `index["overflow"].append((0, 2))`
   - `index["programming"].append((0, 1))`
   - `index["questions"].append((0, 1))`

### Result:
```python
index = {
    "stack": [(0, 2)],
    "overflow": [(0, 2)],
    "programming": [(0, 1)],
    "questions": [(0, 1)]
}
```

## Key Points

1. **One JSON file = One document**: Each JSON file represents one web page/document
2. **doc_id is sequential**: Assigned 0, 1, 2, ... for each new unique URL
3. **Duplicate URLs**: If the same URL appears in multiple JSON files, it reuses the same doc_id
4. **Inverted Index**: Terms point to lists of (doc_id, frequency) pairs
5. **Incremental building**: As each JSON is processed, terms are added to the existing index structure
6. **All documents share one index**: The index is a single data structure that accumulates entries from all JSON files
