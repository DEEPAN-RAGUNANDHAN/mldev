
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("PROGRAMMABLE_SEARCH_ENGINE_ID")

def extract_page_text(url):
    """Fetches and extracts readable text from the given URL."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Remove script and style elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        return text  # Limit size to 2000 chars for prompt
    except Exception as e:
        return f"[Failed to extract content from {url}: {str(e)}]"

def google_search(query, num_results=3):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query,
        "num": num_results
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    logger.info(data)

    combined_text = ""
    for item in data.get("items", []):
        title = item.get("title")
        snippet = item.get("snippet")
        link = item.get("link")

        page_text = extract_page_text(link)

        combined_text += f"{title}\n{snippet}\n{page_text}\n\n"

    return combined_text.strip()