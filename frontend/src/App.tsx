import { useState, useEffect, useRef } from "react";
import { getCurrentUser } from "aws-amplify/auth";
import type { AppView } from "./types";
import { handleSignOut as authSignOut } from "./services/auth";
import { useSummarize } from "./hooks/useSummarize";
import { Navbar } from "./components/Navbar";
import { UrlForm } from "./components/UrlForm";
import { SummaryViewer } from "./components/SummaryViewer";
import { ActionControls } from "./components/ActionControls";
import { AuthModal } from "./components/AuthModal";
import { HistoryList } from "./components/HistoryList";
import { useHistory } from "./hooks/useHistory";

export function App() {
  const { loading, error, data, needsAuth, setNeedsAuth, sessionExpired: summarizeExpired, setSessionExpired: setSummarizeExpired, submitUrl, reset: resetSummarize } =
    useSummarize();
  const {
    items: historyItems,
    isLoading: historyLoading,
    isLoadingMore: historyLoadingMore,
    nextToken: historyNextToken,
    error: historyError,
    sessionExpired: historyExpired,
    setSessionExpired: setHistoryExpired,
    fetch: fetchHistory,
    fetchMore: fetchMoreHistory,
  } = useHistory();
  const [pendingUrl, setPendingUrl] = useState<string>("");
  const [view, setView] = useState<AppView>("new");
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const handlingExpiry = useRef(false);

  useEffect(() => {
    getCurrentUser()
      .then((user) => setUserEmail(user.signInDetails?.loginId ?? user.username))
      .catch(() => setUserEmail(null));
  }, []);

  useEffect(() => {
    if ((summarizeExpired || historyExpired) && !handlingExpiry.current) {
      handlingExpiry.current = true;
      authSignOut().finally(() => {
        setUserEmail(null);
        setView("new");
        setAuthMessage("Your session has expired. Please sign in again.");
        setNeedsAuth(true);
        setSummarizeExpired(false);
        setHistoryExpired(false);
        handlingExpiry.current = false;
      });
    }
  }, [summarizeExpired, historyExpired, setNeedsAuth, setSummarizeExpired, setHistoryExpired]);

  useEffect(() => {
    if (view === "dashboard") {
      fetchHistory();
    }
  }, [view, fetchHistory]);

  const handleSignOut = async () => {
    await authSignOut();
    resetSummarize();
    setPendingUrl("");
    setUserEmail(null);
    setView("new");
  };

  const handleLogin = () => {
    setAuthMessage(null);
    setNeedsAuth(true);
  };

  const handleSubmit = (url: string) => {
    setPendingUrl(url);
    submitUrl(url);
  };

  const handleAuthSuccess = () => {
    setNeedsAuth(false);
    setAuthMessage(null);
    submitUrl(pendingUrl);
    getCurrentUser()
      .then((user) => setUserEmail(user.signInDetails?.loginId ?? user.username))
      .catch(() => setUserEmail(null));
  };

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900">
      <Navbar view={view} onViewChange={setView} userEmail={userEmail} onSignOut={handleSignOut} onLogin={handleLogin} />
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
                <SummaryViewer summary={data.summary} source={data.source} title={data.title} />
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
            isLoadingMore={historyLoadingMore}
            nextToken={historyNextToken}
            onLoadMore={fetchMoreHistory}
            error={historyError}
          />
        )}
      </div>

      <AuthModal
        isOpen={needsAuth}
        onClose={() => { setNeedsAuth(false); setAuthMessage(null); }}
        onSuccess={handleAuthSuccess}
        message={authMessage}
      />
    </div>
  );
}

export default App;
