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
import asyncio

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

@app.get("/")
def home():
    return {"message": "MLDev Unified API is running!"}

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


@app.post("/m2/job/parse")   
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
            job_type = "Remote"

        # Detect skills
        skills_detected = []
        for skill in ["python", "sql", "java", "c++", "javascript", "cloud", "machine learning"]:
            if skill in desc_lower:
                skills_detected.append(skill.capitalize())
        skills = ", ".join(skills_detected) if skills_detected else "Communication, Teamwork, Problem-solving, Adaptability, Time Management, Leadership, Critical Thinking, Creativity, Collaboration, Interpersonal Skills, ""Analytical Thinking, Decision Making, Project Management, Organizational Skills, Attention to Detail"        # Detect language
        job_language = "English" if "english" in desc_lower else "English"

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
@app.post("/m2/generate/coverletter")
async def generate_coverletter(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_token)):
    data = await request.json()
    prompt_content = build_cover_letter_prompt(data)
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
    if data["cl_data"]["language"].lower()!="english":
        level = data["cl_data"].get("level", "B1")
        prompt = translate_prompt(final_data, data["cl_data"]["language"], level)
        def task():
            try:
                result["content"] = generate_text(prompt, OPENAI_API_KEY)
            except Exception as e:
                result["error"] = str(e)

        request_queue.put((task, []))
        request_queue.join()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        try:
            final_data = json.loads(result["content"])
        except json.JSONDecodeError:
            return JSONResponse(status_code=500, content={
                "error": "Failed to parse response as JSON",
                "raw": result["content"]
            })

    return JSONResponse(final_data)
@app.post("/m2/generate/resume")
async def generate_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_token)
):
    ip_data = await request.json()
    data = process_data(ip_data)
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
        return JSONResponse(status_code=500, content={
            "error": "Failed to parse response as JSON",
            "raw": result["content"]
        })

    # Filter skills from parsed_content
    filtered_data = filter_skills(parsed_content, data['user_details'], data['job_description'])

    if data["cv_data"]["language"].lower()!="english":
        ip_level = data["cv_data"].get("level", "B1-B2")
        if ip_level.lower() in ["basic", "beginner", "elementary", "a1", "a2"]:
            level = "A1-A2"
        elif ip_level.lower() in ["fluent", "proficient", "advanced", "native", "c1", "c2"]:
            level = "C1-C2"
        else:
            level = "B1-B2"
        prompt = translate_prompt(filtered_data, data["cv_data"]["language"], level)
        def task():
            try:
                result["content"] = generate_text(prompt, OPENAI_API_KEY)
            except Exception as e:
                result["error"] = str(e)

        request_queue.put((task, []))
        request_queue.join()

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        try:
            filtered_data = json.loads(result["content"])
        except json.JSONDecodeError:
            return JSONResponse(status_code=500, content={
                "error": "Failed to parse response as JSON",
                "raw": result["content"]
            })

    return JSONResponse(filtered_data)

@app.post("/m2/generate/job-research")
async def generate_guide_endpoint(request: Request):
    # if not request.company or not request.job_title or not request.candidate_profile or not request.job_description:
    #     raise HTTPException(status_code=400, detail="Missing required fields")

    data = await request.json()

    required_fields = ["company", "job_title", "candidate_profile", "job_description"]
    if not all(data.get(field) for field in required_fields):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # job_link1 = request.job_link  # <- passed in request
    # job_link2 = request.job_description["link"]

    job_link1 = data.get("job_link")  # passed directly
    job_link2 = data["job_description"].get("link") if isinstance(data["job_description"], dict) else None

    company = data["company"]
    job_title = data["job_title"]
    candidate_profile = data["candidate_profile"]
    job_description = data["job_description"]
    if job_link1 or job_link2:
        web_info = ""
        if job_link1:
            web_info = extract_page_text(job_link1)
        if job_link2:
            web_info = web_info + extract_page_text(job_link2)
    else:
        query = f"{company} {job_title}"
        web_info = google_search(query)

    # query = f"{request.company} {request.job_title}"
    # web_info = google_search(query)
    summarized_text = summarize_text(web_info)
    logger.info(f"Summary: {summarized_text}")
    #return summarized_text

    #profile_str = pprint.pformat(request.candidate_profile, indent=2)

    guide = generate_guide(company, job_title, candidate_profile, job_description, summarized_text)
    logger.info(f"GUIDE {guide}")

    try:
        json_guide = json.loads(guide)  # Ensure it's valid JSON
    except Exception:
        json_guide = fix_json(guide)
        logger.info("Error")

    logger.info(f"\n\n{json_guide}")

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
#----------------------------------------------------------------------#
#----------------------------------------------------------------------#
@app.post("/m2/extract-resume")
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    _: None = Depends(verify_token)):
    """
    Parse a resume file and extract structured information
    
    Accepts: PDF, DOCX, TXT files
    Returns: JSON with parsed resume data
    """
    #resume_parser = ResumeExtractor()
    resume_parser = OpenAIResumeParser()
    if not resume_parser:
        raise HTTPException(status_code=500, detail="Resume parser not initialized")
    
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.txt'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file_extension}. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (e.g., 10MB limit)
    max_file_size = 10 * 1024 * 1024  # 10MB
    if file.size and file.size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size allowed: {max_file_size // (1024*1024)}MB"
        )
    
    try:
        # Create a temporary file to save the uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            # Read and save the uploaded file
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing file: {file.filename} (size: {len(content)} bytes)")
        
        # Parse the resume
        #result = resume_parser.extract_resume_data(temp_file_path)
        result = resume_parser.parse_resume(temp_file_path)
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Check if parsing was successful
        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])
        
        logger.info(f"Successfully parsed resume: {file.filename}")
        
        return JSONResponse(content={"data": result})
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Clean up temp file if it exists
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass
        
        logger.error(f"Error parsing resume {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume: {str(e)}"
        )

@app.exception_handler(413)
async def request_entity_too_large_handler(request, exc):
    """Handle file too large errors"""
    return JSONResponse(
        status_code=413,
        content={
            "success": False,
            "error": "File too large",
            "message": "The uploaded file exceeds the maximum allowed size of 10MB"
        }
    )
# ==============================
# TEXT REWRITE (REGENERATION) API
# ==============================
@app.post("/m2/generate/rewrite")
async def rewrite_text(request: Request, _: None = Depends(verify_token)):
    try:
        payload = await request.json()
        prompt_instruction = payload.get("prompt", "Rewrite this professionally.")
        input_text = payload.get("input", "")
        support_text = payload.get("support", "")
        memory = payload.get("memory", "")

        final_prompt = (
            f"Instruction: {prompt_instruction}.\n"
            f"Context: {support_text}.\n"
            f"Memory Tag: {memory}.\n"
            'Rewrite this input text in a professional tone under 20 words:\n'
            f'"{input_text}"\n\n'
            "Return only the rewritten sentence, no extra commentary."
        )

        # Using asyncio.to_thread to run blocking generate_text function asynchronously
        rewritten_text = await asyncio.to_thread(generate_text, final_prompt, OPENAI_API_KEY)

        if not rewritten_text:
            raise HTTPException(status_code=500, detail="Failed to generate rewritten text")

        return JSONResponse({"rewritten_text": rewritten_text.strip()})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))