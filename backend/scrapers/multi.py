import urllib.parse
import requests
import re
from playwright.sync_api import sync_playwright

def scrape_all_portals(keyword: str, location: str, experience: str = "", limit: int = 3) -> list:
    jobs = []
    
    # --- EXPERIENCE PARSER ---
    exp_code = ""
    nums = re.findall(r'\d+', experience)
    if nums:
        yrs = int(nums[0])
        if yrs <= 1: exp_code = "2"
        elif yrs <= 4: exp_code = "4"
        else: exp_code = "5"
    else:
        exp_lower = experience.lower()
        if "entry" in exp_lower or "fresher" in exp_lower: exp_code = "2"
        elif "mid" in exp_lower: exp_code = "4"
        elif "senior" in exp_lower: exp_code = "5"

    # ---------------------------------------------------------
    # 1. INSTAHYRE (Lightning Fast API)
    # ---------------------------------------------------------
    try:
        print("⚡ Scraping Instahyre...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        insta_url = f"https://www.instahyre.com/api/v1/job_search?title={urllib.parse.quote(keyword)}&location={urllib.parse.quote(location)}"
        insta_resp = requests.get(insta_url, headers=headers, timeout=10)
        
        if insta_resp.status_code == 200:
            data = insta_resp.json()
            if isinstance(data, dict) and "objects" in data:
                for job in data.get("objects", [])[:limit]:
                    jobs.append({
                        "title": job.get("title", ""),
                        "company": job.get("employer", {}).get("company_name", ""),
                        "location": location,
                        "apply_url": f"https://www.instahyre.com/job-{job.get('id')}",
                        "source": "Instahyre"
                    })
    except Exception as e:
        print(f"⚠️ Instahyre failed: {e}")

    # ---------------------------------------------------------
    # 2. LINKEDIN OFFICIAL (Ghost Browser)
    # ---------------------------------------------------------
    print("🕵️‍♂️ Booting Ghost Browser for LinkedIn...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            print("   -> Scraping LinkedIn...")
            page = context.new_page()
            url = f"https://www.linkedin.com/jobs/search?keywords={urllib.parse.quote(keyword)}&location={urllib.parse.quote(location)}"
            if exp_code: url += f"&f_E={exp_code}"
            
            page.goto(url, timeout=15000)
            page.wait_for_selector("ul.jobs-search__results-list li", timeout=5000)
            
            for card in page.query_selector_all("ul.jobs-search__results-list li")[:limit]:
                t_el = card.query_selector("h3.base-search-card__title")
                c_el = card.query_selector("h4.base-search-card__subtitle")
                u_el = card.query_selector("a.base-card__full-link")
                if t_el and c_el:
                    jobs.append({
                        "title": t_el.inner_text().strip(),
                        "company": c_el.inner_text().strip(),
                        "location": location,
                        "apply_url": u_el.get_attribute("href") if u_el else url,
                        "source": "LinkedIn"
                    })
        except Exception as e:
            print(f"   ⚠️ LinkedIn Failed: {e}")

        browser.close()
        
    return jobs