"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Search, MapPin, Briefcase, ArrowLeft, ExternalLink, BookmarkPlus } from "lucide-react";
import Link from "next/link";

interface Job {
  title: string;
  company: string;
  location: string;
  apply_url: string;
  source: string;
}

export default function JobSearchPage() {
  const [limit, setLimit] = useState(3);
  const [keyword, setKeyword] = useState("Python Developer");
  const [location, setLocation] = useState("Delhi, India");
  const [isSearching, setIsSearching] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [message, setMessage] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSearching(true);
    setMessage("Ghost Browser is searching portals... (this takes ~10 seconds)");
    setJobs([]);

    try {
      const res = await api.post("/jobs/search", { keyword, location, limit });
      setJobs(res.data.jobs);
      setMessage(res.data.message);
    } catch (err) {
      setMessage("❌ Search failed. Portals might have blocked the invisible browser temporarily.");
    } finally {
      setIsSearching(false);
    }
  };

  // 🌟 NEW: Function to save the job to your database
  const handleSaveJob = async (job: Job) => {
    try {
      await api.post("/jobs/track", job);
      alert(`Saved ${job.title} at ${job.company} to your Tracker!`);
    } catch (err) {
      alert("Failed to save job. Did you reset the database for the new table?");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        
        <Link href="/" className="flex items-center text-blue-600 hover:text-blue-800 font-medium">
          <ArrowLeft size={20} className="mr-2" /> Back to Dashboard
        </Link>

        <h1 className="text-3xl font-bold text-gray-800 flex items-center">
          <Search className="mr-3 text-green-600" size={32} /> Job Discovery
        </h1>

        {/* Search Bar */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Briefcase className="absolute left-3 top-3 text-gray-400" size={20} />
              <input 
                type="text" 
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500 text-gray-900 bg-white"
                placeholder="Job Title (e.g., Data Scientist)"
                required
              />
            </div>
            <div className="flex-1 relative">
              <MapPin className="absolute left-3 top-3 text-gray-400" size={20} />
              <input 
                type="text" 
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500 text-gray-900 bg-white"
                placeholder="Location (e.g., Delhi, India)"
                required
              />
            </div>
            <div className="w-24">
              <select 
                value={limit} 
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full h-full px-3 py-2 border border-gray-300 rounded-md focus:ring-green-500 focus:border-green-500 text-gray-900 bg-white"
              >
                <option value={3}>3 each</option>
                <option value={5}>5 each</option>
                <option value={10}>10 each</option>
              </select>
            </div>
            <button 
              type="submit" 
              disabled={isSearching}
              className="bg-green-600 text-white px-8 py-2 rounded-md hover:bg-green-700 transition disabled:bg-gray-400 font-medium"
            >
              {isSearching ? "Searching..." : "Find Jobs"}
            </button>
          </form>
          {message && <p className="mt-4 text-sm text-center text-gray-600 font-medium">{message}</p>}
        </div>

        {/* Job Results Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {jobs.map((job, idx) => (
            <div key={idx} className="bg-white p-5 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition flex flex-col justify-between h-full">
              <div>
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-lg text-gray-800 leading-tight">{job.title}</h3>
                  <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-1 rounded">
                    {job.source}
                  </span>
                </div>
                <p className="text-gray-600 font-medium mb-1">{job.company}</p>
                <p className="text-gray-500 text-sm flex items-center mb-4">
                  <MapPin size={14} className="mr-1" /> {job.location}
                </p>
              </div>
              
              {/* 🌟 NEW: Split buttons for View and Save */}
              <div className="flex gap-2">
                <a 
                  href={job.apply_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex-1 bg-gray-50 text-blue-600 border border-blue-200 py-2 rounded flex items-center justify-center hover:bg-blue-50 transition text-sm font-bold"
                >
                  View <ExternalLink size={16} className="ml-2" />
                </a>
                <button 
                  onClick={() => handleSaveJob(job)}
                  className="bg-green-50 text-green-600 border border-green-200 px-4 py-2 rounded flex items-center justify-center hover:bg-green-100 transition text-sm font-bold"
                  title="Save to Tracker"
                >
                  <BookmarkPlus size={18} />
                </button>
              </div>

            </div>
          ))}
        </div>

      </div>
    </div>
  );
}