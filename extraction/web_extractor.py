import requests
from bs4 import BeautifulSoup

def extract_page_text(url: str, max_length: int = 2000) -> str:
    #headers = {"User-Agent": "Mozilla/5.0"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com"
    }

    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"[Failed to fetch {url}: {str(e)}]"

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "noscript", "footer", "header", "nav", "form"]):
        tag.decompose()

    # Try to extract only meaningful text elements
    content_blocks = []
    for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "span", "section"]):
        text = tag.get_text(strip=True)
        if text and len(text.split()) > 5:
            content_blocks.append(text)

    full_text = "\n\n".join(content_blocks)

    # Truncate long pages to avoid token overflow
    return full_text.strip()
