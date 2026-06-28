import uuid
from sqlalchemy.future import select
from shared.schemas.a2a import A2AMessage, A2AResponse, A2AResponseResult
import db.models as models
from utils.llm import groq_client
from utils.voice import text_to_speech
from utils.storage import upload_file

async def execute_interview_agent(message: A2AMessage, db) -> A2AResponse:
    """Generates a tailored interview question and voice audio."""
    
    # 1. Extract the topic or job description from Slack
    payload = message.params.payload
    topic = payload.get("topic") or payload.get("jd_text") or "General Software Engineering"

    # 2. Fetch Master Resume from Database
    resume_result = await db.execute(
        select(models.MasterResume)
        .order_by(models.MasterResume.created_at.desc())
    )
    master_resume = resume_result.scalars().first()

    if not master_resume or not master_resume.parsed_json:
        return A2AResponse(
            id=message.id,
            error={"code": 404, "message": "No Master Resume found. Please upload one first!"}
        )

    # 3. Ask Groq (Llama-3) to generate a tough question based on the resume
    prompt = f"""
    You are an Expert AI Interviewer. 
    The candidate wants to practice for this role: {topic}
    Here is their resume: {master_resume.parsed_json}
    
    Ask ONE tough, highly specific technical or behavioral interview question based on their past projects and the requested role. 
    Do not include any greetings, feedback, or explanations. Just output the exact question text.
    """
    
    chat = await groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    question_text = chat.choices[0].message.content

    # 4. Synthesize the Question into Audio (Edge-TTS)
    audio_bytes = await text_to_speech(question_text)
    
    # 5. Upload Audio to MinIO and get the VIP link
    audio_filename = f"question_{uuid.uuid4()}.mp3"
    audio_url = upload_file(audio_filename, audio_bytes, "audio/mpeg")

    # 6. Send the text and audio link back to the Orchestrator
    result = A2AResponseResult(
        status="completed",
        output={"question_text": question_text, "audio_url": audio_url},
        artifacts=[{"type": "audio", "url": audio_url}]
    )
    
    return A2AResponse(id=message.id, result=result)