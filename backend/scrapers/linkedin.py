import urllib.parse
from playwright.sync_api import sync_playwright

def scrape_linkedin_jobs(keyword: str, location: str) -> list:
    """Uses an invisible browser to search LinkedIn for jobs in a background thread."""
    jobs = []
    
    # Start the invisible browser (Sync Mode)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        safe_keyword = urllib.parse.quote(keyword)
        safe_location = urllib.parse.quote(location)
        url = f"https://www.linkedin.com/jobs/search?keywords={safe_keyword}&location={safe_location}"
        
        try:
            print(f"Going to {url}...")
            page.goto(url)
            
            # Wait for the job list to load on the screen
            page.wait_for_selector("ul.jobs-search__results-list li", timeout=10000)
            
            # Find all the job cards
            job_cards = page.query_selector_all("ul.jobs-search__results-list li")
            
            # Loop through the first 5 jobs we find
            for card in job_cards[:5]:
                title_el = card.query_selector("h3.base-search-card__title")
                company_el = card.query_selector("h4.base-search-card__subtitle")
                location_el = card.query_selector("span.job-search-card__location")
                url_el = card.query_selector("a.base-card__full-link")
                
                if title_el and company_el:
                    title = title_el.inner_text()
                    company = company_el.inner_text()
                    loc = location_el.inner_text() if location_el else location
                    link = url_el.get_attribute("href") if url_el else url
                    
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": loc.strip(),
                        "apply_url": link.strip(),
                        "source": "LinkedIn"
                    })
        except Exception as e:
            print(f"Scraping error: {e}")
            
        # Close the browser
        browser.close()
        
    return jobs