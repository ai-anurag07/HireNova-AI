from groq import AsyncGroq
import os
import json
from dotenv import load_dotenv

load_dotenv()
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def classify_intent(user_message: str) -> dict:
    """Takes a Slack message and figures out what the user wants to do."""
    
    prompt = f"""
    You are the Orchestrator Agent for an AI Career Assistant.
    Analyze the user's message and determine the main intent and extract any parameters.

    Available Intents:
    1. "job_search" (User wants a standard keyword search. Needs: keyword, location)
    2. "semantic_job_search" (User explicitly asks to find jobs that "match my resume" or "fit my profile". Needs: keyword, location)
    3. "resume_curate" (User wants to tailor a resume. Needs: jd_text or job_url)
    4. "interview_start" (User wants to practice an interview. Needs: topic or jd_text)
    5. "create_alert" (User wants to be alerted or notified automatically about new jobs. Needs: keyword, location)
    6. "unknown"

    USER MESSAGE: "{user_message}"

    Respond ONLY in this JSON format:
    {{
        "intent": "job_search",
        "parameters": {{"keyword": "Python Developer", "location": "Delhi", "limit": 7}} 
    }}
    """

    chat = await groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )
    
    return json.loads(chat.choices[0].message.content)