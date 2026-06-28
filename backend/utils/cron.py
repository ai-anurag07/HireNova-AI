import asyncio
import os
import httpx
from sqlalchemy.future import select
from db.database import AsyncSessionLocal
import db.models as models
from scrapers.multi import scrape_all_portals

async def run_job_alerts():
    """Wakes up, runs all saved searches, and messages Slack if there are new jobs."""
    print("⏰ CRON: Waking up to check for new jobs...")
    
    async with AsyncSessionLocal() as db:
        # Fetch all saved alerts
        result = await db.execute(select(models.SavedSearch))
        searches = result.scalars().all()
        
        for search in searches:
            print(f"🔍 Checking alert: {search.keyword} in {search.location}")
            
            # 1. Scrape the portals
            jobs = await asyncio.to_thread(scrape_all_portals, search.keyword, search.location, "", 5)
            
            # 2. Filter out jobs we have already seen
            seen_list = search.seen_jobs or []
            new_jobs = []
            
            for job in jobs:
                # Create a unique ID for the job based on title and company
                job_hash = f"{job['title']}_{job['company']}"
                if job_hash not in seen_list:
                    new_jobs.append(job)
                    seen_list.append(job_hash)
            
            # 3. If there are new jobs, send a Slack message!
            if new_jobs:
                print(f"🚨 Found {len(new_jobs)} new jobs! Sending to Slack...")
                
                blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"🚨 *JOB ALERT!* I found {len(new_jobs)} brand new *{search.keyword}* jobs while you were away!"}}]
                
                for i, job in enumerate(new_jobs):
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
                            "action_id": f"tailor_resume_btn_alert_{search.id}_{i}"
                        }
                    })
                
                # 4. Save the updated seen_list to the database so we don't alert you again
                search.seen_jobs = seen_list
                await db.commit()

                # 5. Send to Slack
                slack_token = os.getenv("SLACK_BOT_TOKEN")
                if slack_token:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            "https://slack.com/api/chat.postMessage",
                            headers={"Authorization": f"Bearer {slack_token}"},
                            json={
                                "channel": search.slack_channel_id, 
                                "blocks": blocks,
                                "unfurl_links": False, 
                                "unfurl_media": False
                            }
                        )