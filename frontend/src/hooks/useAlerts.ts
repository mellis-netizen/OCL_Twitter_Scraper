import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../services/api';
import wsClient from '../services/websocket';
import type { AlertFilter, AlertNotification } from '../types/api';

export function useAlerts(filter?: AlertFilter) {
  const [realtimeAlerts, setRealtimeAlerts] = useState<AlertNotification[]>([]);

  // Fetch alerts from API
  const {
    data: alerts = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: () => apiClient.getAlerts(filter),
  });

  // Listen for real-time alerts via WebSocket
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    wsClient.connect(token, {
      onAlert: (notification: AlertNotification) => {
        setRealtimeAlerts((prev) => [notification, ...prev].slice(0, 50)); // Keep last 50
        refetch(); // Refresh the full alert list
      },
    });

    return () => {
      wsClient.disconnect();
    };
  }, [refetch]);

  return {
    alerts,
    realtimeAlerts,
    isLoading,
    error,
    refetch,
  };
}
