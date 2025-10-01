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
    user_keys = ["name", "designation", "contact", "email", "address", "tools", "skills", "experience_summary", "past_projects"]

    required_data = {
        "job_description": {k: data["job_description"][k] for k in job_keys if k in data["job_description"]},
        "user_details": {k: data["user_details"][k] for k in user_keys if k in data.get("user_details", {})}
    }

    return f"""
You are an expert AI resume writer. Generate a structured JSON resume tailored mainly to the job description below. 
Use user details if available, but **prioritize the job description** when filling content.

### Rules:
- Output must be **valid JSON only** (no markdown, no explanations).
- Include real company names if provided in input. If none, leave blank.
- Summary must be at least 80 words, strongly aligned with the target job role.
- Every experience entry must contain **exactly 3–4 bullet points**, each 70–80 words long.
- Each bullet must include **3 unique quantitative metrics** (%, $, time, counts, scale, etc.), inferred realistically if not in input.
- Use varied, precise action verbs across entries. Avoid repeating the same verbs/phrases more than twice overall.
- Skills: Only include those present in job description and user input. Arrange them based on job relevance.
- Past projects and experience summary: Include only if present in input, else return as an empty list.
- Generate everything in **US English**.

### Required JSON structure:
{{
  "summary": "...",
  "experience_summary": [
    {{
      "company_name": "...",
      "location": "...",
      "position": "...",
      "period": "...",
      "description": ["...", "...", "..."]
    }}
  ],
  "past_projects": [
    {{
      "project_name": "...",
      "company_name": "...",
      "period": "...",
      "skills_used": "...",
      "description": ["...", "...", "..."]
    }}
  ],
  "skills": ["...", "...", "..."]
}}

### Input Data:
{required_data}
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
