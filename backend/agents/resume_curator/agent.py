import uuid
import asyncio
from sqlalchemy.future import select
from shared.schemas.a2a import A2AMessage, A2AResponse, A2AResponseResult
import db.models as models
from utils.llm import curate_resume_with_groq, score_ats_with_groq, generate_interview_prep
from utils.pdf_gen import generate_resume_pdf
from utils.storage import upload_file

async def execute_resume_agent(message: A2AMessage, db) -> A2AResponse:
    """A2A CHAIN: Curates Resume -> Scores ATS -> Generates Interview Prep."""
    
    jd_text = str(message.params.payload)

    resume_result = await db.execute(
        select(models.MasterResume)
        .order_by(models.MasterResume.created_at.desc())
    )
    master_resume = resume_result.scalars().first()

    if not master_resume:
        return A2AResponse(id=message.id, error={"code": 404, "message": "No Master Resume found."})

    print("🤖 Agent Chain Step 1: Tailoring Resume...")
    curated_json = await curate_resume_with_groq(master_resume.parsed_json, jd_text)
    
    if "error" in curated_json:
        return A2AResponse(id=message.id, error={"code": 500, "message": "AI failed to curate."})

    print("🤖 Agent Chain Step 2 & 3: Calculating ATS and Generating Interview Prep in parallel...")
    # Run the ATS scorer and Interview Prep at the exact same time to save time!
    ats_task = score_ats_with_groq(curated_json, jd_text)
    prep_task = generate_interview_prep(curated_json, jd_text)
    
    ats_result, prep_result = await asyncio.gather(ats_task, prep_task)

    print("🤖 Agent Chain Step 4: Generating PDF...")
    # 🌟 NEW: Safe threaded generation
    pdf_bytes = await asyncio.to_thread(generate_resume_pdf, curated_json)
    pdf_url = upload_file(f"curated_{uuid.uuid4()}.pdf", pdf_bytes, "application/pdf")

    # Save to Database
    new_curated = models.CuratedResume(
        user_id=master_resume.user_id,
        master_resume_id=master_resume.id,
        jd_snapshot={"text": jd_text},
        pdf_url=pdf_url,
        template="minimal",
        ats_score=ats_result.get("score", 0)
    )
    db.add(new_curated)
    await db.commit()

    # Package the ultimate Care Package!
    output = {
        "pdf_url": pdf_url,
        "ats_score": ats_result.get("score"),
        "missing_keywords": ats_result.get("missing_keywords", []),
        "prep_sheet": prep_result.get("prep_sheet", [])
    }
    
    return A2AResponse(
        id=message.id, 
        result=A2AResponseResult(status="completed", output=output)
    )