import os
import json
import re
from typing import Dict, Any
import PyPDF2
import docx
import logging
from openai import OpenAI  # ✅ already replaced requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ResumeParserConfig:
    @staticmethod
    def get_json_schema():
        return {
            "first_name": "string",
            "second_name": "string",
            "email": "string",
            "phone": "string",
            "linkedin": "string",
            "country": "string",
            "state": "string",
            "city": "string",
            "links": [{"type": "string", "url": "string"}],
            "work_experience": [{
                "job_title": "string",
                "company_name": "string",
                "location": "string",
                "start_date": "string",
                "end_date": "string",
                "currentwork": "true/false",
                "key_responsibilities": "string"
            }],
            "education": [{
                "institution": "string",
                "city": "string",
                "field_of_study": "string",
                "start_date": "string",
                "end_date": "string",
                "current_study": "true/false",
                "description": "string"
            }],
            "projects": [{
                "project_name": "string",
                "institution": "string",
                "start_date": "string",
                "end_date": "string",
                "currentdo": "true/false",
                "project_description": "string"
            }],
            "languages": [{"language": "string", "proficiency": "string"}],
            "certifications": [{
                "certificate_name": "string",
                "platform": "string",
                "start_date": "string",
                "end_date": "string"
            }],
            "primary_title": "string",
            "secondary_title": "string",
            "tertiary_title": "string",
            "general_skills": ["string"],
            "jobSpecificSkills": ["string"]
        }

    @staticmethod
    def get_job_titles_list():
        """✅ pulled job_titles_list into a reusable function"""
        return [
            "Automation Engineer","Electrical Engineer","Control Systems Engineer","Electronics Engineer",
            "Automotive Engineer","Testing Engineer","Robotics Engineer","Industrial Engineer","HVAC Engineer",
            "Mechatronics Engineer","Embedded Systems Engineer","Telecommunications Engineer","Network Engineer",
            "Software Engineer","Cloud Engineer","DevOps Engineer","Systems Engineer","IT Systems Engineer",
            "Green Energy Engineer","Software Developer","Frontend Developer","Backend Developer",
            "Full Stack Developer","Mobile App Developer","Game Developer","Blockchain Developer",
            "Embedded Software Developer","Java Developer","Python Developer","C++ Developer",
            "Data Scientist","Data Engineer","Machine Learning Engineer","Data Analyst","AI/ML Engineer",
            "AI Research Scientist","Natural Language Processing Engineer","Big Data Engineer",
            "Computer Vision Engineer","AI Ethics Specialist","Data Architect","Healthcare IT Specialist",
            "Cybersecurity Specialist","Network Security Engineer","Penetration Tester","Security Analyst",
            "Cryptography Specialist","Information Security Manager","IT Security Specialist",
            "Project Manager","IT Project Manager","Agile Project Manager","Product Manager",
            "Digital Product Manager","Operations Manager","Supply Chain Manager","HR Manager",
            "Financial Manager","Risk Manager","Marketing Manager","Sales Manager","Business Development Manager",
            "Quality Assurance Manager","Customer Service Manager","Program Manager","Innovation Manager",
            "Business Analyst","Systems Analyst","Financial Analyst","Policy Analyst","IT Business Analyst"
        ]

    @staticmethod
    def get_parsing_prompt():
        schema = ResumeParserConfig.get_json_schema()
        job_titles_list = ResumeParserConfig.get_job_titles_list()

        return f"""You are a professional resume parser. Extract information from the provided resume text and return it in the exact JSON format below.

IMPORTANT:
- Return ONLY valid JSON
- Dates consistent ("Jan 2020", "Present")
- Extract ALL skills, jobs, projects
- For primary_title, secondary_title, tertiary_title → choose ONLY from this list:
{job_titles_list}
- These titles must NEVER be empty. Choose the best 3 matches based on the resume.
- general_skills and jobSpecificSkills must NEVER be empty. Fill with the most relevant ones.

Required JSON format:
{json.dumps(schema, indent=2)}

Resume text:
"""

class OpenAIResumeParser:
    def __init__(self, model="gpt-3.5-turbo"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("Please set OPENAI_API_KEY in your .env")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return ""

    def extract_text_from_docx(self, file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            return ""

    def extract_text_from_txt(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading TXT: {e}")
            return ""

    def extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif ext == ".docx":
            return self.extract_text_from_docx(file_path)
        elif ext == ".txt":
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file: {ext}")

    def clean_json_response(self, response: str) -> str:
        json_start = response.find("{")
        json_end = response.rfind("}")
        if json_start != -1 and json_end != -1:
            response = response[json_start:json_end+1]
        response = re.sub(r"```json\s*", "", response)
        response = re.sub(r"```$", "", response)
        return response.strip()

    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        text = self.extract_text(file_path)
        if not text:
            return {"error": "No text extracted"}

        if len(text) > 8000:
            text = text[:8000] + "\n... [truncated]"
            logger.warning("Text truncated")

        prompt = ResumeParserConfig.get_parsing_prompt() + text

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            ai_content = response.choices[0].message.content.strip()
            clean = self.clean_json_response(ai_content)

            try:
                parsed = json.loads(clean)
            except Exception as e:
                logger.error(f"JSON parsing failed, falling back to empty schema: {e}")
                parsed = {}

            schema = ResumeParserConfig.get_json_schema()
            final_output = {key: parsed.get(key, default) for key, default in schema.items()}

            # ✅ Correction step: enforce non-empty job titles & skills
            job_titles_list = ResumeParserConfig.get_job_titles_list()
            if (not final_output.get("primary_title") or final_output["primary_title"] in ["", "string"] or
                not final_output.get("secondary_title") or final_output["secondary_title"] in ["", "string"] or
                not final_output.get("tertiary_title") or final_output["tertiary_title"] in ["", "string"] or
                not final_output.get("general_skills") or final_output["general_skills"] == [] or
                not final_output.get("jobSpecificSkills") or final_output["jobSpecificSkills"] == []):

                correction_prompt = f"""
                Resume Text:
                {text}

                Please re-analyze and strictly ensure:
                - primary_title, secondary_title, tertiary_title are chosen ONLY from this list: {job_titles_list}
                - These titles MUST be the top 3 most relevant matches, never empty.
                - general_skills must contain at least 3 relevant soft skills.
                - jobSpecificSkills must contain at least 3 relevant technical/role-specific skills.
                Return only valid JSON in the same schema.
                """

                correction_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": correction_prompt}],
                    temperature=0
                )
                corrected = self.clean_json_response(correction_response.choices[0].message.content.strip())
                try:
                    corrected_json = json.loads(corrected)
                    final_output.update(corrected_json)
                except Exception as e:
                    logger.error(f"Correction step failed: {e}")

            return final_output

        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            return {"error": str(e)}
