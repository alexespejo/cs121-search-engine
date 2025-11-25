import utils.constants as const
from indexer.inverted_index import Posting

import bs4
import nltk
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
from nltk.stem import PorterStemmer
from warnings import filterwarnings

filterwarnings("ignore", category=bs4.MarkupResemblesLocatorWarning)
nltk.download("punkt")
nltk.download("punkt_tab")

def calculate_importance(token: str, important_words_set: set[str]) -> float:
    importance_score: float = 0.0
    if token in important_words_set:
        importance_score += 1
    return importance_score

def calculate_postings(doc_id: int, 
                       word_freq_dist: FreqDist, 
                       important_words_set: set[str]
                       ) -> dict[str, Posting]:
    postings_dict: dict[str, Posting] = {}
    for token, frequency in word_freq_dist.items():
        tf: float = float(frequency) / float(word_freq_dist.N())
        importance: float = calculate_importance(token, important_words_set)
        postings_dict[token] = Posting(doc_id, tf, importance)
    return postings_dict

def tokenize_fields(fields: dict[str, list[str]]) -> tuple[FreqDist, set[str]]:
    important_words: list = []
    for field, text_list in fields.items():
        if field != "body":
            important_words.extend(text_list)
    
    important_words_set: set[str] = set(important_words)
    
    combined_text_list = []
    combined_text_list.extend(fields["body"])
    combined_text_list.extend(important_words)

    combined_text_str = " ".join(combined_text_list)
    combined_text_str = combined_text_str.lower()
    
    stemmer = PorterStemmer()
    word_freq_dist = FreqDist(stemmer.stem(word.lower(), to_lowercase=True) 
                              for word in word_tokenize(combined_text_str) 
                              if word.isascii() and word.isalnum())    
    
    return word_freq_dist, important_words_set

def extract_fields_html(html_content: str) -> dict[str, list[str]]:
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html_content, 'html.parser')
    
    for invalid_tag in const.INVALID_TAGS:
        for tag in soup.find_all(invalid_tag):
            tag.decompose()
    
    title: list[str] = soup.title.get_text(strip=True).split() if soup.title else [""]
    h1: list[str] = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2: list[str] = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3: list[str] = [h.get_text(strip=True) for h in soup.find_all("h3")]
    bold: list[str] = [b.get_text(strip=True) for b in soup.find_all(["b", "strong"]) if b.get_text(strip=True)]
    
    for tag in soup.find_all(["h1", "h2", "h3", "b", "strong"]):
        tag.extract()
    
    body: list[str] = soup.body.get_text(" ", strip=True).split() if soup.body else soup.get_text(" ", strip=True).split()
    
    return {
        "title" : title,
        "h1" : h1,
        "h2" : h2,
        "h3" : h3,
        "bold" : bold,
        "body" : body
    }