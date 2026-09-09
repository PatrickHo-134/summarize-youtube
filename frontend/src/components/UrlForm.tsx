import React, { useState } from 'react';
import { FaYoutube } from 'react-icons/fa';
import { Loader2, Sparkles } from 'lucide-react';

interface UrlFormProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

export const UrlForm: React.FC<UrlFormProps> = ({ onSubmit, isLoading }) => {
  const [url, setUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
      <div className="relative flex-1">
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
          <FaYoutube className="w-5 h-5 text-red-500" />
        </div>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste YouTube URL (e.g., https://www.youtube.com/watch?v=...)"
          disabled={isLoading}
          className="w-full pl-11 pr-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition disabled:opacity-60 text-sm sm:text-base shadow-sm"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !url.trim()}
        className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl disabled:bg-indigo-300 disabled:cursor-not-allowed transition shadow-sm cursor-pointer whitespace-nowrap"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Summarizing...</span>
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            <span>Summarize</span>
          </>
        )}
      </button>
    </form>
  );
};