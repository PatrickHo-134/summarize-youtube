import { useState } from 'react';
import { useSummarize } from './hooks/useSummarize';
import { UrlForm } from './components/UrlForm';
import { SummaryViewer } from './components/SummaryViewer';
import { ActionControls } from './components/ActionControls';
import { AuthModal } from './components/AuthModal';

export function App() {
  const { loading, error, data, needsAuth, setNeedsAuth, submitUrl } = useSummarize();
  const [pendingUrl, setPendingUrl] = useState<string>('');

  const handleSubmit = (url: string) => {
    setPendingUrl(url);
    submitUrl(url);
  };

  const handleAuthSuccess = () => {
    setNeedsAuth(false);
    submitUrl(pendingUrl);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <header className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900">
            YouTube Video Summarizer
          </h1>
          <p className="text-gray-600 text-sm sm:text-base">
            Paste any YouTube video link to generate concise takeaways and key insights.
          </p>
        </header>

        <UrlForm onSubmit={handleSubmit} isLoading={loading} />

        {loading && (
          <div className="p-8 text-center text-gray-500 animate-pulse bg-white border border-gray-200 rounded-2xl shadow-sm">
            Fetching transcript and generating OpenAI summary...
          </div>
        )}

        {data && !loading && (
          <div className="space-y-4">
            <SummaryViewer summary={data.summary} source={data.source} />
            <ActionControls
              status="success"
              summaryText={data.summary}
              errorMessage=""
              onRetry={() => submitUrl(pendingUrl)}
            />
          </div>
        )}

        {error && !loading && (
          <ActionControls
            status="error"
            summaryText=""
            errorMessage={error}
            onRetry={() => submitUrl(pendingUrl)}
          />
        )}
      </div>

      <AuthModal
        isOpen={needsAuth}
        onClose={() => setNeedsAuth(false)}
        onSuccess={handleAuthSuccess}
      />
    </div>
  );
}

export default App;
