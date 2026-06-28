from utils.llm import parse_resume_with_groq, curate_resume_with_groq
from utils.pdf_gen import generate_resume_pdf
from pydantic import BaseModel
from scrapers.linkedin import scrape_linkedin_jobs
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.database import engine, Base, get_db
import db.models as models
from contextlib import asynccontextmanager
import uuid
import asyncio
from utils.llm import groq_client
from utils.voice import text_to_speech, speech_to_text
from fastapi import Form
from fastapi.responses import Response
# Import our tools
from utils.storage import upload_file
from utils.parser import extract_text_from_pdf
from pydantic import EmailStr
from utils.auth import get_password_hash, verify_password, create_access_token
from fastapi.middleware.cors import CORSMiddleware
from utils.voice import text_to_speech, speech_to_text
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from utils.auth import SECRET_KEY, ALGORITHM
import json
from shared.schemas.a2a import A2AMessage, A2AParams, A2AContext, A2AResponse
from agents.orchestrator.classifier import classify_intent
from agents.interview_coach.agent import execute_interview_agent


import httpx # Need this to send A2A messages to other agents
from agents.job_search.agent import execute_job_search_agent
from agents.resume_curator.agent import execute_resume_agent

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form, BackgroundTasks, Request
from urllib.parse import parse_qs
from fastapi import Response

from scrapers.multi import scrape_all_portals
from utils.vector_db import index_resume_in_vector_db

from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.cron import run_job_alerts
from db.database import AsyncSessionLocal

class JobSearchQuery(BaseModel):
    keyword: str
    location: str
    experience: Optional[str] = ""
    limit: Optional[int] = 3


class CurateResumeRequest(BaseModel):
    jd_text: str
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

from typing import List

class ChatMessage(BaseModel):
    role: str
    content: str

class InterviewPrepRequest(BaseModel):
    jd_text: str
    messages: List[ChatMessage]
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # <-- USE THIS ONCE to create the new SavedSearch table!
        await conn.run_sync(Base.metadata.create_all)
        
    # Start the background Cron Job! (Runs every 6 hours)
    scheduler.add_job(run_job_alerts, 'interval', hours=6)
    scheduler.start()
    
    yield
    scheduler.shutdown()

app = FastAPI(title="JobAgent API Gateway", lifespan=lifespan)

# 🌟 NEW: Allow the React website to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Your Next.js website
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

@app.get("/")
async def root():
    return {"message": "Welcome to the JobAgent A2A Multi-Agent System!"}

