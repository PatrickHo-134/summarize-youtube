import { useState, useEffect } from "react";
import type { AppView } from "./types";
import { useSummarize } from "./hooks/useSummarize";
import { Navbar } from "./components/Navbar";
import { UrlForm } from "./components/UrlForm";
import { SummaryViewer } from "./components/SummaryViewer";
import { ActionControls } from "./components/ActionControls";
import { AuthModal } from "./components/AuthModal";
import { HistoryList } from "./components/HistoryList";
import { useHistory } from "./hooks/useHistory";

export function App() {
  const { loading, error, data, needsAuth, setNeedsAuth, submitUrl } =
    useSummarize();
  const {
    items: historyItems,
    isLoading: historyLoading,
    error: historyError,
    fetch: fetchHistory,
  } = useHistory();
  const [pendingUrl, setPendingUrl] = useState<string>("");
  const [view, setView] = useState<AppView>("new");

  useEffect(() => {
    if (view === "dashboard") {
      fetchHistory();
    }
  }, [view, fetchHistory]);

  const handleSubmit = (url: string) => {
    setPendingUrl(url);
    submitUrl(url);
  };

  const handleAuthSuccess = () => {
    setNeedsAuth(false);
    submitUrl(pendingUrl);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900">
      <Navbar view={view} onViewChange={setView} />
      <div className="max-w-3xl mx-auto space-y-8 py-12 px-4 sm:px-6 lg:px-8">
        {view === "new" && (
          <>
            <UrlForm onSubmit={handleSubmit} isLoading={loading} />

            {loading && (
              <div className="p-8 text-center text-gray-500 animate-pulse bg-white border border-gray-200 rounded-2xl shadow-sm">
                Fetching transcript and generating summary...
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
          </>
        )}

        {view === "dashboard" && (
          <HistoryList
            items={historyItems}
            isLoading={historyLoading}
            error={historyError}
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
