from typing import List, Dict, Set, Union
import bs4

def tokenize_fields(fields: Dict[str, Union[str, List[str], List[tuple]]]) -> Dict[str, int]:
    all_text = []
    
    for field_name in ['title', 'meta_desc', 'body']:
        if field_name in fields and fields[field_name]:
            all_text.append(str(fields[field_name]))
    
    for field_name in ['h1', 'h2', 'h3', 'alt_text']:
        if field_name in fields and fields[field_name]:
            for item in fields[field_name]:
                if isinstance(item, str):
                    all_text.append(item)
    
    if 'links' in fields and fields['links']:
        for link_text, link_url in fields['links']:
            if link_text:
                all_text.append(link_text)
    
    combined_text = ' '.join(all_text)
    tokens = tokenize(combined_text)
    
    return compute_word_frequencies(tokens)

def extract_fields_html(html_content: str) -> Dict[str, Union[str, List[str], List[tuple]]]:
    # idea is to extract what's most relevant to the user
    # TODO: this is a simple approach off the dome
    soup = bs4.BeautifulSoup(html_content, 'html.parser')
    
    for element in soup(['script', 'style', 'nav', 'footer']):
        element.decompose()
    
    title_tag = soup.find('title')
    main_tag = soup.find('main')
    meta_tag_desc = soup.find('meta', {'name': 'description'})
    body_tag = soup.find('body')

    fields = {
        'title': title_tag.get_text() if title_tag else '',
        'h1': [h.get_text() for h in soup.find_all('h1')],
        'h2': [h.get_text() for h in soup.find_all('h2')],
        'h3': [h.get_text() for h in soup.find_all('h3')],
        'meta_desc': meta_tag_desc.get('content', '') if meta_tag_desc else '',
        'body': main_tag.get_text() if main_tag else (body_tag.get_text() if body_tag else soup.get_text()),
        'links': [(a.get_text(), a['href']) for a in soup.find_all('a', href=True)],
        'alt_text': [img.get('alt', '') for img in soup.find_all('img') if img.has_attr('alt')],
    }
    
    return fields

def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    current: List[str] = []
    for ch in text:
        if ch.isascii() and (ch.isalpha() or ch.isdigit()):
            current.append(ch.lower())
        else:
            if current:
                tokens.append("".join(current))
                current.clear()
    if current:
        tokens.append("".join(current))
    return tokens

def compute_word_frequencies(tokens: List[str]) -> Dict[str, int]:
    res = {}
    for token in tokens:
        if token in res:
            res[token] += 1
        else:
            res[token] = 1
    return res

def print_frequencies(frequencies: Dict[str, int]) -> None:
    sorted_items = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    for word, count in sorted_items:
        print(f"{word} = {count}")

def get_tokens_set(text_file_path: str) -> Set[str]:
    return set(tokenize(text_file_path))

def count_common_tokens(file1_path: str, file2_path: str) -> int:
    tokens_file1 = get_tokens_set(file1_path)
    tokens_file2 = get_tokens_set(file2_path)
    
    common_tokens = tokens_file1.intersection(tokens_file2)
    
    return len(common_tokens)
