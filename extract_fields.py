from bs4 import BeautifulSoup
from typing import Dict

def extract_fields(content: str) -> Dict[str, str]:
    # idea is to extract what's most relevant to the user
    # TODO: this is a simple approach off the dome
    soup = BeautifulSoup(content, 'html.parser')
    
    for element in soup(['script', 'style', 'nav', 'footer']):
        element.decompose()
    
    fields = {
        'title': soup.find('title').get_text() if soup.find('title') else '',
        'h1': [h.get_text() for h in soup.find_all('h1')],
        'h2': [h.get_text() for h in soup.find_all('h2')],
        'h3': [h.get_text() for h in soup.find_all('h3')],
        'meta_desc': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else '',
        'body': soup.find('main').get_text() if soup.find('main') else soup.get_text(),
        'links': [(a.get_text(), a['href']) for a in soup.find_all('a', href=True)],
        'alt_text': [img['alt'] for img in soup.find_all('img', alt=True)]
    }
    
    return fields
