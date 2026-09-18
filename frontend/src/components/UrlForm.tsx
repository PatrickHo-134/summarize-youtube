import React, { useState } from "react";
import { Link, ArrowRight, Loader2 } from "lucide-react";

interface UrlFormProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

export const UrlForm: React.FC<UrlFormProps> = ({ onSubmit, isLoading }) => {
  const [url, setUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url);
    }
  };

  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs px-3 py-1">
        ✨ Less watching. More knowing.
      </span>

      <div className="space-y-3">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900">
          Turn videos into useful notes.
        </h1>
        <p className="text-gray-500 text-sm sm:text-base max-w-md mx-auto">
          Paste any YouTube link and get a clean, structured summary in seconds.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-xl">
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white shadow-sm p-1.5">
          <div className="pl-3 flex items-center pointer-events-none text-gray-400 flex-shrink-0">
            <Link className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste a YouTube URL..."
            disabled={isLoading}
            className="flex-1 bg-transparent text-gray-900 text-sm outline-none placeholder-gray-400 disabled:opacity-60 min-w-0"
          />
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-full px-5 py-2.5 disabled:bg-indigo-300 disabled:cursor-not-allowed transition flex-shrink-0 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Summarizing...</span>
              </>
            ) : (
              <>
                <span>Summarize</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
