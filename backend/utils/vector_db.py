import chromadb
import os

# Initialize ChromaDB locally in a persistent folder
chroma_client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_data"))
resume_collection = chroma_client.get_or_create_collection(name="user_resumes")

def index_resume_in_vector_db(user_id: str, parsed_json: dict):
    """Converts the master resume into an embedding and saves it to the Vector DB."""
    skills = " ".join(parsed_json.get("skills", {}).get("technical", []))
    summary = parsed_json.get("summary", "")
    projects = " ".join([p.get("name", "") + " " + " ".join(p.get("tech_stack", [])) for p in parsed_json.get("projects", [])])
    
    text_blob = f"Skills: {skills} | Summary: {summary} | Experience: {projects}"
    
    resume_collection.upsert(
        documents=[text_blob],
        metadatas=[{"user_id": str(user_id)}],
        ids=[str(user_id)]
    )


def rank_jobs_by_resume_match(user_id: str, jobs: list) -> list:
    """Scores scraped jobs against the user's resume embedding using Cosine Similarity."""
    if len(jobs) == 0:
        return []
        
    # Grab your Master Resume embedding directly
    user_record = resume_collection.get(include=["embeddings"])
    embeddings = user_record.get("embeddings")
    
    # 🌟 FIX: Ultra-safe NumPy check! No "not" or "or" operators.
    if embeddings is None:
        print("⚠️ No embeddings found. Returning unranked.")
        return jobs
    if len(embeddings) == 0:
        print("⚠️ Embeddings list is empty. Returning unranked.")
        return jobs
        
    user_embedding = embeddings[0] 
    
    if hasattr(user_embedding, "tolist"):
        user_embedding = user_embedding.tolist()
        
    # Clean up any stuck temporary collections
    try:
        chroma_client.delete_collection("temp_jobs")
    except Exception:
        pass
        
    temp_col = chroma_client.create_collection(name="temp_jobs")
    
    job_docs = []
    job_ids = []
    for i, job in enumerate(jobs):
        job_docs.append(f"Job Role: {job['title']} at {job['company']}")
        job_ids.append(f"job_{i}")
        
    temp_col.upsert(documents=job_docs, ids=job_ids)
    
    results = temp_col.query(
        query_embeddings=[user_embedding],
        n_results=len(jobs) 
    )
    
    ranked_jobs = []
    for job_id in results["ids"][0]:
        idx = int(job_id.split("_")[1])
        matched_job = jobs[idx].copy()
        matched_job["title"] = f"🧠 {matched_job['title']}" 
        ranked_jobs.append(matched_job)
        
    chroma_client.delete_collection("temp_jobs")
    
    return ranked_jobs