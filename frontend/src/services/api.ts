import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  LoginRequest,
  Token,
  User,
  UserCreate,
  Company,
  CompanyCreate,
  CompanyUpdate,
  Feed,
  FeedCreate,
  FeedUpdate,
  Alert,
  AlertFilter,
  SystemStatistics,
  HealthCheck,
  APIError,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Load token from localStorage
    this.token = localStorage.getItem('auth_token');
    if (this.token) {
      this.setAuthToken(this.token);
    }

    // Response interceptor for error handling (public access mode - no redirect on 401)
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        // Public access mode - silently handle 401s
        return Promise.reject(error);
      }
    );
  }

  setAuthToken(token: string) {
    this.token = token;
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    localStorage.setItem('auth_token', token);
  }

  clearAuth() {
    this.token = null;
    delete this.client.defaults.headers.common['Authorization'];
    localStorage.removeItem('auth_token');
  }

  // Authentication
  async login(credentials: LoginRequest): Promise<Token> {
    const response = await this.client.post<Token>('/auth/login', credentials);
    this.setAuthToken(response.data.access_token);
    return response.data;
  }

  async register(data: UserCreate): Promise<User> {
    const response = await this.client.post<User>('/auth/register', data);
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }

  // Companies
  async getCompanies(params?: { limit?: number; offset?: number }): Promise<Company[]> {
    const response = await this.client.get<Company[]>('/companies', { params });
    return response.data;
  }

  async getCompany(id: number): Promise<Company> {
    const response = await this.client.get<Company>(`/companies/${id}`);
    return response.data;
  }

  async createCompany(data: CompanyCreate): Promise<Company> {
    const response = await this.client.post<Company>('/companies', data);
    return response.data;
  }

  async updateCompany(id: number, data: CompanyUpdate): Promise<Company> {
    const response = await this.client.put<Company>(`/companies/${id}`, data);
    return response.data;
  }

  async deleteCompany(id: number): Promise<void> {
    await this.client.delete(`/companies/${id}`);
  }

  // Feeds
  async getFeeds(params?: { limit?: number; offset?: number }): Promise<Feed[]> {
    const response = await this.client.get<Feed[]>('/feeds', { params });
    return response.data;
  }

  async getFeed(id: number): Promise<Feed> {
    const response = await this.client.get<Feed>(`/feeds/${id}`);
    return response.data;
  }

  async createFeed(data: FeedCreate): Promise<Feed> {
    const response = await this.client.post<Feed>('/feeds', data);
    return response.data;
  }

  async updateFeed(id: number, data: FeedUpdate): Promise<Feed> {
    const response = await this.client.put<Feed>(`/feeds/${id}`, data);
    return response.data;
  }

  async deleteFeed(id: number): Promise<void> {
    await this.client.delete(`/feeds/${id}`);
  }

  // Alerts
  async getAlerts(filter?: AlertFilter): Promise<Alert[]> {
    const response = await this.client.get<Alert[]>('/alerts', { params: filter });
    return response.data;
  }

  async getAlert(id: number): Promise<Alert> {
    const response = await this.client.get<Alert>(`/alerts/${id}`);
    return response.data;
  }

  // System
  async getStatistics(): Promise<SystemStatistics> {
    const response = await this.client.get<SystemStatistics>('/statistics/system');
    return response.data;
  }

  async getHealth(): Promise<HealthCheck> {
    const response = await this.client.get<HealthCheck>('/health');
    return response.data;
  }

  // Manual triggers
  async triggerScraping(): Promise<{ message: string; session_id: string }> {
    const response = await this.client.post('/monitoring/trigger');
    return response.data;
  }

  async sendEmailSummary(): Promise<{ message: string }> {
    const response = await this.client.post('/monitoring/email-summary');
    return response.data;
  }

  // Monitoring sessions
  async getSessionProgress(sessionId: string): Promise<any> {
    const response = await this.client.get(`/monitoring/session/${sessionId}/progress`);
    return response.data;
  }

  async getSession(sessionId: string): Promise<any> {
    const response = await this.client.get(`/monitoring/session/${sessionId}`);
    return response.data;
  }

  async getRecentSessions(limit: number = 10): Promise<any[]> {
    const response = await this.client.get(`/monitoring/sessions/recent?limit=${limit}`);
    return response.data;
  }

  // Seed data
  async seedData(): Promise<any> {
    const response = await this.client.post('/seed-data');
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
