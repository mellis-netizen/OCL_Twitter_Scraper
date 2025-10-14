import { useState, useMemo, useCallback, memo } from 'react';
import { useAlerts } from '../hooks/useAlerts';
import { useDebounce } from '../hooks/useDebounce';
import { formatRelativeTime, getConfidenceColor, getUrgencyColor, truncate } from '../utils/helpers';
import type { AlertFilter, AlertNotification, AlertResponse } from '../types/api';

/**
 * Optimized Alert Card Component with React.memo
 * Only re-renders when alert data actually changes
 */
const AlertCard = memo(({ alert }: { alert: AlertResponse }) => {
  return (
    <div className="bg-dark-800 rounded-lg p-4 border border-dark-700 hover:border-primary-500 transition-colors">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-1">{alert.title}</h3>
          <p className="text-sm text-gray-400">{truncate(alert.content, 200)}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span
            className={`px-2 py-1 rounded text-xs ${getUrgencyColor(alert.urgency_level)}`}
          >
            {alert.urgency_level.toUpperCase()}
          </span>
          <span className={`text-sm font-medium ${getConfidenceColor(alert.confidence)}`}>
            {Math.round(alert.confidence * 100)}%
          </span>
        </div>
      </div>

      {alert.company && (
        <div className="mb-2">
          <span className="px-2 py-1 bg-primary-900 text-primary-200 rounded text-xs">
            {alert.company.name}
          </span>
        </div>
      )}

      {alert.keywords_matched && alert.keywords_matched.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {alert.keywords_matched.slice(0, 5).map((keyword, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 bg-dark-700 text-gray-300 rounded text-xs"
            >
              {keyword}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-dark-700">
        <div className="flex items-center gap-4">
          <span>Source: {alert.source}</span>
          {alert.source_url && (
            <a
              href={alert.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-400 hover:underline"
            >
              View Source →
            </a>
          )}
        </div>
        <span>{formatRelativeTime(alert.created_at)}</span>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function - only re-render if these properties change
  return (
    prevProps.alert.id === nextProps.alert.id &&
    prevProps.alert.status === nextProps.alert.status &&
    prevProps.alert.urgency_level === nextProps.alert.urgency_level
  );
});

AlertCard.displayName = 'AlertCard';

/**
 * Optimized Real-time Alert Component
 */
const RealtimeAlert = memo(({ alert }: { alert: AlertNotification }) => {
  return (
    <div className="bg-dark-800 rounded p-3 border border-primary-600 animate-pulse-slow">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h4 className="font-medium text-white">{alert.title}</h4>
          {alert.company_name && (
            <p className="text-sm text-gray-400 mt-1">{alert.company_name}</p>
          )}
        </div>
        <span
          className={`px-2 py-1 rounded text-xs ${getUrgencyColor(alert.urgency_level)}`}
        >
          {alert.urgency_level.toUpperCase()}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
        <span>Confidence: {Math.round(alert.confidence * 100)}%</span>
        <span>Source: {alert.source}</span>
        <span>{formatRelativeTime(alert.created_at)}</span>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  return prevProps.alert.alert_id === nextProps.alert.alert_id;
});

RealtimeAlert.displayName = 'RealtimeAlert';

/**
 * Optimized Filter Component
 */
const FilterPanel = memo(({ filter, onFilterChange }: {
  filter: AlertFilter;
  onFilterChange: (key: keyof AlertFilter, value: any) => void;
}) => {
  return (
    <div className="bg-dark-800 rounded-lg p-4 border border-dark-700">
      <h3 className="text-lg font-semibold text-white mb-3">Filters</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Source</label>
          <select
            value={filter.source || ''}
            onChange={(e) => onFilterChange('source', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white text-sm"
          >
            <option value="">All Sources</option>
            <option value="twitter">Twitter</option>
            <option value="news">News</option>
            <option value="manual">Manual</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Urgency</label>
          <select
            value={filter.urgency_level || ''}
            onChange={(e) => onFilterChange('urgency_level', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white text-sm"
          >
            <option value="">All Urgency Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Min Confidence</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={filter.min_confidence || ''}
            onChange={(e) =>
              onFilterChange(
                'min_confidence',
                e.target.value ? parseFloat(e.target.value) : undefined
              )
            }
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded text-white text-sm"
            placeholder="0.0 - 1.0"
          />
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Only re-render if filter actually changes
  return JSON.stringify(prevProps.filter) === JSON.stringify(nextProps.filter);
});

FilterPanel.displayName = 'FilterPanel';

/**
 * Main Optimized Alert Dashboard Component
 */
export default function AlertDashboard() {
  const [filter, setFilter] = useState<AlertFilter>({ limit: 50 });

  // Debounce filter changes to avoid excessive API calls
  const debouncedFilter = useDebounce(filter, 500);

  // Fetch alerts with debounced filter
  const { alerts, realtimeAlerts, isLoading, refetch } = useAlerts(debouncedFilter);

  // Memoized filter change handler
  const handleFilterChange = useCallback((key: keyof AlertFilter, value: any) => {
    setFilter((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Memoized refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Memoize realtime alerts slice to avoid recalculation
  const visibleRealtimeAlerts = useMemo(
    () => realtimeAlerts.slice(0, 5),
    [realtimeAlerts]
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Alert Dashboard</h2>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-dark-700 text-gray-300 rounded-lg hover:bg-dark-600 transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Real-time Alerts */}
      {visibleRealtimeAlerts.length > 0 && (
        <div className="bg-primary-900 bg-opacity-30 border border-primary-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-primary-300 mb-3">
            🔴 Live Alerts ({realtimeAlerts.length})
          </h3>
          <div className="space-y-2">
            {visibleRealtimeAlerts.map((alert, idx) => (
              <RealtimeAlert key={alert.alert_id || idx} alert={alert} />
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <FilterPanel filter={filter} onFilterChange={handleFilterChange} />

      {/* Alerts List */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading alerts...</div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          No alerts found matching your filters.
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
