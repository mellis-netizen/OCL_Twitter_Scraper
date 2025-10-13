import type { AlertNotification, WebSocketMessage } from '../types/api';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export type WebSocketEventType = 'alert' | 'status' | 'error' | 'ping';

export interface WebSocketOptions {
  onAlert?: (notification: AlertNotification) => void;
  onStatus?: (data: any) => void;
  onError?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private options: WebSocketOptions = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  connect(token: string, options: WebSocketOptions = {}) {
    this.options = options;
    const wsUrl = `${WS_BASE_URL}/ws?token=${token}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.options.onConnect?.();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.options.onDisconnect?.();
        this.attemptReconnect(token);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }

  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'alert':
        this.options.onAlert?.(message.data as AlertNotification);
        break;
      case 'status':
        this.options.onStatus?.(message.data);
        break;
      case 'error':
        this.options.onError?.(message.data);
        break;
      case 'ping':
        // Respond to ping with pong
        this.send({ type: 'pong', data: {}, timestamp: new Date().toISOString() });
        break;
    }
  }

  private attemptReconnect(token: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    this.reconnectTimeout = window.setTimeout(() => {
      this.connect(token, this.options);
    }, this.reconnectDelay);
  }

  send(message: WebSocketMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new WebSocketClient();
export default wsClient;
