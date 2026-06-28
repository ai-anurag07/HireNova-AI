import html
from playwright.sync_api import sync_playwright

def e(text):
    """Helper function to safely escape characters for HTML."""
    return html.escape(str(text)) if text else ""

def generate_resume_pdf(resume_json: dict) -> bytes:
    """Creates a beautiful HTML document and uses the Ghost Browser to print it to PDF."""
    
    personal = resume_json.get("personal", {})
    
    # 1. Build the Contact String (Phone | Email | LinkedIn)
    contact_parts = []
    for key in ["phone", "email", "linkedin", "github"]:
        val = personal.get(key)
        if val:
            contact_parts.append(e(val))
    contact_str = " | ".join(contact_parts)

    # 2. Build the exact CSS styling for an Ivy-League/IIT style ATS Resume
    html_str = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <style>
            body {{ 
                font-family: 'Times New Roman', Times, serif; 
                font-size: 11pt; color: #000; margin: 0; padding: 40px; line-height: 1.3; 
            }}
            h1 {{ font-size: 24pt; text-align: center; margin: 0 0 5px 0; font-weight: normal; }}
            .contact {{ text-align: center; font-size: 10pt; margin-bottom: 15px; color: #333; }}
            h2 {{ 
                font-size: 12pt; border-bottom: 1px solid #000; 
                margin: 0 0 8px 0; padding-bottom: 2px; text-transform: uppercase; 
            }}
            .flex-row {{ display: flex; justify-content: space-between; align-items: baseline; }}
            .bold {{ font-weight: bold; }}
            .italic {{ font-style: italic; }}
            .mb-1 {{ margin-bottom: 4px; }}
            .mb-2 {{ margin-bottom: 12px; }}
            ul {{ margin: 4px 0 12px 0; padding-left: 20px; }}
            li {{ margin-bottom: 4px; text-align: justify; }}
        </style>
    </head>
    <body>
        <h1>{e(personal.get('name', 'Candidate'))}</h1>
        <div class="contact">{contact_str}</div>
    """

    # 3. Add Summary
    if resume_json.get("summary"):
        html_str += f"<h2>Professional Summary</h2><p class='mb-2'>{e(resume_json['summary'])}</p>"

    # 4. Add Experience
    if resume_json.get("experience"):
        html_str += "<h2>Experience</h2>"
        for exp in resume_json["experience"]:
            html_str += f"""
            <div class="mb-2">
                <div class="flex-row bold">
                    <span>{e(exp.get('role', ''))} at {e(exp.get('company', ''))}</span>
                    <span class="italic font-normal">{e(exp.get('duration', ''))}</span>
                </div>
                <ul>
            """
            for bullet in exp.get("description", []):
                html_str += f"<li>{e(bullet)}</li>"
            html_str += "</ul></div>"

    # 5. Add Projects
    if resume_json.get("projects"):
        html_str += "<h2>Projects</h2>"
        for proj in resume_json["projects"]:
            tech = ", ".join(proj.get("tech_stack", []))
            title = f"{e(proj.get('name', ''))} | {e(tech)}" if tech else e(proj.get('name', ''))
            html_str += f"""
            <div class="mb-2">
                <div class="flex-row bold mb-1">
                    <span>{title}</span>
                    <span class="italic font-normal">{e(proj.get('duration', ''))}</span>
                </div>
                <ul>
            """
            for bullet in proj.get("description", []):
                html_str += f"<li>{e(bullet)}</li>"
            html_str += "</ul></div>"

    # 6. Add Education
    if resume_json.get("education"):
        html_str += "<h2>Education</h2>"
        for edu in resume_json["education"]:
            html_str += f"""
            <div class="mb-2">
                <div class="flex-row bold">
                    <span>{e(edu.get('degree', ''))}</span>
                    <span>{e(edu.get('year', ''))}</span>
                </div>
                <div class="flex-row">
                    <span>{e(edu.get('institution', ''))}</span>
                    <span>GPA/Marks: {e(edu.get('gpa', ''))}</span>
                </div>
            </div>
            """

    # 7. Add Technical Skills
    skills = resume_json.get("skills", {})
    if skills:
        html_str += "<h2>Technical Skills</h2><div class='mb-2'>"
        if skills.get("technical"):
            html_str += f"<div class='mb-1'><span class='bold'>Languages & Core:</span> {e(', '.join(skills['technical']))}</div>"
        if skills.get("tools"):
            html_str += f"<div class='mb-1'><span class='bold'>Tools & Frameworks:</span> {e(', '.join(skills['tools']))}</div>"
        if skills.get("soft"):
            html_str += f"<div class='mb-1'><span class='bold'>Soft Skills:</span> {e(', '.join(skills['soft']))}</div>"
        html_str += "</div>"

    html_str += """
    </body>
    </html>
    """

    # 8. Render the HTML to a PDF using the Ghost Browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_str)
        # Margin is 0 because we added padding directly to the HTML body CSS!
        pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
        
    return pdf_bytes