from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from openai_process.prompt import build_cover_letter_prompt, build_resume_prompt, translate_prompt
from openai_process.openai_service import generate_text
from openai_process.search_google import google_search
from openai_process.job_research_generator import generate_guide
from process.cl_post_process import format_data
from process.cv_post_process import filter_skills
from process.preprocess import process_data
from process.summarizer import summarize_text
from process.job_research_process import fix_json, change_json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
#from extraction.resume_data_extraction import ResumeExtractor
from extraction.resume_data_extraction import OpenAIResumeParser
from extraction.web_extractor import extract_page_text
import tempfile
import threading
import os
import json
import logging

load_dotenv()
print("CPU Count:", os.cpu_count())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Resume and Cover Letter Generator")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_TOKEN = os.getenv("SECRET_KEY")

executor = ThreadPoolExecutor(max_workers=15)
request_queue = Queue()

# ---------------------- Auth Dependency ----------------------

def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------------------- Queue Worker ----------------------

def worker():
    while True:
        func, args = request_queue.get()
        try:
            func(*args)
        finally:
            request_queue.task_done()

threading.Thread(target=worker, daemon=True).start()

# ---------------------- Routes ----------------------

@app.get("/")
def home():
    return {"message": "Resume and Cover Letter Generator (Text Mode) is running!"}

@app.post("/m2/generate/coverletter")
async def generate_coverletter(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_token)
):
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
            raise HTTPException(status_code=500, processdetail=result["error"])
        
        try:
            filtered_data = json.loads(result["content"])
        except json.JSONDecodeError:
            return JSONResponse(status_code=500, content={
                "error": "Failed to parse response as JSON",
                "raw": result["content"]
            })

    return JSONResponse(filtered_data)

#----------------------new----------------------------

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