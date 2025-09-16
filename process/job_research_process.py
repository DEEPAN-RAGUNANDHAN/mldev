import json
import re

# ... (fix_json function remains the same)

def change_json(raw_data):
    # Use .get() with a default value to prevent KeyErrors
    about_company = raw_data.get("About the company", {})
    job_role = raw_data.get("Job role", {})
    background_and_skills = raw_data.get("Background and Skills", {})
    interview_strategies = raw_data.get("Interview preparation strategies", {})

    processed_data = {
        "about_company": {
            "company_overview": about_company.get("Company Overview", "N/A"),
            "values": about_company.get("Values", []),
            "projects_and_work": about_company.get("Projects and work (of the company)", []),
            "recent_activities": about_company.get("Recent Activities", []),
        },
        "job_role": {
            "role_details": job_role.get("Role details", []),
            "responsibilities": job_role.get("Responsibilities", []),
            "qualifications": job_role.get("Qualifications", []),
            "benefits": job_role.get("Benefits", []),
        },
        "background_and_skills": {
            "key_skills": background_and_skills.get("Key skills", []),
            "aligning_skills_with_role": background_and_skills.get("Aligning skills with the role", []),
            "example_scenarios": background_and_skills.get("Example scenarios (of how each skill is relevant)", "N/A")
        },
        "why_user_is_interested": raw_data.get("Why the user is interested in the position", "N/A"),
        "what_user_brings": raw_data.get("What the user brings to the company", "N/A"),
        "interview_preparation_strategies": {
            "research_tips": interview_strategies.get("Research tips", []),
            "practice_interview_questions": interview_strategies.get("Practice Interview Questions", []),
            "questions_to_ask_interviewer": interview_strategies.get("Questions to Ask the Interviewer", []),
        }
    }


    print(json.dumps(processed_data, indent=2))

    return processed_data