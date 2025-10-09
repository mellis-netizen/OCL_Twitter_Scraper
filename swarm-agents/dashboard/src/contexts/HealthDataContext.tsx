import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { useWebSocket } from './WebSocketContext';
import { 
  HealthSummary, 
  AgentStatus, 
  PerformanceMetrics, 
  SystemStats, 
  LogEntry,
  SwarmConfig
} from '../types';

interface HealthDataContextType {
  healthSummary: HealthSummary | null;
  agentStatuses: AgentStatus[];
  performanceMetrics: PerformanceMetrics | null;
  systemStats: SystemStats | null;
  recentLogs: LogEntry[];
  swarmConfig: SwarmConfig | null;
  isLoading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  updateAgentStatus: (agentId: string, action: 'start' | 'stop' | 'restart') => Promise<void>;
}

const HealthDataContext = createContext<HealthDataContextType | undefined>(undefined);

export const useHealthData = () => {
  const context = useContext(HealthDataContext);
  if (!context) {
    throw new Error('useHealthData must be used within a HealthDataProvider');
  }
  return context;
};

interface HealthDataProviderProps {
  children: React.ReactNode;
}

// API base URL - should match your health monitor API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';

export const HealthDataProvider: React.FC<HealthDataProviderProps> = ({ children }) => {
  const { subscribe, isConnected } = useWebSocket();
  
  const [healthSummary, setHealthSummary] = useState<HealthSummary | null>(null);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [recentLogs, setRecentLogs] = useState<LogEntry[]>([]);
  const [swarmConfig, setSwarmConfig] = useState<SwarmConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch initial data from REST API
  const fetchHealthSummary = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health/summary`);
      setHealthSummary(response.data);
    } catch (err) {
      console.error('Failed to fetch health summary:', err);
      // Create mock data for development
      setHealthSummary({
        timestamp: new Date().toISOString(),
        overallHealth: 'healthy',
        components: {
          'swarm-queen': {
            componentName: 'swarm-queen',
            overallStatus: 'healthy',
            checks: [],
            recoveryCount: 0,
            failureStreak: 0,
          },
        },
        recoveryStats: {
          totalRecoveries: 0,
          successfulRecoveries: 0,
          recentRecoveries: 0,
        },
      });
    }
  }, []);

  const fetchAgentStatuses = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/agents/status`);
      setAgentStatuses(response.data);
    } catch (err) {
      console.error('Failed to fetch agent statuses:', err);
      // Create mock agent data for development
      const mockAgents: AgentStatus[] = [
        {
          id: 'scraping-efficiency-1',
          name: 'Scraping Efficiency Specialist',
          type: 'scraping-efficiency',
          status: 'healthy',
          uptime: 86400,
          lastSeen: new Date().toISOString(),
          version: '1.0.0',
          memoryUsage: 85,
          cpuUsage: 25,
          tasksCompleted: 1250,
          tasksActive: 3,
          errorRate: 0.5,
          responseTime: 120,
        },
        {
          id: 'keyword-precision-1',
          name: 'TGE Keyword Precision Specialist',
          type: 'keyword-precision',
          status: 'healthy',
          uptime: 86400,
          lastSeen: new Date().toISOString(),
          version: '1.0.0',
          memoryUsage: 72,
          cpuUsage: 18,
          tasksCompleted: 890,
          tasksActive: 2,
          errorRate: 0.2,
          responseTime: 95,
        },
        {
          id: 'api-reliability-1',
          name: 'API Reliability Optimizer',
          type: 'api-reliability',
          status: 'warning',
          uptime: 82800,
          lastSeen: new Date().toISOString(),
          version: '1.0.0',
          memoryUsage: 95,
          cpuUsage: 35,
          tasksCompleted: 2100,
          tasksActive: 5,
          errorRate: 2.1,
          responseTime: 180,
        },
        {
          id: 'performance-1',
          name: 'Performance Bottleneck Eliminator',
          type: 'performance',
          status: 'healthy',
          uptime: 86400,
          lastSeen: new Date().toISOString(),
          version: '1.0.0',
          memoryUsage: 68,
          cpuUsage: 22,
          tasksCompleted: 1580,
          tasksActive: 1,
          errorRate: 0.3,
          responseTime: 75,
        },
        {
          id: 'data-quality-1',
          name: 'Data Quality Enforcer',
          type: 'data-quality',
          status: 'healthy',
          uptime: 86400,
          lastSeen: new Date().toISOString(),
          version: '1.0.0',
          memoryUsage: 78,
          cpuUsage: 20,
          tasksCompleted: 980,
          tasksActive: 2,
          errorRate: 0.1,
          responseTime: 110,
        },
      ];
      setAgentStatuses(mockAgents);
    }
  }, []);

  const fetchPerformanceMetrics = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/metrics/performance`);
      setPerformanceMetrics(response.data);
    } catch (err) {
      console.error('Failed to fetch performance metrics:', err);
      // Create mock metrics data
      const now = new Date();
      const mockMetrics: PerformanceMetrics = {
        tgeDetectionTotal: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.floor(Math.random() * 50) + 10,
        })),
        tgeFalsePositives: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.floor(Math.random() * 5),
        })),
        apiCallsTotal: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.floor(Math.random() * 1000) + 500,
        })),
        scrapingDuration: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.random() * 2000 + 500,
        })),
        keywordMatches: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.floor(Math.random() * 200) + 50,
        })),
        memoryUsage: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.random() * 30 + 60,
        })),
        cpuUsage: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.random() * 40 + 10,
        })),
        agentHealthRatio: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.random() * 20 + 80,
        })),
        detectionAccuracy: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.random() * 10 + 90,
        })),
        apiEfficiency: Array.from({ length: 24 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
          value: Math.random() * 0.3 + 0.7,
        })),
      };
      setPerformanceMetrics(mockMetrics);
    }
  }, []);

  const fetchSystemStats = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/system/stats`);
      setSystemStats(response.data);
    } catch (err) {
      console.error('Failed to fetch system stats:', err);
      // Create mock system stats
      setSystemStats({
        uptime: 86400,
        totalAgents: 5,
        healthyAgents: 4,
        totalTgeDetected: 127,
        accuracy: 94.5,
        apiCallsToday: 15420,
        memoryUsagePercent: 72,
        cpuUsagePercent: 28,
      });
    }
  }, []);

  const fetchRecentLogs = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/logs/recent?limit=100`);
      setRecentLogs(response.data);
    } catch (err) {
      console.error('Failed to fetch recent logs:', err);
      // Create mock log entries
      const mockLogs: LogEntry[] = Array.from({ length: 20 }, (_, i) => ({
        timestamp: new Date(Date.now() - i * 30000).toISOString(),
        level: ['info', 'warn', 'error'][Math.floor(Math.random() * 3)] as any,
        component: ['swarm-queen', 'agent-scraping', 'agent-keyword', 'agent-api'][Math.floor(Math.random() * 4)],
        agent: Math.random() > 0.5 ? 'scraping-efficiency-1' : undefined,
        message: [
          'TGE detection completed successfully',
          'API rate limit approaching threshold',
          'Keyword matching optimization applied',
          'Agent health check passed',
          'Performance bottleneck detected and resolved',
        ][Math.floor(Math.random() * 5)],
      }));
      setRecentLogs(mockLogs);
    }
  }, []);

  const fetchSwarmConfig = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/config/swarm`);
      setSwarmConfig(response.data);
    } catch (err) {
      console.error('Failed to fetch swarm config:', err);
      // Use default config based on the YAML file
      setSwarmConfig({
        name: 'TGE-Detection-Efficiency-Swarm',
        version: '2.0-optimized',
        mode: 'queen-directed',
        maxWorkers: 5,
        workers: [
          {
            name: 'scraping-efficiency-specialist',
            role: 'primary-optimizer',
            priority: 'critical',
            focus: ['scraper-performance-tuning', 'api-rate-limit-optimization'],
            files: ['src/news_scraper*.py', 'src/twitter_monitor*.py'],
            goals: ['reduce-api-calls-by-30-percent', 'increase-scraping-speed-by-50-percent'],
          },
          {
            name: 'tge-keyword-precision-specialist',
            role: 'accuracy-optimizer',
            priority: 'critical',
            focus: ['keyword-matching-precision', 'false-positive-elimination'],
            files: ['config.py', 'src/news_scraper*.py'],
            goals: ['achieve-95-percent-precision', 'reduce-false-positives-by-50-percent'],
          },
          {
            name: 'api-reliability-optimizer',
            role: 'integration-hardener',
            priority: 'high',
            focus: ['error-handling-robustness', 'retry-mechanism-optimization'],
            files: ['src/twitter_monitor*.py', 'src/news_scraper*.py'],
            goals: ['zero-unhandled-exceptions', 'intelligent-rate-limit-handling'],
          },
          {
            name: 'performance-bottleneck-eliminator',
            role: 'speed-optimizer',
            priority: 'high',
            focus: ['cpu-usage-optimization', 'memory-leak-prevention'],
            files: ['src/main*.py', 'src/*_optimized.py'],
            goals: ['reduce-memory-usage-by-40-percent', 'eliminate-performance-bottlenecks'],
          },
          {
            name: 'data-quality-enforcer',
            role: 'quality-gatekeeper',
            priority: 'medium',
            focus: ['tge-data-validation', 'duplicate-detection-efficiency'],
            files: ['src/utils.py', 'src/news_scraper*.py'],
            goals: ['zero-duplicate-alerts', '100-percent-data-sanitization'],
          },
        ],
        coordination: {
          syncInterval: '90s',
          crossPollination: true,
          adaptiveFocus: true,
        },
        optimization: {
          primaryGoal: 'maximize-tge-detection-efficiency',
          targetAreas: ['scraping-speed', 'tge-detection-accuracy', 'false-positive-elimination'],
          successMetrics: ['tge-detection-precision-above-95-percent', 'false-positive-rate-below-5-percent'],
        },
      });
    }
  }, []);

  const refreshData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchHealthSummary(),
        fetchAgentStatuses(),
        fetchPerformanceMetrics(),
        fetchSystemStats(),
        fetchRecentLogs(),
        fetchSwarmConfig(),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  }, [
    fetchHealthSummary,
    fetchAgentStatuses,
    fetchPerformanceMetrics,
    fetchSystemStats,
    fetchRecentLogs,
    fetchSwarmConfig,
  ]);

  const updateAgentStatus = useCallback(async (agentId: string, action: 'start' | 'stop' | 'restart') => {
    try {
      await axios.post(`${API_BASE_URL}/agents/${agentId}/${action}`);
      // Refresh agent statuses after action
      await fetchAgentStatuses();
    } catch (err) {
      console.error(`Failed to ${action} agent ${agentId}:`, err);
      throw err;
    }
  }, [fetchAgentStatuses]);

  // Subscribe to real-time updates
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribers: (() => void)[] = [];

    // Subscribe to health updates
    unsubscribers.push(
      subscribe('health_update', (data) => {
        setHealthSummary(data);
      })
    );

    // Subscribe to agent status updates
    unsubscribers.push(
      subscribe('agent_status', (data) => {
        setAgentStatuses(prev => {
          const index = prev.findIndex(agent => agent.id === data.id);
          if (index >= 0) {
            const updated = [...prev];
            updated[index] = { ...updated[index], ...data };
            return updated;
          }
          return [...prev, data];
        });
      })
    );

    // Subscribe to metrics updates
    unsubscribers.push(
      subscribe('metrics_update', (data) => {
        setPerformanceMetrics(prev => ({
          ...prev,
          ...data,
        }));
      })
    );

    // Subscribe to log entries
    unsubscribers.push(
      subscribe('log_entry', (data) => {
        setRecentLogs(prev => [data, ...prev.slice(0, 99)]);
      })
    );

    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
    };
  }, [isConnected, subscribe]);

  // Initial data fetch
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  const value: HealthDataContextType = {
    healthSummary,
    agentStatuses,
    performanceMetrics,
    systemStats,
    recentLogs,
    swarmConfig,
    isLoading,
    error,
    refreshData,
    updateAgentStatus,
  };

  return (
    <HealthDataContext.Provider value={value}>
      {children}
    </HealthDataContext.Provider>
  );
};