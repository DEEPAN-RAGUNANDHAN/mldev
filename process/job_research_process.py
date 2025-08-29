import json
import re

def fix_json(gpt_output: str):
    # Strip markdown formatting or extra braces
    text = gpt_output.strip().strip("```json").strip("```").strip()
    text = text.replace("{{", "{").replace("}}", "}")

    # Step 1: Fix missing commas between adjacent "key": "value" lines
    text = re.sub(
        r'"(":[^"]*?")\s*\n\s*(")',  # matches: "value"\n"key"
        r'\1,\n\2',
        text
    )

    text = re.sub(
        r'(".*?")\s*(")',  # string directly followed by another string, even without newline
        r'\1,\n\2',
        text
    )

    text = re.sub(
        r'(")(\s*)(")',  # match: string" string"
        r'\1,\2\3',
        text
    )

    # Step 2: Fix missing commas between string and object
    text = re.sub(
        r'"(":[^"]*?")\s*\n\s*({)',  # matches: "value"\n{
        r'\1,\n\2',
        text
    )

    text = re.sub(
        r'":\s*(".*?")\s*\n\s*(")',  # matches: "value"\n"next_key"
        r'\1,\n\2',
        text
    )

    # Step 3: Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Step 6: Attempt to parse
    print(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print("❌ Failed to parse JSON after cleanup:", e)
        return None

def change_json(raw_data):
    processed_data = {
        "about_company": {
            "company_overview": raw_data["About the company"]["Company Overview"],
            "values": raw_data["About the company"]["Values"],
            "projects_and_work": raw_data["About the company"]["Projects and work (of the company)"],
            "recent_activities": raw_data["About the company"]["Recent Activities"],
        },
        "job_role": {
            "role_details": raw_data["Job role"]["Role details"],
            "responsibilities": raw_data["Job role"]["Responsibilities"],
            "qualifications": raw_data["Job role"]["Qualifications"],
            "benefits": raw_data["Job role"]["Benefits"],
        },
        "background_and_skills": {
            "key_skills": raw_data["Background and Skills"]["Key skills"],
            "aligning_skills_with_role": raw_data["Background and Skills"]["Aligning skills with the role"],
            "example_scenarios": raw_data["Background and Skills"]["Example scenarios (of how each skill is relevant)"]
        },
        "why_user_is_interested": raw_data["Why the user is interested in the position"],
        "what_user_brings": raw_data["What the user brings to the company"],
        "interview_preparation_strategies": {
            "research_tips": raw_data["Interview preparation strategies"]["Research tips"],
            "practice_interview_questions": raw_data["Interview preparation strategies"]["Practice Interview Questions"],
            "questions_to_ask_interviewer": raw_data["Interview preparation strategies"]["Questions to Ask the Interviewer"],
        }
    }

    print(json.dumps(processed_data, indent=2))

    return processed_data