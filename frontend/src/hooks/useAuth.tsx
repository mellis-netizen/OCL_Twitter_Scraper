import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import wsClient from '../services/websocket';
import type { User, LoginRequest, UserCreate } from '../types/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  register: (data: UserCreate) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Authentication disabled - always authenticated for public access
  const [isAuthenticated] = useState<boolean>(true);

  // Mock user data for public access
  const user: User | null = {
    id: 1,
    username: 'public',
    email: 'public@access.local',
    is_admin: false,
    is_active: true,
    created_at: new Date().toISOString(),
  };
  const isLoading = false;

  // WebSocket connection without authentication
  useEffect(() => {
    // Connect without token for public access
    wsClient.connect('', {
      onConnect: () => {}, // WebSocket connected in public mode
      onDisconnect: () => {}, // WebSocket disconnected
    });

    return () => {
      wsClient.disconnect();
    };
  }, []);

  const login = async (_credentials: LoginRequest) => {
    // Authentication disabled - no-op
  };

  const logout = () => {
    // Authentication disabled - no-op
  };

  const register = async (_data: UserCreate) => {
    // Authentication disabled - no-op
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
