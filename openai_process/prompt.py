import json

import json

def build_cover_letter_prompt(data):
    job_title = data["job_description"].get("job_title", "")

    return f"""Compose a truly uplifting and captivating body—within 150 words—structured as 2 evocative paragraphs suited for a formal cover letter.
Omit all greetings, headings, and company names.
Refrain from listing skills, technical details, past projects, or explicit prior experience.
Deliver an inspiring tone that radiates purpose, optimism, and genuine enthusiasm for the opportunity, positioning the candidate as an exceptional match in terms of values, culture, and growth ambitions.
Give each sentence unique energy—never begin all sentences the same way—and use vivid, persuasive language reflecting the candidate’s vision and alignment with the role.
Highlight authentic motivation, a strong sense of contribution, and a future-focused spirit, making the reader want to learn more.
The essence should reflect character, drive, and readiness to embrace new challenges rather than just technical fit.

Job Title:
{job_title}

Return only plain text for .docx generation (no file, no markdown)."""

def build_resume_prompt(data):
    job_keys = ["job_title", "link", "description", "responsibilities", "qualifications", "skills"]
    # Minimal user keys, only if required
    user_keys = []

    required_data = {
        "job_description": {k: data["job_description"][k] for k in job_keys if k in data["job_description"]},
        "user_details": {k: data["user_details"][k] for k in user_keys if k in data.get("user_details", {})}
    }

    return f"""
You are an expert AI resume writer. Using the **following job description as primary guidance**, generate a structured JSON resume that fully aligns with the position and its requirements. 
Only use user details if absolutely required to fill missing fields (e.g., name). Otherwise, base every section—summary, experience, projects, skills—on the job description and its key terms.



### Rules:
- Output must be **valid JSON only** (no markdown, no explanations).
- Each experience and project entry: 3-4 bullet points, 70-80 words per bullet, each having 3 *unique* inferred or provided quantitative metrics.
- Do not fabricate skills that are not in the job description. Skills must be prioritized and based on job requirements.
- Do not include company names sourced from user details.
- Summary must be at least 80 words, strongly aligned to the target job role ("{data['job_description'].get('job_title', '')}").
- Past projects and experience summary: include only if there is explicit data in user details. Otherwise, return as an empty list.
- Use varied action verbs and realistic, contextually appropriate metrics.
- Use US English only.


### Required JSON Structure:
{{
  "summary": "...",
  "experience_summary": [...],
  "past_projects": [...],
  "skills": [...]
}}


### Input Data:
{required_data}
"""



def translate_prompt(data, target_lang, level):
    return f"""
Translate the following JSON into {target_lang}. The content must be in {level} level of the specified language.
Only translate the values — do not change the keys or the JSON structure. 
Return the translated content as valid JSON in the same format.

{json.dumps(data, indent=2)}
"""

def job_research_prompt(company, job_title, profile,job_details, web_content):
    return f"""
You are an expert AI assistant helping a candidate prepare for an interview.

Company: {company}
Job Title: {job_title}
Candidate Profile: {profile}
Job details: {job_details}

Here is some real-time information about the company and role:
{web_content[:3000]}

Your task is to generate a JSON interview preparation guide in the following format:

{{
  "About the company": {{
    "Company Overview": "...",
    "Values": ["...", "...", "...", "...", "..."],
    "Projects and work (of the company)": [
      {{"project": "Project Name", "description": "150-word explanation"}}
    ],
    "Recent Activities": ["...", "...", "...", "...", "..."]
  }},
  "Job role": {{
    "Role details": ["...", "...", "...", "...", "..."],
    "Responsibilities": ["...", "...", "...", "...", "..."],
    "Qualifications": ["...", "...", "...", "...", "..."],
    "Benefits": ["...", "...", "...", "...", "..."]
  }},
  "Background and Skills": {{
    "Key skills": ["...", "...", "...", "...", "..."],
    "Aligning skills with the role": ["...", "...", "...", "...", "..."],
    "Example scenarios (of how each skill is relevant)": "..."
  }},
  "Why the user is interested in the position": "...",
  "What the user brings to the company": "...",
  "Interview preparation strategies": {{
    "Research tips": ["...", "...", "...", "...", "..."],
    "Practice Interview Questions": [
      {{"ques": "Question 1", "ans": "150-word answer"}},
      ...
    ],
    "Questions to Ask the Interviewer": ["...", "...", "...", "...", "..."]
  }}
}}

Guidelines:
- Fill **every field completely** — no empty or unfinished strings or blank lists.
- Each list must contain atleast 5 values.
- **Each bullet/item must contain at least 150 words** unless it's a question.
- Tailor all answers using only the company/job description — do not guess based on the candidate.
- Respond with **only the raw JSON**, no markdown or comments.
"""
