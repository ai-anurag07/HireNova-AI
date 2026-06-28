"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { FileText, UploadCloud, FileCheck, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function ResumePage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [jdText, setJdText] = useState("");
  const [curatingStatus, setCuratingStatus] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploadStatus("Uploading & Parsing via AI...");
    try {
      const formData = new FormData();
      formData.append("file", file);
      await api.post("/resume/upload", formData);
      setUploadStatus("✅ Master Resume Saved & AI Parsed!");
    } catch (err) {
      setUploadStatus("❌ Upload failed. Please try again.");
    }
  };

  const handleCurate = async () => {
    if (!jdText) return;
    setCuratingStatus("AI is rewriting your resume for this job...");
    setPdfUrl(null);
    try {
      const res = await api.post("/resume/curate", { jd_text: jdText });
      setPdfUrl(res.data.pdf_download_url);
      setCuratingStatus("✅ Success!");
    } catch (err) {
      setCuratingStatus("❌ Failed to curate. Make sure you uploaded a Master Resume first.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        
        <Link href="/" className="flex items-center text-blue-600 hover:text-blue-800 font-medium">
          <ArrowLeft size={20} className="mr-2" /> Back to Dashboard
        </Link>

        <h1 className="text-3xl font-bold text-gray-800 flex items-center">
          <FileText className="mr-3 text-blue-600" size={32} /> Resume AI Studio
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* STEP 1: Upload Master Resume */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
              <span className="bg-blue-100 text-blue-600 w-8 h-8 rounded-full flex items-center justify-center mr-3">1</span> 
              Master Resume
            </h2>
            <p className="text-sm text-gray-600 mb-4">Upload your full, unedited PDF resume. Our AI will extract all your experience.</p>
            
            <input 
              type="file" 
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 mb-4"
            />
            
            <button 
              onClick={handleUpload}
              disabled={!file}
              className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 transition disabled:bg-gray-300 flex items-center justify-center"
            >
              <UploadCloud size={20} className="mr-2" /> Upload & Parse
            </button>
            {uploadStatus && <p className="mt-3 text-sm font-medium text-center text-blue-600">{uploadStatus}</p>}
          </div>

          {/* STEP 2: Tailor for a Job */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
              <span className="bg-green-100 text-green-600 w-8 h-8 rounded-full flex items-center justify-center mr-3">2</span> 
              Tailor to Job
            </h2>
            <p className="text-sm text-gray-600 mb-4">Paste the Job Description. The AI will rewrite your resume to match it perfectly.</p>
            
            <textarea 
              rows={4}
              placeholder="Paste Job Description here..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500 mb-4 text-sm text-gray-900 bg-white"
            />
            
            <button 
              onClick={handleCurate}
              disabled={!jdText}
              className="w-full bg-green-600 text-white py-2 rounded-md hover:bg-green-700 transition disabled:bg-gray-300 flex items-center justify-center"
            >
              <FileCheck size={20} className="mr-2" /> Generate Tailored PDF
            </button>
            {curatingStatus && <p className="mt-3 text-sm font-medium text-center text-green-600">{curatingStatus}</p>}
            
            {/* The Download Button appears here! */}
            {pdfUrl && (
              <a 
                href={pdfUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="mt-4 block w-full text-center border-2 border-green-600 text-green-600 font-bold py-2 rounded-md hover:bg-green-50 transition"
              >
                📥 Download PDF Resume
              </a>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}