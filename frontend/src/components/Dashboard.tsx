import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../services/api';
import type { SystemStatistics, HealthCheck } from '../types/api';

export default function Dashboard() {
  const [seedResult, setSeedResult] = useState<any>(null);
  const queryClient = useQueryClient();

  // Fetch system statistics
  const { data: stats, isLoading: statsLoading } = useQuery<SystemStatistics>({
    queryKey: ['statistics'],
    queryFn: () => apiClient.getStatistics(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch health check
  const { data: health } = useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Seed data mutation
  const seedMutation = useMutation({
    mutationFn: () => apiClient.seedData(),
    onSuccess: (data) => {
      setSeedResult(data);
      // Refresh statistics
      queryClient.invalidateQueries({ queryKey: ['statistics'] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
    },
    onError: (error: any) => {
      setSeedResult({ success: false, error: error.message });
    }
  });

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  const statCards = [
    {
      label: 'Total Companies',
      value: stats?.total_companies || 0,
      icon: '🏢',
      color: 'from-blue-500 to-blue-600',
    },
    {
      label: 'Active Feeds',
      value: `${stats?.active_feeds || 0}/${stats?.total_feeds || 0}`,
      icon: '📰',
      color: 'from-green-500 to-green-600',
    },
    {
      label: 'Total Alerts',
      value: stats?.total_alerts || 0,
      icon: '🚨',
      color: 'from-red-500 to-red-600',
    },
    {
      label: 'Alerts (24h)',
      value: stats?.alerts_last_24h || 0,
      icon: '⏰',
      color: 'from-purple-500 to-purple-600',
    },
    {
      label: 'Alerts (7d)',
      value: stats?.alerts_last_7d || 0,
      icon: '📊',
      color: 'from-yellow-500 to-yellow-600',
    },
    {
      label: 'Avg Confidence',
      value: stats?.avg_confidence ? `${Math.round(stats.avg_confidence * 100)}%` : '0%',
      icon: '🎯',
      color: 'from-indigo-500 to-indigo-600',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-white mb-2">Dashboard Overview</h2>
        <p className="text-gray-400">
          Real-time monitoring of Token Generation Events across cryptocurrency projects
        </p>
      </div>

      {/* System Health Banner */}
      {health && (
        <div
          className={`p-4 rounded-lg border ${
            health.status === 'healthy'
              ? 'bg-green-900 bg-opacity-20 border-green-700'
              : 'bg-red-900 bg-opacity-20 border-red-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">
                {health.status === 'healthy' ? '✅' : '⚠️'}
              </span>
              <div>
                <h3
                  className={`font-semibold ${
                    health.status === 'healthy' ? 'text-green-300' : 'text-red-300'
                  }`}
                >
                  System Status: {health.status.toUpperCase()}
                </h3>
                <p className="text-sm text-gray-400">
                  All services operational - Last check: {new Date().toLocaleTimeString()}
                </p>
              </div>
            </div>
            <div className="flex gap-4 text-sm">
              <div className="text-center">
                <div className="text-gray-400">Database</div>
                <div className={health.database ? 'text-green-400' : 'text-red-400'}>
                  {health.database ? '✓ Online' : '✗ Offline'}
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Redis</div>
                <div className={health.redis ? 'text-green-400' : 'text-red-400'}>
                  {health.redis ? '✓ Online' : '✗ Offline'}
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Uptime</div>
                <div className="text-green-400">
                  {stats?.system_uptime ? `${stats.system_uptime.toFixed(2)}%` : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statCards.map((card, idx) => (
          <div
            key={idx}
            className="bg-dark-800 rounded-lg p-6 border border-dark-700 hover:border-primary-500 transition-all hover:shadow-lg"
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-3xl">{card.icon}</span>
              <div
                className={`w-12 h-12 rounded-full bg-gradient-to-br ${card.color} opacity-20`}
              ></div>
            </div>
            <h3 className="text-gray-400 text-sm font-medium mb-1">{card.label}</h3>
            <p className="text-3xl font-bold text-white">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Feed Health */}
        <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
          <h3 className="text-xl font-semibold text-white mb-4">Feed Health</h3>
          {health?.feeds_health ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Active Feeds</span>
                <span className="text-green-400 font-medium">
                  {health.feeds_health.active || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Inactive Feeds</span>
                <span className="text-red-400 font-medium">
                  {health.feeds_health.inactive || 0}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Error Rate</span>
                <span
                  className={`font-medium ${
                    (health.feeds_health.error_rate || 0) < 0.1
                      ? 'text-green-400'
                      : 'text-yellow-400'
                  }`}
                >
                  {((health.feeds_health.error_rate || 0) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-400">No feed health data available</p>
          )}
        </div>

        {/* System Metrics */}
        <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
          <h3 className="text-xl font-semibold text-white mb-4">System Metrics</h3>
          {health?.system_metrics ? (
            <div className="space-y-3">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-gray-400">CPU Usage</span>
                  <span className="text-white font-medium">
                    {health.system_metrics.cpu_percent?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${health.system_metrics.cpu_percent || 0}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-gray-400">Memory Usage</span>
                  <span className="text-white font-medium">
                    {health.system_metrics.memory_percent?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all"
                    style={{ width: `${health.system_metrics.memory_percent || 0}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-gray-400">Disk Usage</span>
                  <span className="text-white font-medium">
                    {health.system_metrics.disk_percent?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full transition-all"
                    style={{ width: `${health.system_metrics.disk_percent || 0}%` }}
                  ></div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-400">No system metrics available</p>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h3 className="text-xl font-semibold text-white mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button className="p-4 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors text-center">
            <div className="text-2xl mb-2">🚨</div>
            <div className="text-sm text-gray-300">View Alerts</div>
          </button>
          <button className="p-4 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors text-center">
            <div className="text-2xl mb-2">🏢</div>
            <div className="text-sm text-gray-300">Manage Companies</div>
          </button>
          <button className="p-4 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors text-center">
            <div className="text-2xl mb-2">📰</div>
            <div className="text-sm text-gray-300">Configure Feeds</div>
          </button>
          <button className="p-4 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors text-center">
            <div className="text-2xl mb-2">⚙️</div>
            <div className="text-sm text-gray-300">System Controls</div>
          </button>
        </div>
      </div>

      {/* Seed Data Section */}
      <div className="bg-dark-800 rounded-lg p-6 border border-dark-700">
        <h3 className="text-xl font-semibold text-white mb-4">Initialize Database</h3>
        <div className="space-y-4">
          <p className="text-gray-400 text-sm">
            Load companies and news feeds from config.py. This will populate your database with
            15 companies and all configured news sources/Twitter accounts.
          </p>
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {seedMutation.isPending ? '🔄 Loading Data...' : '📥 Load Config Data'}
          </button>

          {/* Seed Result */}
          {seedResult && (
            <div className={`p-4 rounded-lg border ${
              seedResult.success
                ? 'bg-green-900 bg-opacity-20 border-green-700'
                : 'bg-red-900 bg-opacity-20 border-red-700'
            }`}>
              <div className="space-y-2">
                <div className="font-semibold text-white">
                  {seedResult.success ? '✅ Data Loaded Successfully!' : '❌ Error Loading Data'}
                </div>
                {seedResult.success && (
                  <div className="text-sm text-gray-300 space-y-1">
                    <div>Companies: {seedResult.companies.added} added, {seedResult.companies.skipped} skipped</div>
                    <div>Feeds: {seedResult.feeds.added} added, {seedResult.feeds.skipped} skipped</div>
                    <div className="text-green-400 font-medium mt-2">
                      Total: {seedResult.summary.total_added} items added to database
                    </div>
                  </div>
                )}
                {seedResult.error && (
                  <div className="text-sm text-red-300">{seedResult.error}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Information Banner */}
      <div className="bg-primary-900 bg-opacity-20 border border-primary-700 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div>
            <h4 className="font-semibold text-primary-300 mb-1">Getting Started</h4>
            <p className="text-sm text-gray-400">
              Add companies to monitor, configure news feeds, and set up automated scraping to start
              receiving TGE alerts. Use the Manual Controls to trigger immediate scans.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