# Tells Swagger UI where to send the login request to get the padlock working
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """The Bouncer: Checks the token and finds the real user in the database."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
    result = await db.execute(select(models.User).filter_by(id=uuid.UUID(user_id_str)))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/auth/register")
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(models.User).filter_by(email=user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Hash the password and save the user
    hashed_pw = get_password_hash(user.password)
    new_user = models.User(
        id=uuid.uuid4(),
        email=user.email,
        hashed_password=hashed_pw,
        name=user.name
    )
    db.add(new_user)
    await db.commit()
    
    return {"message": "User created successfully! You can now log in."}

@app.post("/auth/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Find the user by email (Swagger puts the email in the 'username' field)
    result = await db.execute(select(models.User).filter_by(email=form_data.username))
    db_user = result.scalars().first()
    
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post("/resume/upload")
async def upload_master_resume(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 🌟 THE LOCK!
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed right now.")

    try:
        file_bytes = await file.read()
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_url = upload_file(file_name, file_bytes, file.content_type)
        resume_text = extract_text_from_pdf(file_bytes)
        structured_resume = await parse_resume_with_groq(resume_text)

        # 🌟 NEW: Save the resume to the Vector Database!
        index_resume_in_vector_db(str(current_user.id), structured_resume)


        # 🌟 Look how clean this is now! We just use 'current_user.id'
        new_resume = models.MasterResume(
            user_id=current_user.id,
            raw_file_url=file_url,
            parsed_json=structured_resume
        )
        db.add(new_resume)
        await db.commit()

        return {
            "message": f"Resume uploaded securely for {current_user.name}!",
            "file_url": file_url,
            "structured_data": structured_resume 
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/search")
def search_jobs(query: JobSearchQuery):
    try:
        # 🌟 Pass the new parameters!
        results = scrape_all_portals(query.keyword, query.location, query.experience, query.limit)
        
        if not results:
            return {"message": "No jobs found. The portals might have blocked the search.", "jobs": []}
            
        return {
            "message": f"Successfully found {len(results)} jobs across multiple portals!",
            "jobs": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/resume/curate")
async def curate_resume(
    request: CurateResumeRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 🌟 THE PADLOCK
):
    try:
        # Get the current logged-in user's master resume
        resume_result = await db.execute(
            select(models.MasterResume)
            .filter_by(user_id=current_user.id)
            .order_by(models.MasterResume.created_at.desc())
        )
        master_resume = resume_result.scalars().first()
        
        if not master_resume or not master_resume.parsed_json:
            raise HTTPException(status_code=400, detail="Please upload a master resume first.")

        # Ask AI to curate
        curated_json = await curate_resume_with_groq(master_resume.parsed_json, request.jd_text)
        if "error" in curated_json:
            raise HTTPException(status_code=500, detail="AI failed to curate.")

        # 🌟 NEW: 4. Generate the physical PDF document in a safe thread!
        pdf_bytes = await asyncio.to_thread(generate_resume_pdf, curated_json)
        
        # 🌟 NEW: 5. Save the new PDF to our free cloud (MinIO)
        pdf_filename = f"curated_{uuid.uuid4()}.pdf"
        pdf_url = upload_file(pdf_filename, pdf_bytes, "application/pdf")

        # 6. Save to Database
        new_curated_resume = models.CuratedResume(
            user_id=current_user.id,     # 🌟 FIXED!
            master_resume_id=master_resume.id,
            jd_snapshot={"text": request.jd_text},
            pdf_url=pdf_url,
            template="minimal" 
        )
        db.add(new_curated_resume)
        await db.commit()

        return {
            "message": "Resume successfully curated!",
            "pdf_download_url": pdf_url, # 🌟 The user can click this to download!
            "curated_resume_data": curated_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/interview/ask")
async def ask_interview_question(
    jd_text: str = Form(...), 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 🌟 THE PADLOCK
):
    try:
        # Get the current logged-in user's master resume
        resume_result = await db.execute(
            select(models.MasterResume)
            .filter_by(user_id=current_user.id)
            .order_by(models.MasterResume.created_at.desc())
        )
        master_resume = resume_result.scalars().first()

        # 1. Ask Groq to write a question
        prompt = f"""
        Look at this candidate's resume and this job description. 
        Ask ONE tough, specific technical interview question based on their past projects that relates to this JD.
        Just give the question, nothing else.
        
        Resume: {master_resume.parsed_json}
        JD: {jd_text}
        """
        
        
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        question_text = chat.choices[0].message.content

        # 2. Turn the question into Audio!
        audio_bytes = await text_to_speech(question_text)

        # 🌟 NEW: Save the audio to MinIO and get a temporary VIP link!
        audio_filename = f"question_{uuid.uuid4()}.mp3"
        audio_url = upload_file(audio_filename, audio_bytes, "audio/mpeg")

        # Return a nice JSON response with the link
        return {
            "message": "Question generated successfully!",
            "question_text": question_text,
            "audio_download_url": audio_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interview/answer")
async def evaluate_answer(
    question_text: str = Form(...), 
    audio_file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user) # 🌟 THE PADLOCK
):
    """Takes the user's voice answer, transcribes it, and grades it."""
    try:
        # 1. Read the audio file you uploaded
        audio_bytes = await audio_file.read()
        
        # 2. Use Groq Whisper to turn your voice into text!
        transcript = await speech_to_text(audio_bytes, audio_file.filename)
        
        if not transcript:
            raise HTTPException(status_code=400, detail="Could not hear any words in the audio.")

        # 3. Ask the AI Brain to grade your answer
        prompt = f"""
        You are an Expert Technical Interviewer. 
        You asked the candidate this question: "{question_text}"
        The candidate answered with this transcript: "{transcript}"
        
        Evaluate their answer. Be strict but fair.
        Return ONLY a JSON object matching this schema:
        {{
            "score": float (0 to 10),
            "verdict": "strong" | "adequate" | "weak",
            "feedback": "2-3 sentences of specific coaching feedback",
            "ideal_answer": "A complete, word-for-word script of the perfect 10/10 answer they should have spoken, written in the first person ('I'). No outlines."
        }}
        """
        
        from utils.llm import groq_client
        import json
        
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        
        evaluation = json.loads(chat.choices[0].message.content)

        return {
            "message": "Answer evaluated successfully!",
            "your_transcript": transcript,
            "evaluation": evaluation
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/interview/prep-chat")
async def interview_prep_chat(
    req: InterviewPrepRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """An interactive chat endpoint for interview preparation."""
    try:
        # 1. Fetch user's master resume
        resume_result = await db.execute(
            select(models.MasterResume)
            .filter_by(user_id=current_user.id)
            .order_by(models.MasterResume.created_at.desc())
        )
        master_resume = resume_result.scalars().first()
        if not master_resume:
            raise HTTPException(status_code=404, detail="No master resume found.")

        # 2. Build the System Prompt giving the AI its identity and knowledge
        system_prompt = f"""
        You are an Expert Technical Interview Coach. 
        The candidate is preparing for a role with this Job Description: {req.jd_text}
        Here is the candidate's Master Resume: {master_resume.parsed_json}
        
        Your goal is to help them prepare. When the user asks for example answers, DO NOT just give outlines, frameworks, or bullet-point strategies. 
        You MUST write out the complete, word-for-word ideal answer script in the first person ("I did X..."), integrating their actual past experience seamlessly.
        Be encouraging and format your responses clearly using Markdown.
        """

        # 3. Assemble the chat history
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for msg in req.messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        # 4. Call Llama-3!
        from utils.llm import groq_client
        chat = await groq_client.chat.completions.create(
            messages=formatted_messages,
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        
        return {"reply": chat.choices[0].message.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class SlackMessage(BaseModel):
    text: str

# In a real microservice setup, agents run on different ports (8001, 8002).
# For now, we will route them internally or to local ports.
AGENT_REGISTRY = {
    "job_search": "http://localhost:8000/agent/job_search",
    "resume_curate": "http://localhost:8000/agent/resume",
    "interview_start": "http://localhost:8000/agent/interview",
}

import httpx
import os

async def process_slack_message(text: str, channel: str, user_id: str):
    """Runs in the background. Analyzes the message, triggers agents, and replies to Slack."""
    # 1. Classify Intent
    classification = await classify_intent(text)
    intent = classification.get("intent")
    params = classification.get("parameters", {})

    if intent == "unknown":
        reply_text = "I'm not sure how to help with that. Try asking me to find jobs!"
        
    # 🌟 NEW: Create a background Job Alert
    # 🌟 NEW: Create a background Job Alert
    elif intent == "create_alert":
        keyword = params.get("keyword")
        location = params.get("location")
        
        if keyword and location:
            from sqlalchemy.future import select
            async with AsyncSessionLocal() as db_session:
                # 🌟 FIX: Grab your actual User account from the database!
                result = await db_session.execute(select(models.User))
                real_user = result.scalars().first()
                
                if not real_user:
                    reply_text = "❌ I couldn't find a registered user account. Please sign up on the Web UI first!"
                else:
                    new_alert = models.SavedSearch(
                        user_id=real_user.id, # 🌟 Use the mathematical database UUID!
                        keyword=keyword,
                        location=location,
                        slack_channel_id=channel,
                        seen_jobs=[]
                    )
                    db_session.add(new_alert)
                    await db_session.commit()
                    
                    reply_text = f"⏰ *Job Alert Set!* I will wake up every 6 hours, invisibly search for *{keyword}* jobs in *{location}*, and ping you here if I find brand new ones!"
        else:
            reply_text = "Please specify both the job title and location for the alert."
    else:
        # 2. Package A2A Message
        a2a_message = A2AMessage(
            params=A2AParams(
                task_type=intent,
                user_id=user_id,
                session_id=str(uuid.uuid4()),
                payload=params,
                context=A2AContext()
            )
        )

        # 🌟 FIX: Route semantic searches to the Job Agent too!
        agent_url = AGENT_REGISTRY.get(intent)
        if intent == "semantic_job_search":
            agent_url = AGENT_REGISTRY.get("job_search")
            
        
        # 3. Call the Agent
        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(agent_url, json=a2a_message.model_dump())
                a2a_response = response.json()
                
                if a2a_response.get("error"):
                    reply_text = f"Agent issue: {a2a_response['error'].get('message')}"
                else:
                    output = a2a_response.get("result", {}).get("output", {})
                    
                    # 🌟 FIX: Clean Slack UI - No redundant text!
                    if intent in ["job_search", "semantic_job_search"] and "jobs" in output:
                        jobs = output["jobs"]
                        blocks = [
                            {
                                "type": "section", 
                                "text": {"type": "mrkdwn", "text": f"🎯 *Found {len(jobs)} Jobs!* Click to auto-tailor your application:"}
                            }
                        ]
                        
                        for i, job in enumerate(jobs):
                            title = job.get('title', 'Role')
                            company = job.get('company', 'Company')
                            loc = job.get('location', 'Location')
                            link = job.get('apply_url', '#')
                            source = job.get('source', 'Web')
                            
                            job_summary = f"{title} at {company} in {loc}"
                            
                            blocks.append({
                                "type": "section",
                                "text": {"type": "mrkdwn", "text": f"<{link}|*{title}*> at *{company}*\n📍 _{loc}_  |  🏷️ `{source}`"},
                                "accessory": {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "✨ Auto-Tailor"},
                                    "value": job_summary,
                                    "action_id": f"tailor_resume_btn_{i}"
                                }
                            })
                            
                        # Send ONLY the blocks to Slack, nothing else!
                        slack_token = os.getenv("SLACK_BOT_TOKEN")
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                "https://slack.com/api/chat.postMessage",
                                headers={"Authorization": f"Bearer {slack_token}"},
                                json={
                                    "channel": channel, 
                                    "blocks": blocks,
                                    "unfurl_links": False,  # 🌟 FIX: Turns off the ugly previews!
                                    "unfurl_media": False   # 🌟 FIX: Turns off the ugly previews!
                                }
                            )
                        return # EXIT INSTANTLY so no duplicate text is printed
                    
                    # 🌟 FIX: The Ultimate A2A Care Package Formatting!
                    elif intent == "resume_curate" and "pdf_url" in output:
                        pdf_url = output.get("pdf_url")
                        ats_score = output.get("ats_score", 0)
                        keywords = ", ".join(output.get("missing_keywords", []))
                        prep_sheet = output.get("prep_sheet", [])
                        
                        # Format the ATS and PDF
                        emoji = "🟢" if ats_score >= 80 else "🟡" if ats_score >= 60 else "🔴"
                        reply_text = f"🚀 *Your Application Care Package is ready!*\n\n"
                        reply_text += f"📄 *Tailored Resume:* <{pdf_url}|*Download PDF*>\n"
                        reply_text += f"{emoji} *ATS Match Score:* {ats_score}%\n"
                        reply_text += f"🔍 *Keywords to consider adding:* _{keywords}_\n\n"
                        
                        # Format the Interview Prep
                        # Format the Interview Prep (Inside the resume_curate elif block)
                        reply_text += f"🧠 *Interview Prep Sheet:*\n"
                        for idx, item in enumerate(prep_sheet, 1):
                            reply_text += f"*{idx}. {item.get('question')}*\n"
                            reply_text += f">💡 _Ideal Answer:_ {item.get('answer_script')}\n\n"
                        
                        reply_text += "_(To practice this live with Voice AI, head over to your Web Dashboard!)_"

                    # 🌟 FIX: NEW SLACK V2 FILE UPLOAD!
                    elif intent == "interview_start" and "audio_url" in output:
                        q_text = output["question_text"]
                        audio_url = output["audio_url"]
                        
                        slack_token = os.getenv("SLACK_BOT_TOKEN")
                        headers = {"Authorization": f"Bearer {slack_token}"}
                        
                        # Download the MP3 from our MinIO cloud
                        audio_resp = await client.get(audio_url)
                        audio_bytes = audio_resp.content
                        
                        # STEP 1: Ask Slack for a secure upload URL
                        get_url_resp = await client.post(
                            "https://slack.com/api/files.getUploadURLExternal",
                            headers=headers,
                            data={"filename": "question.mp3", "length": len(audio_bytes)}
                        )
                        url_data = get_url_resp.json()
                        
                        if url_data.get("ok"):
                            upload_url = url_data["upload_url"]
                            file_id = url_data["file_id"]
                            
                            # STEP 2: Upload the raw audio bytes to the secure URL
                            await client.post(upload_url, content=audio_bytes)
                            
                            # STEP 3: Tell Slack we are done and post it to the channel!
                            await client.post(
                                "https://slack.com/api/files.completeUploadExternal",
                                headers=headers,
                                json={
                                    "files": [{"id": file_id, "title": "AI Interviewer"}],
                                    "channel_id": channel,
                                    "initial_comment": f"🎙️ *Mock Interview Started!*\n\n*Question:* {q_text}\n\n_(Tip: Click the Microphone 🎤 icon in the chat bar to reply with a voice note!)_"
                                }
                            )
                        else:
                            # Safety Net Fallback
                            fallback_text = f"🎙️ *Mock Interview Started!*\n\n*Question:* {q_text}\n\n🎧 <{audio_url}|*Click here to listen*>"
                            await client.post(
                                "https://slack.com/api/chat.postMessage",
                                headers=headers,
                                json={"channel": channel, "text": fallback_text}
                            )
                        return # Exit early
                        
                    # Fallback
                    else:
                        reply_text = f"Task completed!\n```{output}```"
            except Exception as e:
                reply_text = f"Failed to contact {intent} agent: {str(e)}"

    # 4. Send the result back to Slack!
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        print("❌ CRITICAL ERROR: SLACK_BOT_TOKEN is missing from .env!")
        return

    print(f"Sending response to Slack channel {channel}...")
    async with httpx.AsyncClient() as client:
        slack_resp = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {slack_token}"},
            json={"channel": channel, "text": reply_text}
        )
        print(f"Slack API Response: {slack_resp.status_code} - {slack_resp.text}")

async def process_slack_voice_note(file_info: dict, channel: str):
    """Downloads a Slack Voice Note, transcribes it, and grades it!"""
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    download_url = file_info.get("url_private_download")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Let the user know we are listening!
        await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {slack_token}"},
            json={"channel": channel, "text": "👂 _Listening to your voice note and analyzing..._"}
        )

        # 2. Download the secure voice note file from Slack
        audio_resp = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {slack_token}"}
        )
        
        # 3. Transcribe it instantly using Groq Whisper!
        transcript = await speech_to_text(audio_resp.content, "voicenote.webm")
        
        if not transcript:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {slack_token}"},
                json={"channel": channel, "text": "❌ I couldn't hear any words in that audio. Try again!"}
            )
            return
            
        # 4. Grade the answer using Llama-3!
        prompt = f"""
        You are an Expert Technical Interviewer. 
        The candidate just answered an interview question via a voice note. 
        Transcript: "{transcript}"
        
        Evaluate their answer based on general engineering best practices. Be strict but fair.
        Return ONLY a JSON object matching this schema:
        {{
            "score": float (0 to 10),
            "verdict": "strong" | "adequate" | "weak",
            "feedback": "2-3 sentences of specific coaching feedback",
            "ideal_answer": "What a perfect answer would have included"
        }}
        """
        
        from utils.llm import groq_client
        import json
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        
        eval_data = json.loads(chat.choices[0].message.content)
        
        # 5. Format the beautiful scorecard!
        score = eval_data.get("score")
        verdict = eval_data.get("verdict", "").upper()
        emoji = "✅" if verdict == "STRONG" else "⚠️" if verdict == "ADEQUATE" else "❌"
        
        reply_text = f"📝 *Interview Scorecard*\n\n"
        reply_text += f"*Your Transcript:* _{transcript}_\n\n"
        reply_text += f"*Score:* {score}/10 {emoji} ({verdict})\n\n"
        reply_text += f"*Feedback:* {eval_data.get('feedback')}\n\n"
        reply_text += f"*Ideal Answer:* {eval_data.get('ideal_answer')}"
        
        await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {slack_token}"},
            json={"channel": channel, "text": reply_text}
        )

