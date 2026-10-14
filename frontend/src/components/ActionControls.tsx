import React from 'react';
import { Mail, RefreshCw } from 'lucide-react';

interface ActionControlsProps {
  status: 'success' | 'error';
  summaryText: string;
  errorMessage: string;
  onRetry: () => void;
}

export const ActionControls: React.FC<ActionControlsProps> = ({
  status,
  summaryText,
  errorMessage,
  onRetry,
}) => {
  const handleEmail = () => {
    const subject = encodeURIComponent('YouTube Video Summary');
    const body = encodeURIComponent(
      `Here is the summary of the YouTube video:\n\n${summaryText}`
    );
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  if (status === 'error') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-2xl p-4 sm:p-6 text-red-700 space-y-4">
        <div className="text-sm font-medium break-words">Error: {errorMessage}</div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={onRetry}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 sm:py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl transition cursor-pointer w-full sm:w-auto"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry Request</span>
          </button>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="flex flex-col sm:flex-row sm:justify-end gap-3 pt-2">
        <button
          onClick={handleEmail}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-xl shadow-sm transition cursor-pointer w-full sm:w-auto"
        >
          <Mail className="w-4 h-4" />
          <span>Send to Email</span>
        </button>
      </div>
    );
  }

  return null;
};