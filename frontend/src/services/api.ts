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
        // Public access mode - just log errors, don't redirect
        if (error.response?.status === 401) {
          console.warn('API returned 401 - Backend may require authentication to be disabled');
        }
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
    const response = await this.client.post<Token>('/api/v1/auth/login', credentials);
    this.setAuthToken(response.data.access_token);
    return response.data;
  }

  async register(data: UserCreate): Promise<User> {
    const response = await this.client.post<User>('/api/v1/auth/register', data);
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/api/v1/auth/me');
    return response.data;
  }

  // Companies
  async getCompanies(params?: { limit?: number; offset?: number }): Promise<Company[]> {
    const response = await this.client.get<Company[]>('/api/v1/companies', { params });
    return response.data;
  }

  async getCompany(id: number): Promise<Company> {
    const response = await this.client.get<Company>(`/api/v1/companies/${id}`);
    return response.data;
  }

  async createCompany(data: CompanyCreate): Promise<Company> {
    const response = await this.client.post<Company>('/api/v1/companies', data);
    return response.data;
  }

  async updateCompany(id: number, data: CompanyUpdate): Promise<Company> {
    const response = await this.client.put<Company>(`/api/v1/companies/${id}`, data);
    return response.data;
  }

  async deleteCompany(id: number): Promise<void> {
    await this.client.delete(`/api/v1/companies/${id}`);
  }

  // Feeds
  async getFeeds(params?: { limit?: number; offset?: number }): Promise<Feed[]> {
    const response = await this.client.get<Feed[]>('/api/v1/feeds', { params });
    return response.data;
  }

  async getFeed(id: number): Promise<Feed> {
    const response = await this.client.get<Feed>(`/api/v1/feeds/${id}`);
    return response.data;
  }

  async createFeed(data: FeedCreate): Promise<Feed> {
    const response = await this.client.post<Feed>('/api/v1/feeds', data);
    return response.data;
  }

  async updateFeed(id: number, data: FeedUpdate): Promise<Feed> {
    const response = await this.client.put<Feed>(`/api/v1/feeds/${id}`, data);
    return response.data;
  }

  async deleteFeed(id: number): Promise<void> {
    await this.client.delete(`/api/v1/feeds/${id}`);
  }

  // Alerts
  async getAlerts(filter?: AlertFilter): Promise<Alert[]> {
    const response = await this.client.get<Alert[]>('/api/v1/alerts', { params: filter });
    return response.data;
  }

  async getAlert(id: number): Promise<Alert> {
    const response = await this.client.get<Alert>(`/api/v1/alerts/${id}`);
    return response.data;
  }

  // System
  async getStatistics(): Promise<SystemStatistics> {
    const response = await this.client.get<SystemStatistics>('/api/v1/stats');
    return response.data;
  }

  async getHealth(): Promise<HealthCheck> {
    const response = await this.client.get<HealthCheck>('/api/v1/health');
    return response.data;
  }

  // Manual triggers
  async triggerScraping(): Promise<{ message: string; session_id: string }> {
    const response = await this.client.post('/api/v1/monitoring/trigger');
    return response.data;
  }

  async sendEmailSummary(): Promise<{ message: string }> {
    const response = await this.client.post('/api/v1/monitoring/email-summary');
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
