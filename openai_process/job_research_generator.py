import os
from openai import OpenAI
from dotenv import load_dotenv
from openai_process.prompt import job_research_prompt

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_guide(company, job_title, profile, job_details, context):
    prompt = job_research_prompt(company, job_title, profile, job_details, context)
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        #max_tokens=1500
    )
    return response.choices[0].message.content