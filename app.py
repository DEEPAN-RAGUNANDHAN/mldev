import os
import json
import tempfile
import logging
import traceback
from datetime import datetime
from pathlib import Path
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import threading

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from dotenv import load_dotenv

# ------------------- Internal imports -------------------
from openai_process.prompt import build_cover_letter_prompt, build_resume_prompt, translate_prompt
from openai_process.openai_service import generate_text
from openai_process.search_google import google_search
from openai_process.job_research_generator import generate_guide
from process.cl_post_process import format_data
from process.cv_post_process import filter_skills
from process.preprocess import process_data
from process.summarizer import summarize_text
from process.job_research_process import fix_json, change_json
from extraction.resume_data_extraction import OpenAIResumeParser
from extraction.web_extractor import extract_page_text

# ------------------- Load ENV -------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------- App Config -------------------
app = FastAPI(title="MLDev Unified API Service")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=15)
request_queue = Queue()

# ------------------- Auth -------------------
def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ")[1]
    if token != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")

# ------------------- Queue Worker -------------------
def worker():
    while True:
        func, args = request_queue.get()
        try:
            func(*args)
        finally:
            request_queue.task_done()

threading.Thread(target=worker, daemon=True).start()

# ============================================================
# ------------------- JOB PARSE ------------------------------
# ============================================================

from typing import Union, List
from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime

# ---------- INPUT STRUCT ----------
class JobRequest(BaseModel):
    job_id: Union[str, int]              # allow string or number
    company: Union[str, dict]            # handle dict or str
    job_title: Union[str, dict]
    link: Union[str, dict]
    description: Union[str, dict]        # sometimes dict input

