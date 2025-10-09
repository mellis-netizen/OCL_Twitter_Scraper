// Type definitions for TGE Swarm Dashboard

export interface AgentStatus {
  id: string;
  name: string;
  type: 'scraping-efficiency' | 'keyword-precision' | 'api-reliability' | 'performance' | 'data-quality';
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  uptime: number;
  lastSeen: string;
  version: string;
  memoryUsage: number;
  cpuUsage: number;
  tasksCompleted: number;
  tasksActive: number;
  errorRate: number;
  responseTime: number;
}

export interface HealthCheck {
  name: string;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  timestamp: string;
  responseTime: number;
  errorMessage?: string;
  metrics?: Record<string, any>;
}

export interface ComponentHealth {
  componentName: string;
  overallStatus: 'healthy' | 'warning' | 'critical' | 'unknown';
  checks: HealthCheck[];
  lastRecoveryAttempt?: string;
  recoveryCount: number;
  failureStreak: number;
}

export interface HealthSummary {
  timestamp: string;
  overallHealth: 'healthy' | 'warning' | 'critical';
  components: Record<string, ComponentHealth>;
  recoveryStats: {
    totalRecoveries: number;
    successfulRecoveries: number;
    recentRecoveries: number;
  };
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface PerformanceMetrics {
  tgeDetectionTotal: MetricDataPoint[];
  tgeFalsePositives: MetricDataPoint[];
  apiCallsTotal: MetricDataPoint[];
  scrapingDuration: MetricDataPoint[];
  keywordMatches: MetricDataPoint[];
  memoryUsage: MetricDataPoint[];
  cpuUsage: MetricDataPoint[];
  agentHealthRatio: MetricDataPoint[];
  detectionAccuracy: MetricDataPoint[];
  apiEfficiency: MetricDataPoint[];
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  component: string;
  agent?: string;
  message: string;
  metadata?: Record<string, any>;
}

export interface SwarmConfig {
  name: string;
  version: string;
  mode: string;
  maxWorkers: number;
  workers: {
    name: string;
    role: string;
    priority: string;
    focus: string[];
    files: string[];
    goals: string[];
  }[];
  coordination: {
    syncInterval: string;
    crossPollination: boolean;
    adaptiveFocus: boolean;
  };
  optimization: {
    primaryGoal: string;
    targetAreas: string[];
    successMetrics: string[];
  };
}

export interface AlertRule {
  id: string;
  name: string;
  condition: string;
  threshold: number;
  severity: 'info' | 'warning' | 'critical';
  enabled: boolean;
  lastTriggered?: string;
}

export interface SystemStats {
  uptime: number;
  totalAgents: number;
  healthyAgents: number;
  totalTgeDetected: number;
  accuracy: number;
  apiCallsToday: number;
  memoryUsagePercent: number;
  cpuUsagePercent: number;
}

export interface WebSocketMessage {
  type: 'health_update' | 'metrics_update' | 'log_entry' | 'agent_status' | 'alert';
  data: any;
  timestamp: string;
}