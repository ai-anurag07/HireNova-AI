import os
import json
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

# Connect to Groq using your API key from the .env file
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def parse_resume_with_groq(raw_text: str) -> dict:
    """Sends the messy text to Groq (Llama 3) and gets back neat JSON."""
    
    prompt = """
    You are an expert HR AI. Extract the information from the following resume text and format it STRICTLY as a JSON object matching this schema:
    {
        "personal": {"name": "", "email": "", "phone": "", "linkedin": "", "github": "", "location": ""},
        "summary": "A 2-3 line professional summary",
        "education": [{"degree": "", "institution": "", "year": "", "gpa": ""}],
        "experience": [{"role": "", "company": "", "duration": "", "description": ["bullet 1", "bullet 2"]}],
        "projects": [{"name": "", "tech_stack": ["python", "sql"], "duration": "", "description": ["bullet 1", "bullet 2"]}],
        "skills": {"technical": [""], "tools": [""], "soft": [""]},
        "achievements": ["award 1", "award 2"]
    }
    
    RULES:
    1. Do not invent information. If something is missing, leave it as an empty string or empty list.
    2. Respond ONLY with valid JSON. Do not include markdown formatting like ```json.
    3. No explanations, just the JSON.

    RESUME TEXT:
    """ + raw_text

    try:
        # We ask Llama-3-70b (a very smart and fast model) to do the work
        chat_completion = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0, # Temperature 0 means we want facts, not creativity
            response_format={"type": "json_object"}, # Forces the AI to output JSON!
        )

        # Convert the text response into a Python dictionary
        result_string = chat_completion.choices[0].message.content
        return json.loads(result_string)
        
    except Exception as e:
        print(f"AI Parsing Error: {e}")
        # If it fails, return a safe fallback
        return {"raw_text": raw_text, "error": "Failed to parse"}
    
async def curate_resume_with_groq(master_resume_json: dict, jd_text: str) -> dict:
    """Uses Llama-3 to tailor the master resume to a specific job description."""
    
    prompt = f"""
    You are an expert Executive Resume Writer. I will give you a Master Resume (JSON) and a Job Description.
    Your task is to produce a highly targeted, ATS-optimized Curated Resume in JSON format.

    STRICT RULES:
    1. NEVER fabricate experience, skills, or metrics that are not in the master resume.
    2. EXPERIENCE: You MUST keep ALL internships/jobs from the master resume. Do not delete any. Just rewrite their bullet points to highlight relevance to the JD.
    3. PROJECTS: You MUST select exactly the top 4 most relevant projects for this JD. Rewrite their bullet points to mirror JD terminology.
    4. SKILLS: You MUST keep ALL technical skills, tools, and soft skills from the master resume. Do not delete any skills, as ATS systems look for a wide variety of keywords.
    5. SUMMARY: Write a new, 3-line targeted professional summary tailored to this role.
    6. Output ONLY valid JSON matching the schema below. No explanations.

    SCHEMA:
    {{
        "personal": {{"name": "", "email": "", "phone": "", "linkedin": "", "github": ""}},
        "summary": "Tailored 3-line summary",
        "education": [{{"degree": "", "institution": "", "year": "", "gpa": ""}}],
        "experience": [{{"role": "", "company": "", "duration": "", "description": ["tailored bullet 1", "tailored bullet 2"]}}],
        "projects": [{{"name": "", "tech_stack": [""], "duration": "", "description": ["tailored bullet 1", "tailored bullet 2"]}}],
        "skills": {{"technical": ["all original skills"], "tools": ["all original tools"], "soft": ["all original soft skills"]}}
    }}

    MASTER RESUME:
    {json.dumps(master_resume_json)}

    JOB DESCRIPTION:
    {jd_text}
    """

    try:
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.2, 
            response_format={"type": "json_object"},
        )
        return json.loads(chat.choices[0].message.content)
    except Exception as e:
        print(f"Curation Error: {e}")
        return {"error": "Failed to curate resume"}
    


async def score_ats_with_groq(resume_json: dict, jd_text: str) -> dict:
    """Acts as an ATS system to score the resume against the JD."""
    prompt = f"""
    Compare this Resume to this Job Description. 
    Give it an ATS match score (0-100) and list exactly 3 missing keywords or brief improvement suggestions.
    
    Resume: {json.dumps(resume_json)}
    JD: {jd_text}
    
    Respond ONLY in this JSON format:
    {{"score": 85, "missing_keywords": ["keyword 1", "keyword 2", "keyword 3"]}}
    """
    try:
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(chat.choices[0].message.content)
    except Exception:
        return {"score": 75, "missing_keywords": ["Failed to calculate ATS"]}

async def generate_interview_prep(resume_json: dict, jd_text: str) -> dict:
    """Generates a text-based interview prep sheet for Slack."""
    prompt = f"""
    Act as an Expert Interview Coach. Based on this Resume and JD, generate 3 highly probable interview questions they will be asked.
    
    CRITICAL INSTRUCTION: For each question, provide a FULL, WORD-FOR-WORD ideal answer script written in the first person ("I"). 
    Do NOT just give an outline, framework, or strategy. Write the exact sentences they should speak out loud, seamlessly integrating their specific resume experience.
    
    Resume: {json.dumps(resume_json)}
    JD: {jd_text}
    
    Respond ONLY in this JSON format:
    {{
        "prep_sheet": [
            {{"question": "...", "answer_script": "..."}},
            {{"question": "...", "answer_script": "..."}},
            {{"question": "...", "answer_script": "..."}}
        ]
    }}
    """
    try:
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(chat.choices[0].message.content)
    except Exception:
        return {"prep_sheet": []}