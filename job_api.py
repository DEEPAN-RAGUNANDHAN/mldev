import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
import traceback

# Load env file
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI(title="Job API Service")

# ---------------------------
# Input Schema
# ---------------------------
class JobRequest(BaseModel):
    job_id: str
    company: str
    job_title: str
    link: str
    description: str

# ---------------------------
# Output Schema
# ---------------------------
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

# ---------------------------
# Endpoint
# ---------------------------
@app.post("/job/parse")
async def parse_job(req: JobRequest, authorization: str = Header(...)):
    # ---------------- Auth ----------------
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ")[1]
    if token != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key")

    try:
        # Detect job type
        desc_lower = req.description.lower()
        if "full-time" in desc_lower:
            job_type = "Full-time"
        elif "part-time" in desc_lower:
            job_type = "Part-time"
        elif "intern" in desc_lower:
            job_type = "Internship"
        else:
            job_type = "Other"

        # Detect skills (simple extraction)
        skills_detected = []
        for skill in ["python", "sql", "java", "c++", "javascript", "cloud", "machine learning"]:
            if skill in desc_lower:
                skills_detected.append(skill.capitalize())
        skills = ", ".join(skills_detected) if skills_detected else "General Skills"

        # Detect language
        job_language = "English" if "english" in desc_lower else "Unknown"

        # ---------------- Build Response ----------------
        job = Job(
            job_id=req.job_id,
            title=req.job_title,
            company=req.company,
            location="Unknown",  # Default (can be parsed if description contains location)
            posted_date=datetime.today().strftime("%Y-%m-%d"),
            link=req.link,
            processed=True,
            source="API",
            job_description=req.description,
            job_type=job_type,
            skills=skills,
            job_link=req.link,
            selected_count=0,
            job_language=job_language,
            job_title=req.job_title
        )

        return JSONResponse(content=job.dict())

    except Exception as e:
        print("🔥 ERROR:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")
