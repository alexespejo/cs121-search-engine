import utils.constants as const
from indexer.inverted_index import Posting

import bs4
import nltk
from nltk.tokenize import word_tokenize
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

def calculate_postings(doc_id: int, zone_tokens: dict[str, list[str]]) -> dict[str, Posting]:
    postings: dict[str, Posting] = {}

    for zone_key, zone_name in const.ZONES.items():
            token_list = zone_tokens.get(zone_key, [])
            for term in token_list:
                if term not in postings:
                    postings[term] = Posting(doc_id)
                postings[term].add(zone_name)

    return postings


def tokenize_fields(fields: dict) -> dict[str, list[str]]:
    stemmer = PorterStemmer()

    def tokenize_list(text_list):
        joined = " ".join(text_list).lower()
        return [
            stemmer.stem(tok, to_lowercase=True)
            for tok in word_tokenize(joined)
            if tok.isascii() and tok.isalnum()
        ]

    out = {}

    out["body_tokens"] = tokenize_list(fields.get("body", []))
    out["title_tokens"] = tokenize_list(fields.get("title"))
    out["h1_tokens"] = tokenize_list(fields.get("h1", []))
    out["h2_tokens"] = tokenize_list(fields.get("h2", []))
    out["h3_tokens"] = tokenize_list(fields.get("h3", []))
    out["bold_tokens"] = tokenize_list(fields.get("bold", []))

    # anchors is [(href, anchor_text)]
    anchor_texts = [text for _, text in fields.get("anchors", [])]
    out["anchor_tokens"] = tokenize_list(anchor_texts)

    return out


def extract_fields_html(html_content: str) -> dict[str, list[str] | list[tuple[str, str]]]:
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(html_content, 'html.parser')
    
    for invalid_tag in const.INVALID_TAGS:
        for tag in soup.find_all(invalid_tag):
            tag.decompose()
    
    title: list[str] = soup.title.get_text(strip=True).split() if soup.title else [""]
    h1: list[str] = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2: list[str] = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3: list[str] = [h.get_text(strip=True) for h in soup.find_all("h3")]
    bold: list[str] = [b.get_text(strip=True) for b in soup.find_all(["b", "strong"]) if b.get_text(strip=True)]
    anchors: list[tuple[str, str]] = []
    for a in soup.find_all("a"):
        anchor_text = a.get_text(strip=True)
        href = str(a.get("href", "")).strip()
        if anchor_text and href:
            anchors.append((href, anchor_text))
    
    for tag in soup.find_all(["h1", "h2", "h3", "b", "strong"]):
        tag.extract()
    
    body: list[str] = soup.body.get_text(" ", strip=True).split() if soup.body else soup.get_text(" ", strip=True).split()
    
    return {
        "title" : title,
        "h1" : h1,
        "h2" : h2,
        "h3" : h3,
        "bold" : bold,
        "body" : body,
        "anchors" : anchors
    }