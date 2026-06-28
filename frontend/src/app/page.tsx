"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Search, Mic, LayoutDashboard } from "lucide-react";

export default function Dashboard() {
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    // Check if the user has a VIP token! If not, kick them back to login.
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  // This stops the page from flashing before checking the token
  if (!isClient) return null;

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <header className="flex justify-between items-center mb-12">
          <h1 className="text-3xl font-bold text-blue-600">HireNova Dashboard</h1>
          <button 
            onClick={handleLogout}
            className="text-gray-500 hover:text-red-500 font-medium transition"
          >
            Log Out
          </button>
        </header>

        {/* The 3 Main Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Card 1: Resume */}
          <Link href="/resume">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:-translate-y-1 transition duration-200 cursor-pointer">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-4">
              <FileText size={24} />
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">1. Resume AI</h2>
            <p className="text-gray-600">Upload your master resume and generate tailored, ATS-friendly PDFs.</p>
          </div>
          </Link>

          {/* Card 2: Jobs */}
          <Link href="/jobs">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:-translate-y-1 transition duration-200 cursor-pointer h-full">
              <div className="w-12 h-12 bg-green-100 text-green-600 rounded-lg flex items-center justify-center mb-4">
                <Search size={24} />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">2. Job Search</h2>
              <p className="text-gray-600">Use the Ghost Browser to scrape live jobs based on your criteria.</p>
            </div>
          </Link>

          {/* Card 3: Interview */}
          <Link href="/interview">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:-translate-y-1 transition duration-200 cursor-pointer h-full">
              <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-4">
                <Mic size={24} />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">3. AI Interviewer</h2>
              <p className="text-gray-600">Practice with a realistic voice AI that listens and grades your answers.</p>
            </div>
          </Link>

          {/* Card 4: Tracker */}
       <Link href="/tracker">
         <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-lg hover:-translate-y-1 transition duration-200 cursor-pointer h-full">
           <div className="w-12 h-12 bg-orange-100 text-orange-500 rounded-lg flex items-center justify-center mb-4">
             <LayoutDashboard size={24} />
           </div>
           <h2 className="text-xl font-bold text-gray-800 mb-2">4. App Tracker</h2>
           <p className="text-gray-600">Drag and drop your saved jobs to track your application progress.</p>
         </div>
       </Link>

        </div>
      </div>
    </div>
  );
}