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
    user_keys = ["designation", "tools", "skills", "experience_summary", "past_projects"]
    job_keys = ["job_title", "link", "description", "responsibilities", "qualifications", "skills"]

    required_data = {
    "user_details": {k: data["user_details"][k] for k in user_keys if k in data["user_details"]},
    "job_description": {k: data["job_description"][k] for k in job_keys if k in data["job_description"]}
    }
    return f"""Generate structured JSON content for a professional resume based on the following user details and job description. Do not include company names. Don't include the word Resume in it. Give terms instead of sentences for skills and arrange them based on job requirement. Don't include any skills that is not present in user data.
Return past projects and experience summary data only if there is data for that in the input. Otherwise leave it blank.
Avoid repeating verbs or phrases (e.g., "developed", "implemented", "responsible for") more than twice in total. Use a wide vocabulary — apply varied, precise action verbs and phrasing throughout. Each entry must use a **unique set of verbs** and sentence structure.
Every experience description must contain **three quantitative metrics**, even if not provided in the input. Always include 3 different, realistic, inferred quantitative metrics in every description entry, even if the input lacks numbers. These must be embedded naturally in each bullet point.

For example:
- “Led a team of 6 engineers and increased processing speed by 35%.”
- “Managed budgets up to $150K across 3 projects in 12 months.”
- “Reduced bug count by 42% through automation.”
- “Increased accuracy by 10%.”

Use **different metrics** each time — avoid repeating the same phrasing or numbers across entries but include it for sure.
Return a valid JSON with the following structure:
{{
  "summary": "...",
  "experience_summary": [
    {{
      "company_name": "...",
      "location": "...",
      "position": "...",
      "period": "...",
      "description": ["...","..."]
    }},
    ...
  ],
  "past_projects": [
    {{
      "project_name": "..."
      "company_name": "...",
      "period": "...",
      "skills_used": "..."
      "description": ["...","..."]
    }},
    ...
  ],
  "skills": ["...", "..."]
}}

The description for each experience_summary and project must be atleast 3-4 points with 70-80 words and the summary must be atleast 80 words relevant to the applying job. Ensure that each experience entry has a real company name (if provided in input), otherwise leave it blank. Make sure each field is properly filled based on the user input below. Do NOT return markdown or any additional explanation.
Generate everything in US English.
Details:
{required_data}"""



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
