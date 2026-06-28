import json
from shared.schemas.a2a import A2AMessage, A2AResponse, A2AResponseResult
from scrapers.linkedin import scrape_linkedin_jobs
from utils.llm import groq_client
import asyncio
from scrapers.multi import scrape_all_portals
# This is the "MCP Tool Definition" - It tells the LLM what tools it has available
JOB_SCRAPE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_all_portals",
        "description": "Scrapes LinkedIn and Instahyre for open job roles.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "location": {"type": "string"},
                "experience": {"type": "string", "description": "Years of experience, e.g., '3 years' or 'entry level'"},
                "limit": {"type": "integer", "description": "Number of jobs per portal"}
            },
            "required": ["keyword", "location"]
        }
    }
}

async def execute_job_search_agent(message: A2AMessage) -> A2AResponse:
    """The Job Agent receives the A2A message, uses the LLM to call the MCP tool, and returns the result."""
    
    user_request = str(message.params.payload)
    
    # 1. Give the LLM the user's request AND the toolbox
    chat = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are the Job Agent. You MUST use the search_all_portals tool."},
            {"role": "user", "content": f"Find jobs using these parameters: {user_request}"}
        ],
        tools=[JOB_SCRAPE_TOOL],
        tool_choice={"type": "function", "function": {"name": "search_all_portals"}} # 🌟 RENAMED
    )
    
    response_message = chat.choices[0].message
    jobs = []

    # 2. Did the LLM decide to use the tool?
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "search_all_portals": # 🌟 RENAMED
                args = json.loads(tool_call.function.arguments)
                print(f"🤖 Agent decided to run scraper with: {args}")
                
                # 🌟 FIX: Safely pass experience to the scraper    
                exp = args.get("experience", "")
                limit = args.get("limit", 3) # 🌟 Defaults to 3 if user didn't specify
                jobs = await asyncio.to_thread(scrape_all_portals, args["keyword"], args["location"], exp, limit)
    
    # 🌟 NEW: If the user asked for Semantic Search, rank the jobs using ChromaDB!
    if message.params.task_type == "semantic_job_search":
        print("🧠 Performing Vector Database Semantic Matching...")
        from utils.vector_db import rank_jobs_by_resume_match
        jobs = rank_jobs_by_resume_match(message.params.user_id, jobs)

    result = A2AResponseResult(
        status="completed",
        output={"message": f"Found {len(jobs)} jobs!", "jobs": jobs},
        next_actions=["suggest_apply"]
    )
    
    
    return A2AResponse(
        id=message.id,
        result=result
    )