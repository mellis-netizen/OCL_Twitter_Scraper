import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '../types';

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connectionError: string | null;
  sendMessage: (type: string, data: any) => void;
  subscribe: (eventType: string, callback: (data: any) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const connect = useCallback(() => {
    try {
      // WebSocket server endpoint - should match your health monitor WebSocket server
      const wsSocket = io(process.env.REACT_APP_WS_URL || 'ws://localhost:8080', {
        transports: ['websocket'],
        autoConnect: true,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5,
        timeout: 20000,
      });

      wsSocket.on('connect', () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
      });

      wsSocket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        setIsConnected(false);
        if (reason === 'io server disconnect') {
          // The disconnection was initiated by the server, reconnect manually
          wsSocket.connect();
        }
      });

      wsSocket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        setConnectionError(error.message);
        setIsConnected(false);
      });

      wsSocket.on('reconnect', (attemptNumber) => {
        console.log('WebSocket reconnected after', attemptNumber, 'attempts');
        setIsConnected(true);
        setConnectionError(null);
      });

      wsSocket.on('reconnect_failed', () => {
        console.error('WebSocket reconnection failed');
        setConnectionError('Failed to reconnect to server');
        setIsConnected(false);
      });

      // Handle incoming messages
      wsSocket.on('message', (message: WebSocketMessage) => {
        console.log('Received WebSocket message:', message);
        // Messages are handled by individual subscribers
      });

      setSocket(wsSocket);

      return () => {
        wsSocket.disconnect();
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError(error instanceof Error ? error.message : 'Unknown connection error');
    }
  }, []);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  const sendMessage = useCallback(
    (type: string, data: any) => {
      if (socket && isConnected) {
        const message: WebSocketMessage = {
          type: type as any,
          data,
          timestamp: new Date().toISOString(),
        };
        socket.emit('message', message);
      } else {
        console.warn('Cannot send message: WebSocket not connected');
      }
    },
    [socket, isConnected]
  );

  const subscribe = useCallback(
    (eventType: string, callback: (data: any) => void) => {
      if (!socket) {
        console.warn('Cannot subscribe: WebSocket not available');
        return () => {};
      }

      socket.on(eventType, callback);

      // Return unsubscribe function
      return () => {
        socket.off(eventType, callback);
      };
    },
    [socket]
  );

  const value: WebSocketContextType = {
    socket,
    isConnected,
    connectionError,
    sendMessage,
    subscribe,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};