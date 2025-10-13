import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import apiClient from '../services/api';

export default function ManualControls() {
  const [scrapingResult, setScrapingResult] = useState<string | null>(null);
  const [emailResult, setEmailResult] = useState<string | null>(null);

  // Trigger scraping mutation
  const scrapingMutation = useMutation({
    mutationFn: () => apiClient.triggerScraping(),
    onSuccess: (data) => {
      setScrapingResult(`Scraping started successfully! Session ID: ${data.session_id}`);
      setTimeout(() => setScrapingResult(null), 5000);
    },
    onError: (error: any) => {
      setScrapingResult(`Error: ${error.response?.data?.detail || 'Failed to start scraping'}`);
      setTimeout(() => setScrapingResult(null), 5000);
    },
  });

  // Send email mutation
  const emailMutation = useMutation({
    mutationFn: () => apiClient.sendEmailSummary(),
    onSuccess: (data) => {
      setEmailResult(data.message || 'Email sent successfully!');
      setTimeout(() => setEmailResult(null), 5000);
    },
    onError: (error: any) => {
      setEmailResult(`Error: ${error.response?.data?.detail || 'Failed to send email'}`);
      setTimeout(() => setEmailResult(null), 5000);
    },
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Manual Controls</h2>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Scraping Control */}
        <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white mb-2">Trigger Scraping Cycle</h3>
            <p className="text-sm text-gray-400">
              Manually start a complete scraping cycle for all configured news sources and Twitter
              accounts. This will check for new TGE-related content and generate alerts.
            </p>
          </div>

          <button
            onClick={() => scrapingMutation.mutate()}
            disabled={scrapingMutation.isPending}
            className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {scrapingMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Starting Scraping...
              </span>
            ) : (
              '🔍 Start Scraping Cycle'
            )}
          </button>

          {scrapingResult && (
            <div
              className={`mt-4 p-3 rounded ${
                scrapingResult.startsWith('Error')
                  ? 'bg-red-900 bg-opacity-30 border border-red-700 text-red-200'
                  : 'bg-green-900 bg-opacity-30 border border-green-700 text-green-200'
              }`}
            >
              {scrapingResult}
            </div>
          )}

          <div className="mt-4 text-xs text-gray-500">
            <p className="font-semibold mb-1">What this does:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Fetches latest content from all active RSS feeds</li>
              <li>Monitors configured Twitter accounts for new tweets</li>
              <li>Analyzes content for TGE-related keywords and company mentions</li>
              <li>Generates alerts for high-confidence matches</li>
              <li>Updates feed statistics and performance metrics</li>
            </ul>
          </div>
        </div>

        {/* Email Summary Control */}
        <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-white mb-2">Send Email Summary</h3>
            <p className="text-sm text-gray-400">
              Manually send an email summary of recent TGE alerts to configured recipients. This
              includes all high-priority alerts from the last 24 hours.
            </p>
          </div>

          <button
            onClick={() => emailMutation.mutate()}
            disabled={emailMutation.isPending}
            className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {emailMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Sending Email...
              </span>
            ) : (
              '📧 Send Email Summary'
            )}
          </button>

          {emailResult && (
            <div
              className={`mt-4 p-3 rounded ${
                emailResult.startsWith('Error')
                  ? 'bg-red-900 bg-opacity-30 border border-red-700 text-red-200'
                  : 'bg-green-900 bg-opacity-30 border border-green-700 text-green-200'
              }`}
            >
              {emailResult}
            </div>
          )}

          <div className="mt-4 text-xs text-gray-500">
            <p className="font-semibold mb-1">Email includes:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Summary of alerts from last 24 hours</li>
              <li>High-priority TGE announcements</li>
              <li>Company-specific updates</li>
              <li>Confidence scores and urgency levels</li>
              <li>Direct links to source articles/tweets</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Status Information */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h3 className="text-lg font-semibold text-white mb-3">ℹ️ Information</h3>
        <div className="space-y-2 text-sm text-gray-400">
          <p className="text-yellow-500">
            ⚠️ <strong>Note:</strong> Frequent manual scraping may trigger rate limits on external
            sources. Use scheduled monitoring for regular updates.
          </p>
        </div>
      </div>
    </div>
  );
}
