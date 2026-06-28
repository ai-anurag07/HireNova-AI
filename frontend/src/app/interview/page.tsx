"use client";

import { useState, useRef } from "react";
import { api } from "@/lib/api";
import { Mic, Square, Play, ArrowLeft, User, Bot, CheckCircle, MessageSquare, Send } from "lucide-react";
import Link from "next/link";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

export default function InterviewPage() {
  const [mode, setMode] = useState<"voice" | "chat">("voice");
  const [jdText, setJdText] = useState("");

  // Voice State
  const [status, setStatus] = useState<"setup" | "loading_q" | "interviewing" | "grading" | "finished">("setup");
  const [questionText, setQuestionText] = useState("");
  const [aiAudioUrl, setAiAudioUrl] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const [evaluation, setEvaluation] = useState<any>(null);
  const [userTranscript, setUserTranscript] = useState("");

  // Chat State
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);

  // --- VOICE FUNCTIONS ---
  const startVoiceInterview = async () => {
    if (!jdText) return;
    setStatus("loading_q");
    try {
      const formData = new FormData();
      formData.append("jd_text", jdText);
      const res = await api.post("/interview/ask", formData);
      setQuestionText(res.data.question_text);
      setAiAudioUrl(res.data.audio_download_url);
      const audio = new Audio(res.data.audio_download_url);
      audio.play();
      setStatus("interviewing");
    } catch (err) {
      alert("Failed to start. Did you upload a master resume?");
      setStatus("setup");
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mediaRecorder.onstop = submitAnswer;
      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) { alert("Microphone access denied."); }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      setStatus("grading");
    }
  };

  const submitAnswer = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("question_text", questionText);
    formData.append("audio_file", audioBlob, "answer.webm");
    try {
      const res = await api.post("/interview/answer", formData);
      setUserTranscript(res.data.your_transcript);
      setEvaluation(res.data.evaluation);
      setStatus("finished");
    } catch (err) {
      alert("Failed to grade answer.");
      setStatus("interviewing");
    }
  };

  // --- CHAT FUNCTIONS ---
  const startPrepChat = async () => {
    if (!jdText) return;
    setIsChatLoading(true);
    // The very first automatic message
    const initialMsg: ChatMsg = { role: "user", content: "Hi! Can you give me 3 highly likely interview questions for this JD, along with complete, word-for-word ideal answer scripts based on my resume?" };

    try {
      const res = await api.post("/interview/prep-chat", { jd_text: jdText, messages: [initialMsg] });
      setChatMessages([{ role: "user", content: "Please generate my prep questions." }, { role: "assistant", content: res.data.reply }]);
    } catch (err) {
      alert("Failed to start chat.");
    } finally {
      setIsChatLoading(false);
    }
  };

  const sendChatMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const newMsg: ChatMsg = { role: "user", content: chatInput };
    const newHistory = [...chatMessages, newMsg];
    setChatMessages(newHistory);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const res = await api.post("/interview/prep-chat", { jd_text: jdText, messages: newHistory });
      setChatMessages([...newHistory, { role: "assistant", content: res.data.reply }]);
    } catch (err) {
      alert("Message failed to send.");
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        
        <Link href="/" className="flex items-center text-blue-600 hover:text-blue-800 font-medium">
          <ArrowLeft size={20} className="mr-2" /> Back to Dashboard
        </Link>

        <div className="flex justify-between items-end">
          <h1 className="text-3xl font-bold text-gray-800 flex items-center">
            <Mic className="mr-3 text-purple-600" size={32} /> Interview Studio
          </h1>
          
          {/* 🌟 NEW: TABS TO SWITCH MODES */}
          <div className="bg-gray-200 p-1 rounded-lg flex gap-1">
            <button 
              onClick={() => setMode("voice")}
              className={`px-4 py-2 rounded-md font-bold text-sm transition ${mode === "voice" ? "bg-white text-purple-700 shadow-sm" : "text-gray-600 hover:bg-gray-300"}`}
            >
              🎙️ Voice Mock
            </button>
            <button 
              onClick={() => setMode("chat")}
              className={`px-4 py-2 rounded-md font-bold text-sm transition ${mode === "chat" ? "bg-white text-blue-700 shadow-sm" : "text-gray-600 hover:bg-gray-300"}`}
            >
              💬 Prep Chat
            </button>
          </div>
        </div>

        {/* SHARED JD INPUT */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold text-gray-800 mb-2">Target Job Description</h2>
          <textarea 
         rows={3}
         value={jdText}
         onChange={(e) => setJdText(e.target.value)}
         className="w-full p-3 border border-gray-300 rounded-md focus:ring-purple-500 focus:border-purple-500 mb-4 text-gray-900 bg-white"
         placeholder="Paste the Job Description here..."
       />
          {mode === "voice" && status === "setup" && (
            <button onClick={startVoiceInterview} disabled={!jdText} className="w-full bg-purple-600 text-white py-3 rounded-md hover:bg-purple-700 font-bold disabled:bg-gray-300">
              Start Voice Interview
            </button>
          )}
          {mode === "chat" && chatMessages.length === 0 && (
            <button onClick={startPrepChat} disabled={!jdText || isChatLoading} className="w-full bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700 font-bold disabled:bg-gray-300">
              {isChatLoading ? "Generating Prep Guide..." : "Generate Prep & Start Chat"}
            </button>
          )}
        </div>

        {/* --- VOICE MODE UI --- */}
        {mode === "voice" && (
          <div className="space-y-6">
            {status === "loading_q" && <div className="text-center py-10 animate-pulse text-purple-600 font-bold">Preparing question...</div>}
            
            {status === "interviewing" && (
              <div className="bg-white p-8 rounded-xl shadow-sm border border-purple-200 text-center">
                <p className="text-xl font-medium text-gray-800 mb-6">"{questionText}"</p>
                <audio controls src={aiAudioUrl} className="mx-auto mb-6 h-8" />
                {!isRecording ? (
                  <button onClick={startRecording} className="mx-auto bg-red-500 text-white rounded-full w-20 h-20 flex items-center justify-center shadow-lg"><Mic size={32} /></button>
                ) : (
                  <button onClick={stopRecording} className="mx-auto bg-gray-800 text-white rounded-full w-20 h-20 flex items-center justify-center shadow-lg animate-pulse"><Square size={28} /></button>
                )}
                <p className="mt-4 text-sm font-bold text-red-500">{isRecording ? "Recording... Click to Stop" : "Click to Record Answer"}</p>
              </div>
            )}

            {status === "grading" && <div className="text-center py-10 animate-pulse text-purple-600 font-bold">Evaluating answer...</div>}

            {status === "finished" && evaluation && (
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <h2 className="text-2xl font-bold mb-4 flex items-center"><CheckCircle className="mr-2 text-green-500" /> Score: {evaluation.score}/10</h2>
                <p className="italic text-gray-600 mb-4">"{userTranscript}"</p>
                <div className="space-y-4">
                  <div><h3 className="font-bold">Feedback</h3><p className="text-sm">{evaluation.feedback}</p></div>
                  <div className="bg-blue-50 p-4 rounded-lg">
    <h3 className="font-bold text-blue-800">Ideal Answer</h3>
    <p className="text-sm text-blue-900">{evaluation.ideal_answer}</p>
</div>
                </div>
                <button onClick={() => setStatus("setup")} className="mt-6 w-full bg-purple-100 text-purple-700 py-2 rounded-md font-bold">Try Another Question</button>
              </div>
            )}
          </div>
        )}

        {/* --- CHAT MODE UI --- */}
        {mode === "chat" && chatMessages.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[500px]">
            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] p-3 rounded-xl whitespace-pre-wrap text-sm ${msg.role === "user" ? "bg-blue-600 text-white rounded-br-none" : "bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm"}`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 text-gray-500 p-3 rounded-xl rounded-bl-none text-sm animate-pulse flex items-center">
                    <Bot size={16} className="mr-2" /> Thinking...
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <form onSubmit={sendChatMessage} className="p-4 bg-white border-t border-gray-200 flex gap-2">
              <input 
             type="text" 
             value={chatInput}
             onChange={(e) => setChatInput(e.target.value)}
             placeholder="Ask for advice, rephrase an answer, or ask another question..."
             className="flex-1 px-4 py-2 border border-gray-300 rounded-full focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-900 bg-white"
             disabled={isChatLoading}
           />
              <button 
                type="submit" 
                disabled={isChatLoading || !chatInput.trim()}
                className="bg-blue-600 text-white w-10 h-10 rounded-full flex items-center justify-center hover:bg-blue-700 transition disabled:bg-gray-300"
              >
                <Send size={18} />
              </button>
            </form>
          </div>
        )}

      </div>
    </div>
  );
}