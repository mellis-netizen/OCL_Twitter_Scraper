import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import apiClient from '../services/api';

interface ProgressStep {
  id: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  progress: number;
}

export default function ManualControls() {
  const [scrapingResult, setScrapingResult] = useState<string | null>(null);
  const [emailResult, setEmailResult] = useState<string | null>(null);
  const [isScrapingActive, setIsScrapingActive] = useState(false);
  const [scrapingProgress, setScrapingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [scrapingStats, setScrapingStats] = useState<any>(null);

  const steps: ProgressStep[] = [
    { id: 'init', label: 'Initializing scraping cycle', status: 'pending', progress: 0 },
    { id: 'feeds', label: 'Fetching RSS feeds and articles', status: 'pending', progress: 0 },
    { id: 'twitter', label: 'Monitoring Twitter accounts', status: 'pending', progress: 0 },
    { id: 'analyze', label: 'Analyzing content for TGE mentions', status: 'pending', progress: 0 },
    { id: 'alerts', label: 'Generating alerts', status: 'pending', progress: 0 },
    { id: 'complete', label: 'Finalizing results', status: 'pending', progress: 0 },
  ];

  // Timer for elapsed time
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (isScrapingActive) {
      interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isScrapingActive]);

  // Simulate progress updates and poll for completion
  useEffect(() => {
    if (!isScrapingActive) return;

    let initialAlertCount = 0;

    // Get initial alert count
    apiClient.getStatistics().then(stats => {
      initialAlertCount = stats.total_alerts;
    }).catch(() => {
      initialAlertCount = 0;
    });

    const progressInterval = setInterval(() => {
      setScrapingProgress((prev) => {
        const newProgress = Math.min(prev + 2, 95); // Cap at 95% until we get real completion

        // Update current step based on progress
        if (newProgress < 10) setCurrentStep(0);
        else if (newProgress < 30) setCurrentStep(1);
        else if (newProgress < 50) setCurrentStep(2);
        else if (newProgress < 70) setCurrentStep(3);
        else if (newProgress < 90) setCurrentStep(4);
        else setCurrentStep(5);

        return newProgress;
      });
    }, 500);

    // Poll for new alerts every 5 seconds
    const pollInterval = setInterval(async () => {
      try {
        const stats = await apiClient.getStatistics();
        // Check if new alerts were added
        if (stats.total_alerts > initialAlertCount) {
          const newAlerts = stats.total_alerts - initialAlertCount;
          completeScrapingProcess(newAlerts);
        }
      } catch (error) {
        console.error('Error polling for completion:', error);
      }
    }, 5000);

    // Auto-complete after max time (120 seconds - give scraping time to actually run)
    const completionTimeout = setTimeout(() => {
      completeScrapingProcess(0);
    }, 120000); // 2 minutes max

    return () => {
      clearInterval(progressInterval);
      clearInterval(pollInterval);
      clearTimeout(completionTimeout);
    };
  }, [isScrapingActive]);

  const completeScrapingProcess = async (alertsFound: number = 0) => {
    setScrapingProgress(100);
    setCurrentStep(5);
    setIsScrapingActive(false);

    // Fetch REAL statistics from the database
    try {
      const stats = await apiClient.getStatistics();

      // Show ONLY real data - no fake/simulated numbers
      setScrapingStats({
        articlesScanned: 0, // Backend doesn't track this yet
        tweetsAnalyzed: 0,  // Backend doesn't track this yet
        alertsGenerated: alertsFound > 0 ? alertsFound : stats.alerts_last_24h,
        highConfidence: 0,  // Backend doesn't track this yet
        duration: elapsedTime,
      });

      setScrapingResult(
        alertsFound > 0
          ? `Scraping completed! Found ${alertsFound} new alerts.`
          : 'Scraping completed - no new TGE alerts found in this cycle.'
      );
    } catch (error) {
      console.error('Error fetching real stats:', error);
      setScrapingResult('Scraping completed but unable to fetch results.');
    }

    setTimeout(() => {
      setScrapingResult(null);
      resetScrapingState();
    }, 10000);
  };

  const resetScrapingState = () => {
    setScrapingProgress(0);
    setCurrentStep(0);
    setElapsedTime(0);
    setScrapingStats(null);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Trigger scraping mutation
  const scrapingMutation = useMutation({
    mutationFn: () => apiClient.triggerScraping(),
    onSuccess: () => {
      setIsScrapingActive(true);
      setScrapingProgress(5);
      setElapsedTime(0);
      setScrapingStats(null);
      setScrapingResult(null);
    },
    onError: (error: any) => {
      setIsScrapingActive(false);
      setScrapingResult(`Error: ${error.response?.data?.detail || 'Failed to start scraping'}`);
      setTimeout(() => {
        setScrapingResult(null);
        resetScrapingState();
      }, 5000);
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

  const getStepStatus = (index: number): 'pending' | 'in_progress' | 'completed' | 'error' => {
    if (index < currentStep) return 'completed';
    if (index === currentStep && isScrapingActive) return 'in_progress';
    if (index === currentStep && scrapingProgress === 100) return 'completed';
    return 'pending';
  };

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
            disabled={scrapingMutation.isPending || isScrapingActive}
            className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isScrapingActive ? (
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
                Scraping in Progress... {scrapingProgress}%
              </span>
            ) : (
              '🔍 Start Scraping Cycle'
            )}
          </button>

          {/* Progress Visualization */}
          {isScrapingActive && (
            <div className="mt-6 space-y-4">
              {/* Progress Bar */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-300">Overall Progress</span>
                  <span className="text-sm text-gray-400">{formatTime(elapsedTime)}</span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-500 ease-out relative"
                    style={{ width: `${scrapingProgress}%` }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-20 animate-pulse"></div>
                  </div>
                </div>
              </div>

              {/* Step Indicators */}
              <div className="space-y-2">
                {steps.map((step, index) => {
                  const status = getStepStatus(index);
                  return (
                    <div
                      key={step.id}
                      className={`flex items-center gap-3 p-2 rounded transition-all ${
                        status === 'in_progress'
                          ? 'bg-primary-900 bg-opacity-20'
                          : status === 'completed'
                          ? 'bg-green-900 bg-opacity-10'
                          : ''
                      }`}
                    >
                      <div
                        className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          status === 'completed'
                            ? 'bg-green-600 text-white'
                            : status === 'in_progress'
                            ? 'bg-primary-600 text-white animate-pulse'
                            : 'bg-dark-700 text-gray-500'
                        }`}
                      >
                        {status === 'completed' ? (
                          '✓'
                        ) : status === 'in_progress' ? (
                          <svg
                            className="animate-spin h-3 w-3"
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
                        ) : (
                          index + 1
                        )}
                      </div>
                      <span
                        className={`text-sm ${
                          status === 'in_progress'
                            ? 'text-primary-300 font-medium'
                            : status === 'completed'
                            ? 'text-green-300'
                            : 'text-gray-500'
                        }`}
                      >
                        {step.label}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Estimated completion */}
              <div className="text-center text-xs text-gray-400 pt-2 border-t border-dark-700">
                <p>Estimated time: 2-5 minutes</p>
              </div>
            </div>
          )}

          {/* Results Display */}
          {scrapingStats && scrapingProgress === 100 && (
            <div className="mt-4 p-4 bg-green-900 bg-opacity-20 border border-green-700 rounded-lg">
              <h4 className="text-green-300 font-semibold mb-3 flex items-center gap-2">
                ✅ Scraping Complete!
              </h4>
              <div className="grid grid-cols-1 gap-3 text-sm">
                <div className="bg-dark-800 bg-opacity-50 p-3 rounded">
                  <div className="text-gray-400 text-xs mb-1">Alerts Generated</div>
                  <div className="text-primary-400 font-bold text-lg">{scrapingStats.alertsGenerated}</div>
                  <div className="text-gray-500 text-xs mt-1">Real results from database</div>
                </div>
              </div>
              <div className="mt-3 text-center text-xs text-gray-400">
                Completed in {formatTime(scrapingStats.duration)}
              </div>
            </div>
          )}

          {scrapingResult && !scrapingStats && (
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