# ---------- OUTPUT STRUCT ----------
class Job(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    posted_date: str
    link: str
    processed: bool
    source: str
    job_description: str
    job_type: str
    skills: str
    job_link: str
    selected_count: int
    job_language: str
    job_title: str


@app.post("/m2/job/parse")   # ✅ fixed endpoint
async def parse_job(req: JobRequest, authorization: str = Header(...)):
    # Auth
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ")[1]
    if token != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")

    try:
        # ✅ Ensure fields are strings
        job_id = str(req.job_id)
        company = req.company if isinstance(req.company, str) else json.dumps(req.company)
        job_title = req.job_title if isinstance(req.job_title, str) else json.dumps(req.job_title)
        link = req.link if isinstance(req.link, str) else json.dumps(req.link)
        description = req.description if isinstance(req.description, str) else json.dumps(req.description)

        desc_lower = description.lower()

        # Detect job type
        if "full-time" in desc_lower:
            job_type = "Full-time"
        elif "part-time" in desc_lower:
            job_type = "Part-time"
        elif "intern" in desc_lower:
            job_type = "Internship"
        else:
            job_type = "Other"

        # Detect skills
        skills_detected = []
        for skill in ["python", "sql", "java", "c++", "javascript", "cloud", "machine learning"]:
            if skill in desc_lower:
                skills_detected.append(skill.capitalize())
        skills = ", ".join(skills_detected) if skills_detected else "General Skills"

        # Detect language
        job_language = "English" if "english" in desc_lower else "Unknown"

        # Build Response
        job = Job(
            job_id=job_id,
            title=job_title,
            company=company,
            location="Unknown",
            posted_date=datetime.today().strftime("%Y-%m-%d"),
            link=link,
            processed=True,
            source="API",
            job_description=description,
            job_type=job_type,
            skills=skills,
            job_link=link,
            selected_count=0,
            job_language=job_language,
            job_title=job_title
        )
        return JSONResponse(content=job.dict())

    except Exception as e:
        logger.error(f"🔥 ERROR in parse_job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ============================================================
# ------------------- RESUME + COVERLETTER -------------------
# ============================================================

@app.get("/")
def home():
    return {"message": "MLDev Unified API is running!"}

@app.post("/m2/generate/coverletter")
async def generate_coverletter(request: Request, _: None = Depends(verify_token)):
    data = await request.json()

    # ✅ get language & level from request
    cl_lang = data.get("cl_data", {}).get("language", "english").lower()
    cl_level = data.get("cl_data", {}).get("level", "B1")

    # ✅ tell prompt builder to generate directly in that language
    prompt_content = build_cover_letter_prompt(data, language=cl_lang, level=cl_level)
    result = {}

    def task():
        try:
            result["content"] = generate_text(prompt_content, OPENAI_API_KEY)
        except Exception as e:
            result["error"] = str(e)

    request_queue.put((task, []))
    request_queue.join()

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    paragraphs = result["content"].split("\n\n")
    data["paragraphs"] = paragraphs
    final_data = format_data(data)

    # ✅ remove translation step, because generation already in correct language
    return JSONResponse(final_data)


@app.post("/m2/generate/resume")
async def generate_resume(request: Request, _: None = Depends(verify_token)):
    ip_data = await request.json()
    data = process_data(ip_data)
    
    # Extract the requested language and level from the input data.
    # Default to English and B1 if not provided.
    cv_data = data.get('cv_data', {})
    cv_lang = cv_data.get('language', 'english').lower()
    cv_level = cv_data.get('level', 'A1')

    prompt_content = build_resume_prompt(data)
    result = {}

    def task():
        try:
            result["content"] = generate_text(prompt_content, OPENAI_API_KEY)
        except Exception as e:
            result["error"] = str(e)

    request_queue.put((task, []))
    request_queue.join()
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    try:
        parsed_content = json.loads(result["content"])
    except json.JSONDecodeError:
        return JSONResponse(status_code=500, content={"error": "Failed to parse AI response", "raw": result["content"]})

    # Post-process the resume to filter skills. This step runs regardless of language.
    filtered_data = filter_skills(parsed_content, data['user_details'], data['job_description'])

    # If the requested language is German, translate the entire JSON object.
    if cv_lang == "german":
        try:
            translation_prompt = translate_prompt(filtered_data, "German", cv_level)
            translated_content = generate_text(translation_prompt, OPENAI_API_KEY)
            translated_json = json.loads(translated_content)
            return JSONResponse(translated_json)
        except Exception as e:
            logger.error(f"Failed to translate resume to German: {str(e)}")
            # Return the original English version as a fallback
            return JSONResponse(filtered_data)
            
    return JSONResponse(filtered_data)

@app.post("/m2/generate/job-research")
async def generate_guide_endpoint(request: Request, _: None = Depends(verify_token)):
    data = await request.json()
    required_fields = ["company", "job_title", "candidate_profile", "job_description"]
    if not all(data.get(field) for field in required_fields):
        raise HTTPException(status_code=400, detail="Missing required fields")

    job_link1 = data.get("job_link")
    job_link2 = data["job_description"].get("link") if isinstance(data["job_description"], dict) else None
    company, job_title, candidate_profile, job_description = (
        data["company"], data["job_title"], data["candidate_profile"], data["job_description"]
    )

    web_info = ""
    if job_link1:
        web_info += extract_page_text(job_link1)
    if job_link2:
        web_info += extract_page_text(job_link2)
    if not web_info:
        web_info = google_search(f"{company} {job_title}")

    summarized_text = summarize_text(web_info)
    guide = generate_guide(company, job_title, candidate_profile, job_description, summarized_text)

    try:
        json_guide = json.loads(guide)
    except Exception:
        json_guide = fix_json(guide)

    final_output = change_json(json_guide)
    return JSONResponse(content=jsonable_encoder(final_output))
# ============================================================
# ------------------- COVER LETTER MATCH SCORE ---------------
# ============================================================

def calculate_match_score(user_details, job_description):

    try:
        # Validate user fields (but default missing ones to empty list instead of raising)
        required_user_fields = ["skills", "tools", "experience_summary", "education"]
        for field in required_user_fields:
            if field not in user_details:
                user_details[field] = []

        # Collect user info
        user_text = " ".join(
            user_details.get("skills", []) +
            user_details.get("tools", []) +
            user_details.get("experience_summary", []) +
            user_details.get("education", [])
        )

        # Collect job info - fallback to description if all three are empty
        job_text = " ".join(
            job_description.get("skills", []) +
            job_description.get("qualifications", []) +
            job_description.get("responsibilities", [])
        )
        if not job_text.strip():
            job_text = job_description.get("description", "")

        # Normalize words
        user_words = set(user_text.lower().replace(",", "").split())
        job_words = set(job_text.lower().replace(",", "").split())

        if not job_words:
            logger.warning("No job words found; returning base score 50")
            return 50  # fallback default score

        overlap = user_words.intersection(job_words)
        score = int((len(overlap) / len(job_words)) * 100)

        # Force score range 50–65
        score = max(50, min(score, 65))
        return score

    except Exception as e:
        logger.error(f"Error in calculate_match_score: {str(e)}")
        return 50  # fallback safe score



# ============================================================
# ------------------- EXTERNAL JOB API -----------------------
# ============================================================

from pydantic import BaseModel
from typing import Optional

class ExternalJobRequest(BaseModel):
    user_details: dict
    job_description: dict
    cl_data: Optional[dict] = None


@app.post("/external/job-api")
async def external_job_api(req: ExternalJobRequest, _: None = Depends(verify_token)):
    try:
        # Validate top-level fields
        if not req.user_details:
            raise HTTPException(status_code=400, detail="Missing user_details")
        if not req.job_description:
            raise HTTPException(status_code=400, detail="Missing job_description")

        job_desc = req.job_description
        if "description" not in job_desc or not job_desc["description"]:
            raise HTTPException(status_code=400, detail="Missing or empty job_description.description")

        desc_lower = job_desc["description"].lower()

        # Detect job type
        if "full-time" in desc_lower:
            job_type = "Full-time"
        elif "part-time" in desc_lower:
            job_type = "Part-time"
        elif "intern" in desc_lower:
            job_type = "Internship"
        else:
            job_type = "Remote"

        
        job_language = "English" if "english" in desc_lower else "English"

        # Build Job object safely
        try:
            job = Job(
                job_id=job_desc.get("job_id", "N/A"),
                title=job_desc.get("job_title", "Unknown"),
                company=job_desc.get("company", "Unknown"),
                location=job_desc.get("location", "Unknown"),
                posted_date=datetime.today().strftime("%Y-%m-%d"),
                link=job_desc.get("link", ""),
                processed=True,
                source="External API",
                job_description=job_desc.get("description", ""),
                job_type=job_type,
                skills=", ".join(job_desc.get("skills", [])) if job_desc.get("skills") else  "Communication, Teamwork, Problem-solving, Adaptability, Time Management, "
           "Leadership, Critical Thinking, Creativity, Collaboration, Interpersonal Skills, "
           "Analytical Thinking, Decision Making, Project Management, Organizational Skills, "
           "Attention to Detail",
                job_link=job_desc.get("link", ""),
                selected_count=0,
                job_language=job_language,
                job_title=job_desc.get("job_title", "Unknown")
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or missing job fields: {str(e)}")

        # Calculate match score
        match_score = calculate_match_score(req.user_details, job_desc)

        return JSONResponse(content={
            "job": job.dict(),
            "match_score": match_score
        })


    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f"Unexpected error in external_job_api: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process external job API: {str(e)}")
