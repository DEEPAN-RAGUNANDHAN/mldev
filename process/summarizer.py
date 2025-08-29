from summa import summarizer
import re

# Patterns to ignore boilerplate text
IGNORE_PATTERNS = [
    r"sign", r"join", r"cookie", r"privacy", r"policy", r"user agreement",
    r"linkedin", r"email", r"phone", r"forgot", r"password",
    r"show", r"skip", r"welcome", r"games", r"learning"
]

def remove_noise(text):
    # Remove unwanted short or repetitive phrases
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if len(line.split()) < 5:
            continue
        if any(re.search(pattern, line.lower()) for pattern in IGNORE_PATTERNS):
            continue
        clean_lines.append(line)
    return " ".join(clean_lines)

def summarize_text(text, ratio=0.2):
    clean_text = remove_noise(text)
    try:
        summary = summarizer.summarize(clean_text, ratio=ratio)
        return summary.strip() if summary.strip() else clean_text
    except Exception:
        return clean_text
