import os
import json
import re
from typing import Dict, List, Any, Optional
import PyPDF2
import docx
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ResumeParserConfig:
    """Configuration class to easily modify JSON output format"""
    
    @staticmethod
    def get_json_schema():
        """Define the required JSON output format - easily modifiable"""
        return {
            "first_name": "string",
            "second_name": "string",
            "email": "string",
            "phone": "string",
            "linkedin": "string",
            "country": "string",
            "state": "string",
            "city": "string",
            "links": [{
                "type": "string",
                "url": "string"
            }],
            "work_experience": [
                {
                    "job_title": "string",
                    "company_name": "string",
                    "location": "string",
                    "start_date": "string",
                    "end_date": "string",
                    "currentwork": "true/false",
                    "key_responsibilities": "string"
                }
            ],
            "education": [
                {
                    "institution": "string",
                    "city": "string",
                    "field_of_study": "string",
                    "start_date": "string",
                    "end_date": "string",
                    "current_study": "true/false",
                    "description": "string"
                }
            ],
            "projects": [
                {
                    "project_name": "string",
                    "institution": "string",
                    "start_date": "string",
                    "end_date": "string",
                    "currentdo": "true/false",
                    "project_description": "string"
                }
            ],
            "languages": [
                {
                    "language": "string",
                    "proficiency": "string"
                }
            ],
            "certifications": [
                {
                    "certificate_name": "string",
                    "platform": "string",
                    "start_date": "string",
                    "end_date": "string"
                }
            ],
            "primary_title": "string",
            "secondary_title": "string",
            "tertiary_title": "string",
            "general_skills": ["string"],
            "jobSpecificSkills": ["string"]
        }
    
    @staticmethod
    def get_parsing_prompt():
        """Get the prompt for AI parsing - easily modifiable"""
        schema = ResumeParserConfig.get_json_schema()
        return f"""You are a professional resume parser. Extract information from the provided resume text and return it in the exact JSON format specified below.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON, no additional text or explanation
2. If information is not available, use empty string "" for strings and empty array [] for arrays
3. Extract dates in a consistent format (e.g., "Jan 2020", "2020", "Present")
4. Be accurate and extract all available information
5. For skills, extract both technical and soft skills
6. For work experience, include all jobs mentioned
7. For projects, include both professional and personal projects
8. Do not include any markdown formatting or code blocks
9. Ensure the JSON is properly formatted and valid

Required JSON format:
{json.dumps(schema, indent=2)}

Resume text to parse:
"""

class TogetherResumeParser:
    def __init__(self, model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"):
        """
        Initialize the parser using TogetherAI's free LLaMA 3.3 model.
        """
        self.model = model
        api_key = os.getenv("TOGETHER_API_KEY") or ""
        if not api_key:
            raise Exception("Please set environment variable TOGETHER_API_KEY")
        self.api_key = api_key
        self.host = "https://api.together.xyz"
        self.timeout = 120

    def call_together_api(self, prompt: str, max_retries: int = 3) -> str:
        """Call TogetherAI chatcompletion endpoint, similar logic to Ollama one."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional resume parser."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(max_retries):
            try:
                logger.info(f"Calling TogetherAI API (attempt {attempt + 1}/{max_retries})")
                resp = requests.post(
                    f"{self.host}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"TogetherAI API error {resp.status_code}: {resp.text}")
                    if attempt == max_retries - 1:
                        raise Exception(f"API failed: {resp.text}")
            except requests.Timeout:
                logger.error(f"Attempt {attempt + 1} timed out")
                if attempt == max_retries - 1:
                    raise Exception("All requests to TogetherAI timed out")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
        raise Exception("Failed after retries")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            return ""
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading TXT: {e}")
            return ""
    
    def extract_text(self, file_path: str) -> str:
        """Extract text based on file extension"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            return self.extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

    def clean_json_response(self, response: str) -> str:
        # Same as before
        json_start = response.find('{')
        if json_start != -1:
            response = response[json_start:]
        json_end = response.rfind('}')
        if json_end != -1:
            response = response[:json_end + 1]
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*$', '', response)
        return response.strip()

    def validate_and_fix_json(self, json_str: str) -> Dict[str, Any]:
        # Same as before
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
            fixes = [
                (r',(\s*[}\]])', r'\1'),
                (r"'([^']*)':", r'"\1":'),
                (r'(\w+):', r'"\1":'),
                (r'\bNone\b', 'null'),
                (r'\bTrue\b', 'true'),
                (r'\bFalse\b', 'false')
            ]
            fixed = json_str
            for pat, repl in fixes:
                fixed = re.sub(pat, repl, fixed)
            return json.loads(fixed)

    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        try:
            text = self.extract_text(file_path)
            if not text:
                return {"error": "Could not extract text"}

            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... [truncated]"
                logger.warning("Text truncated")

            prompt = ResumeParserConfig.get_parsing_prompt() + "\n\n" + text
            logger.info("Sending prompt to TogetherAI...")
            ai_response = self.call_together_api(prompt)
            clean = self.clean_json_response(ai_response)
            parsed = self.validate_and_fix_json(clean)
            logger.info("Parsing successful")
            return parsed

        except Exception as e:
            logger.error(f"Parsing error: {e}")
            return {"error": str(e)}

# Example usage:
# def main():
#     parser = TogetherResumeParser()
#     file_path = "HariniResume.pdf"
#     result = parser.parse_resume(file_path)
#     print(json.dumps(result, indent=2, ensure_ascii=False))

# if __name__ == "__main__":
#     main()