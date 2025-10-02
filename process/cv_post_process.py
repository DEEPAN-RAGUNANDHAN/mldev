from rapidfuzz import fuzz
import gensim.downloader as api
import logging
import re
from typing import List, Dict


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Load this once globally (or cache it if you want better performance)
glove_model = api.load("glove-wiki-gigaword-50")  


def semantic_similarity(word1, word2, model):
    """Returns cosine similarity between two words if they exist in the model."""
    word1, word2 = word1.lower(), word2.lower()
    if word1 in model and word2 in model:
        return model.similarity(word1, word2)
    return 0.0


def filter_skills(output_json, user_data, job_data, min_fuzzy_similarity=50, min_semantic_similarity=0.5):
    """
    Filters hallucinated skills and adds relevant user skills based on fuzzy or semantic match with job description.


    Args:
        output_json (dict): Model-generated resume JSON.
        user_data (dict): Input user data with 'skills' and 'tools'.
        job_data (dict): Job description with 'skills', 'responsibilities', or 'qualifications'.
        min_fuzzy_similarity (int): Minimum fuzzy match score to include a skill.
        min_semantic_similarity (float): Cosine similarity threshold for semantic match.
        max_additional (int): Maximum extra skills to include from user data.


    Returns:
        dict: Cleaned and enhanced resume JSON.
    """
    user_skills = user_data.get("skills", [])
    user_tools = user_data.get("tools", [])
    all_user_terms = set(map(str.lower, user_skills + user_tools))
    
    # Step 1: Keep exact matches only
    model_skills = output_json.get("skills", [])
    retained_skills = [
        skill for skill in model_skills if skill.lower() in all_user_terms
    ]


    # Step 2: Prepare job keywords
    job_keywords = (
        job_data.get("skills", []) +
        job_data.get("responsibilities", []) +
        job_data.get("qualifications", [])
    )
    job_keywords_flat = ' '.join(job_keywords).lower()
    job_terms = list(set(job_keywords_flat.split()))  # unique words only


    # Step 3: Fuzzy or semantic match for boosting
    extra_skills = []
    for skill in user_skills + user_tools:
        skill_lc = skill.lower()
        # Fuzzy match
        fuzzy_score = fuzz.partial_ratio(skill_lc, job_keywords_flat)
        # Semantic match: find max similarity to any job term
        semantic_score = max(
            (semantic_similarity(skill_lc, job_term, glove_model) for job_term in job_terms),
            default=0.0
        )


        if (fuzzy_score >= min_fuzzy_similarity or semantic_score >= min_semantic_similarity) and skill not in retained_skills:
            combined_score = 0.5 * (fuzzy_score / 100) + 0.5 * semantic_score
            extra_skills.append((skill, combined_score))


    # Step 4: Add top N extra relevant skills
    extra_skills = sorted(extra_skills, key=lambda x: -x[1])
    boosted_skills = retained_skills + [s[0] for s in extra_skills]


    output_json["skills"] = boosted_skills[:10]
    return format_data(output_json, user_data)


def format_data(ip_json, user_data):
    # for item in ip_json["experience_summary"]:
    #     if isinstance(item["description"], str):
    #         text = item["description"]
    #         item["description"] = [sentence.strip() for sentence in text.split('.') if sentence.strip()]
    # for item in ip_json["past_projects"]:
    #     if isinstance(item["description"], str):
    #         text = item["description"]
    #         item["description"] = [sentence.strip() for sentence in text.split('.') if sentence.strip()]
    data = {
    "personal_info": {
        "name": user_data["name"],
        #"title": user_data["designation"],  # old
        "title": user_data.get("job_title", user_data.get("designation", "")),  # changed: prioritize job_title from user_data if available
        "mail": user_data["email"],
        "phone": user_data["contact"],
        "linkedin": user_data["linkedin"],
        "portfolio": user_data["portfolio"],
        "address": user_data["address"]
    },
    "profile_summary": ip_json.get("summary", ""),
    "work_experience": ip_json.get("experience_summary", []), #company_name, position, period, description
    "projects": ip_json.get("past_projects", []),
    "education": user_data.get("education", []),
    "languages": user_data.get("languages", []),
    "certifications": user_data.get("certifications", []),
    "skills": ip_json.get("skills", []),
    }
    final_data = process_resume_json(data)
    logger.info(final_data)
    return final_data


def has_quantitative_data(text: str) -> bool:
    """Check if a string contains numeric or percentage-based data."""
    #return bool(re.search(r'\d+[%$KkMm]|(?:\d+\s*(?:projects?|bugs?|users?|clients?|months?|years?|tasks?))', text, re.IGNORECASE))
    return bool(re.search(r'\d+', text))



def choose_metric_by_keyword(text: str) -> str:
    """Choose a metric based on the presence of specific keywords."""
    lower_text = text.lower()
    if "client" in lower_text or "user" in lower_text:
        return "Increased client satisfaction by 20%."
    else:
        # default fallback
        return "Increased accuracy by 15%."


def inject_metrics(description_list: List[str]) -> List[str]:
    """Inject a quantitative metric if none exist in the description."""
    if not any(has_quantitative_data(desc) for desc in description_list):
        combined_text = " ".join(description_list)
        metric = choose_metric_by_keyword(combined_text)
        description_list.append(metric)
    return description_list


def process_resume_json(resume_data: Dict) -> Dict:
    """Process the resume JSON to ensure every description has quantitative data."""
    for section in ["work_experience", "projects"]:
        if section in resume_data:
            for entry in resume_data[section]:
                if "description" in entry and isinstance(entry["description"], list):
                    entry["description"] = inject_metrics(entry["description"])
    return resume_data
