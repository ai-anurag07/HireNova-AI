"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Link from "next/link";
export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      // Create the special form data Swagger uses
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      // Talk to our Python backend!
      const response = await api.post("/auth/login", formData);
      
      // Save the VIP token to the browser's memory
      localStorage.setItem("token", response.data.access_token);
      
      // Go to the dashboard!
      router.push("/");
    } catch (err) {
      setError("Invalid email or password. Try again!");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-xl shadow-lg w-96">
        <h1 className="text-2xl font-bold text-center mb-6 text-blue-600">HireNova</h1>
        <h2 className="text-lg font-semibold text-center mb-6 text-gray-700">Welcome Back</h2>
        
        {error && <div className="bg-red-100 text-red-600 p-2 rounded mb-4 text-sm text-center">{error}</div>}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input 
              type="email" 
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input 
              type="password" 
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button 
            type="submit" 
            className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 transition font-bold"
          >
            Log In
          </button>
        </form>
        
        {/* 🌟 NEW: Link to the registration page */}
        <div className="mt-4 text-center text-sm">
          <Link href="/register" className="text-blue-600 hover:underline">Don't have an account? Sign up.</Link>
        </div>

      </div>
    </div>
  );
}