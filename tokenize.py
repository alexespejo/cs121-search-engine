from typing import Dict, List, Union
from token import tokenize as tokenize_text, compute_word_frequencies


def tokenize(fields: Dict[str, Union[str, List[str], List[tuple]]]) -> Dict[str, int]:
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
    tokens = tokenize_text(combined_text)
    
    return compute_word_frequencies(tokens)