class ApplicationCreate(BaseModel):
    title: str
    company: str
    location: str
    apply_url: str

class ApplicationUpdate(BaseModel):
    status: str

@app.post("/jobs/track")
async def save_job_application(app_data: ApplicationCreate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_app = models.Application(
        user_id=current_user.id,
        title=app_data.title,
        company=app_data.company,
        location=app_data.location,
        apply_url=app_data.apply_url,
        status="saved"
    )
    db.add(new_app)
    await db.commit()
    return {"message": "Job saved to your tracker!"}

@app.get("/jobs/applications")
async def get_applications(db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    result = await db.execute(select(models.Application).filter_by(user_id=current_user.id).order_by(models.Application.created_at.desc()))
    apps = result.scalars().all()
    return apps

@app.put("/jobs/track/{app_id}")
async def update_application_status(app_id: str, app_update: ApplicationUpdate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    result = await db.execute(select(models.Application).filter_by(id=uuid.UUID(app_id), user_id=current_user.id))
    application = result.scalars().first()
    if application:
        application.status = app_update.status
        await db.commit()
        return {"message": "Status updated!"}
    raise HTTPException(status_code=404, detail="Application not found.")
@app.delete("/jobs/track/{app_id}")
async def delete_application(app_id: str, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Permanently deletes a saved job from the tracker."""
    result = await db.execute(select(models.Application).filter_by(id=uuid.UUID(app_id), user_id=current_user.id))
    application = result.scalars().first()
    
    if application:
        await db.delete(application)
        await db.commit()
        return {"message": "Job removed from tracker!"}
        
    raise HTTPException(status_code=404, detail="Application not found.")
@app.get("/jobs/research")
async def get_company_research(company: str, role: str, current_user: models.User = Depends(get_current_user)):
    """Generates a quick company cheat sheet for interview prep."""
    prompt = f"""
    Act as an Expert Career Advisor. The candidate is interviewing for the role of '{role}' at '{company}'.
    Generate a highly concise, bullet-pointed "Cheat Sheet" about this company to help them prepare.
    
    Include exactly these 4 sections:
    1. 🏢 Core Business & Mission
    2. 💻 Likely Tech Stack / Tools
    3. 📈 Market Position & Culture
    4. 🎯 Top 3 Interview Tips (Specific to this role and company)
    
    Keep it under 300 words. Format it beautifully using standard Markdown.
    """
    
    try:
        chat = await groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        brief = chat.choices[0].message.content
        return {"brief": brief}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate research brief.")
    
@app.post("/orchestrator/chat")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """The webhook that Slack talks to."""
    body = await request.json()

    if "challenge" in body:
        return {"challenge": body["challenge"]}

    if "event" in body:
        event = body["event"]
        
        # Ignore messages sent by the bot itself
        if event.get("bot_id"):
            return {"status": "ok"}
            
        # We process mentions OR direct messages
        if event.get("type") in ["app_mention", "message"]:
            channel = event.get("channel")
            user = event.get("user")
            
            # 🌟 NEW: Check if the user sent an audio Voice Note!
            files = event.get("files", [])
            if files and files[0].get("mimetype", "").startswith("audio"):
                background_tasks.add_task(process_slack_voice_note, files[0], channel)
                return {"status": "ok"}

            # Otherwise, process it as standard text
            text = event.get("text", "")
            if text:
                background_tasks.add_task(process_slack_message, text, channel, user)

    return {"status": "ok"}
        

@app.post("/agent/job_search", response_model=A2AResponse)
async def job_search_agent_endpoint(message: A2AMessage):
    """Internal A2A Endpoint: Only other agents (like the Orchestrator) call this."""
    try:
        # Pass the message to the Agent logic
        response = await execute_job_search_agent(message)
        return response
    except Exception as e:
        return A2AResponse(
            id=message.id,
            error={"code": 500, "message": str(e)}
        )
    

@app.post("/agent/resume", response_model=A2AResponse)
async def resume_agent_endpoint(message: A2AMessage, db: AsyncSession = Depends(get_db)):
    """Internal A2A Endpoint for tailoring resumes."""
    try:
        # We pass the 'db' session so the agent can fetch your master resume
        return await execute_resume_agent(message, db)
    except Exception as e:
        return A2AResponse(
            id=message.id,
            error={"code": 500, "message": str(e)}
        )
    
@app.post("/agent/interview", response_model=A2AResponse)
async def interview_agent_endpoint(message: A2AMessage, db: AsyncSession = Depends(get_db)):
    """Internal A2A Endpoint for generating mock interviews."""
    try:
        return await execute_interview_agent(message, db)
    except Exception as e:
        return A2AResponse(
            id=message.id,
            error={"code": 500, "message": str(e)}
        )
    
@app.post("/orchestrator/interactivity")
async def slack_interactivity(request: Request, background_tasks: BackgroundTasks):
    """Catches button clicks from Slack."""
    body = await request.body()
    parsed_body = parse_qs(body.decode("utf-8"))
    payload = json.loads(parsed_body["payload"][0])
    
    # Slack requires an instant 200 OK response when a button is clicked
    if payload.get("type") == "block_actions":
        action = payload["actions"][0]
        action_id = action.get("action_id", "")
        
        if action_id.startswith("tailor_resume_btn"):
            job_details = action["value"]
            channel_id = payload["channel"]["id"]
            user_id = payload["user"]["id"]
            
            # 1. Send a quick "Processing" message to Slack
            slack_token = os.getenv("SLACK_BOT_TOKEN")
            async def send_loading():
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={"Authorization": f"Bearer {slack_token}"},
                        json={"channel": channel_id, "text": f"⚙️ Starting the A2A Chain for *{job_details}*...\n_Curating Resume ➔ Scoring ATS ➔ Generating Interview Prep_"}
                    )
            background_tasks.add_task(send_loading)
            
            # 2. Trick the Orchestrator into thinking you typed a resume command!
            fake_user_command = f"Tailor my resume and prep me for this job: {job_details}"
            background_tasks.add_task(process_slack_message, fake_user_command, channel_id, user_id)

    return Response(status_code=200)