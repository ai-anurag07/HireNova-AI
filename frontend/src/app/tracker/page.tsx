"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ArrowLeft, LayoutDashboard, Building, MapPin, ExternalLink, Trash2, BookOpen, X } from "lucide-react";
import Link from "next/link";

interface Application {
  id: string;
  title: string;
  company: string;
  location: string;
  apply_url: string;
  status: string;
}

const COLUMNS = [
  { id: "saved", title: "📑 Saved" },
  { id: "applied", title: "📤 Applied" },
  { id: "interviewing", title: "🎙️ Interviewing" },
  { id: "offer", title: "🎉 Offer" },
  { id: "rejected", title: "❌ Rejected" },
];

export default function TrackerPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [researchBrief, setResearchBrief] = useState("");
  const [isResearching, setIsResearching] = useState(false);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    try {
      const res = await api.get("/jobs/applications");
      setApps(res.data);
    } catch (err) {
      console.error("Failed to fetch applications", err);
    } finally {
      setLoading(false);
    }
  };

  // --- HTML5 Drag and Drop Handlers ---
  const handleDragStart = (e: React.DragEvent, appId: string) => {
    e.dataTransfer.setData("appId", appId);
  };

  const handleDrop = async (e: React.DragEvent, newStatus: string) => {
    e.preventDefault();
    const appId = e.dataTransfer.getData("appId");
    if (!appId) return;

    // 1. Update the UI instantly so it feels fast
    setApps((prevApps) => 
      prevApps.map((app) => app.id === appId ? { ...app, status: newStatus } : app)
    );

    // 2. Tell the Python backend to update the database
    try {
      await api.put(`/jobs/track/${appId}`, { status: newStatus });
    } catch (err) {
      alert("Failed to update status in database.");
      fetchApplications(); // Revert if it fails
    }
  };
  const handleDelete = async (appId: string) => {
    const confirmDelete = window.confirm("Are you sure you want to remove this job from your tracker?");
    if (!confirmDelete) return;

    try {
      await api.delete(`/jobs/track/${appId}`);
      // Remove it from the screen instantly
      setApps((prev) => prev.filter((app) => app.id !== appId));
    } catch (err) {
      alert("Failed to delete job.");
    }
  };
  const handleResearch = async (company: string, title: string) => {
    setIsResearching(true);
    setResearchBrief("");
    setShowModal(true);
    
    try {
      const res = await api.get(`/jobs/research?company=${encodeURIComponent(company)}&role=${encodeURIComponent(title)}`);
      setResearchBrief(res.data.brief);
    } catch (err) {
      setResearchBrief("❌ Failed to fetch company research. Please try again.");
    } finally {
      setIsResearching(false);
    }
  };
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault(); // Required to allow dropping
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        <Link href="/" className="flex items-center text-blue-600 hover:text-blue-800 font-medium">
          <ArrowLeft size={20} className="mr-2" /> Back to Dashboard
        </Link>

        <h1 className="text-3xl font-bold text-gray-800 flex items-center">
          <LayoutDashboard className="mr-3 text-orange-500" size={32} /> Application Tracker
        </h1>

        {loading ? (
          <p className="text-gray-500">Loading your saved jobs...</p>
        ) : (
          <div className="flex gap-6 overflow-x-auto pb-8 h-[70vh]">
            {COLUMNS.map((col) => (
              <div 
                key={col.id}
                onDrop={(e) => handleDrop(e, col.id)}
                onDragOver={handleDragOver}
                className="bg-gray-100 rounded-xl p-4 min-w-[300px] w-[300px] flex flex-col border border-gray-200 shadow-inner"
              >
                <h2 className="font-bold text-gray-700 mb-4 border-b-2 border-gray-200 pb-2">{col.title}</h2>
                
                <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                  {apps.filter((app) => app.status === col.id).map((app) => (
                    <div 
                      key={app.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, app.id)}
                      className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 cursor-grab active:cursor-grabbing hover:shadow-md transition"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-bold text-gray-800 text-sm pr-2">{app.title}</h3>
                        <div className="flex gap-2">
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleResearch(app.company, app.title); }}
                            className="text-blue-400 hover:text-blue-600 transition"
                            title="Research Company"
                          >
                            <BookOpen size={16} />
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleDelete(app.id); }}
                            className="text-gray-400 hover:text-red-500 transition"
                            title="Unsave Job"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                      <p className="text-gray-600 text-xs flex items-center mb-1">
                        <Building size={12} className="mr-1" /> {app.company}
                      </p>
                      <p className="text-gray-500 text-xs flex items-center mb-3">
                        <MapPin size={12} className="mr-1" /> {app.location}
                      </p>
                      <a 
                        href={app.apply_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 font-bold hover:underline flex items-center"
                      >
                        Job Link <ExternalLink size={12} className="ml-1" />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
      {/* RESEARCH MODAL OVERLAY */}
        {showModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
              <div className="flex justify-between items-center p-4 border-b border-gray-200 bg-gray-50">
                <h2 className="text-lg font-bold text-gray-800 flex items-center">
                  <BookOpen className="mr-2 text-blue-600" size={20} /> Company Cheat Sheet
                </h2>
                <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-800">
                  <X size={24} />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1 text-gray-700 whitespace-pre-wrap leading-relaxed">
                {isResearching ? (
                  <div className="flex flex-col items-center justify-center py-10 animate-pulse">
                    <BookOpen size={48} className="text-blue-300 mb-4" />
                    <p className="text-blue-600 font-medium">AI is analyzing the company...</p>
                  </div>
                ) : (
                  researchBrief
                )}
              </div>
            </div>
          </div>
        )}
    </div>
  );
}