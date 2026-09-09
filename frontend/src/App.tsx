import { useSummarize } from './hooks/useSummarize';
import { UrlForm } from './components/UrlForm';
import { SummaryViewer } from './components/SummaryViewer';
import { ActionControls } from './components/ActionControls';

export function App() {
  const { status, summary, source, errorMessage, summarize, retry } = useSummarize();

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <header className="text-center space-y-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900">
            YouTube Video Summarizer
          </h1>
          <p className="text-gray-600 text-sm sm:text-base">
            Paste any YouTube video link to generate concise takeaways and key insights.
          </p>
        </header>

        {/* Input Form */}
        <UrlForm onSubmit={summarize} isLoading={status === 'loading'} />

        {/* Loading Indicator */}
        {status === 'loading' && (
          <div className="p-8 text-center text-gray-500 animate-pulse bg-white border border-gray-200 rounded-2xl shadow-sm">
            Fetching transcript and generating OpenAI summary...
          </div>
        )}

        {/* Results */}
        {status === 'success' && (
          <div className="space-y-4">
            <SummaryViewer summary={summary} source={source} />
            <ActionControls
              status={status}
              summaryText={summary}
              errorMessage={errorMessage}
              onRetry={retry}
            />
          </div>
        )}

        {/* Error Container */}
        {status === 'error' && (
          <ActionControls
            status={status}
            summaryText={summary}
            errorMessage={errorMessage}
            onRetry={retry}
          />
        )}
      </div>
    </div>
  );
}

export default App;