// TypeScript types matching backend Pydantic schemas

export type Priority = 'HIGH' | 'MEDIUM' | 'LOW';
export type UrgencyLevel = 'low' | 'medium' | 'high' | 'critical';
export type SourceType = 'twitter' | 'news' | 'manual';
export type AlertStatus = 'active' | 'archived' | 'false_positive';

// User types
export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at?: string;
  last_login?: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// Company types
export interface Company {
  id: number;
  name: string;
  aliases: string[];
  tokens: string[];
  priority: Priority;
  status: string;
  website?: string;
  twitter_handle?: string;
  description?: string;
  exclusions: string[];
  created_at?: string;
  updated_at?: string;
}

export interface CompanyCreate {
  name: string;
  aliases?: string[];
  tokens?: string[];
  priority?: Priority;
  status?: string;
  website?: string;
  twitter_handle?: string;
  description?: string;
  exclusions?: string[];
}

export interface CompanyUpdate {
  name?: string;
  aliases?: string[];
  tokens?: string[];
  priority?: Priority;
  status?: string;
  website?: string;
  twitter_handle?: string;
  description?: string;
  exclusions?: string[];
}

// Feed types
export interface Feed {
  id: number;
  name: string;
  url: string;
  type: string;
  priority: number;
  is_active: boolean;
  success_count: number;
  failure_count: number;
  last_fetch?: string;
  last_success?: string;
  last_failure?: string;
  last_error?: string;
  articles_found: number;
  tge_alerts_found: number;
  created_at?: string;
  updated_at?: string;
}

export interface FeedCreate {
  name: string;
  url: string;
  type?: string;
  priority?: number;
  is_active?: boolean;
}

export interface FeedUpdate {
  name?: string;
  url?: string;
  type?: string;
  priority?: number;
  is_active?: boolean;
}

// Alert types
export interface Alert {
  id: number;
  title: string;
  content: string;
  source: SourceType;
  source_url?: string;
  confidence: number;
  company_id?: number;
  company?: Company;
  keywords_matched?: string[];
  tokens_mentioned?: string[];
  analysis_data?: Record<string, any>;
  sentiment_score?: number;
  urgency_level: UrgencyLevel;
  status: AlertStatus;
  created_at?: string;
  updated_at?: string;
}

export interface AlertFilter {
  company_id?: number;
  source?: SourceType;
  min_confidence?: number;
  max_confidence?: number;
  urgency_level?: UrgencyLevel;
  status?: AlertStatus;
  from_date?: string;
  to_date?: string;
  keywords?: string[];
  limit?: number;
  offset?: number;
}

// System types
export interface SystemStatistics {
  total_companies: number;
  total_feeds: number;
  active_feeds: number;
  total_alerts: number;
  alerts_last_24h: number;
  alerts_last_7d: number;
  avg_confidence: number;
  system_uptime: number;
  last_monitoring_session?: string;
}

export interface HealthCheck {
  status: string;
  timestamp: string;
  database: boolean;
  redis: boolean;
  feeds_health: Record<string, any>;
  system_metrics: Record<string, any>;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface AlertNotification {
  alert_id: number;
  title: string;
  company_name?: string;
  confidence: number;
  urgency_level: UrgencyLevel;
  source: SourceType;
  created_at: string;
}

// API Error type
export interface APIError {
  detail: string;
}

// Alert response type (alias for Alert interface)
export type AlertResponse = Alert;
