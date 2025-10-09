import React, { useState } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Paper,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RestartIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as CriticalIcon,
  HelpOutline as UnknownIcon,
} from '@mui/icons-material';
import { useHealthData } from '../contexts/HealthDataContext';
import SystemOverview from '../components/Dashboard/SystemOverview';
import AgentCard from '../components/Dashboard/AgentCard';
import MetricsOverview from '../components/Dashboard/MetricsOverview';
import RecentAlerts from '../components/Dashboard/RecentAlerts';

const Dashboard: React.FC = () => {
  const { 
    agentStatuses, 
    systemStats, 
    healthSummary, 
    isLoading, 
    error, 
    updateAgentStatus 
  } = useHealthData();
  
  const [actionLoading, setActionLoading] = useState<{ [key: string]: boolean }>({});

  const handleAgentAction = async (agentId: string, action: 'start' | 'stop' | 'restart') => {
    setActionLoading(prev => ({ ...prev, [agentId]: true }));
    try {
      await updateAgentStatus(agentId, action);
    } catch (err) {
      console.error(`Failed to ${action} agent:`, err);
    } finally {
      setActionLoading(prev => ({ ...prev, [agentId]: false }));
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <HealthyIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'critical':
        return <CriticalIcon color="error" />;
      default:
        return <UnknownIcon color="disabled" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  if (isLoading && !agentStatuses.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* System Overview */}
      <SystemOverview systemStats={systemStats} healthSummary={healthSummary} />

      {/* Agent Status Grid */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Agent Status Overview
      </Typography>
      
      <Grid container spacing={3}>
        {agentStatuses.map((agent) => (
          <Grid item xs={12} sm={6} lg={4} key={agent.id}>
            <AgentCard 
              agent={agent}
              onAction={handleAgentAction}
              isLoading={actionLoading[agent.id]}
            />
          </Grid>
        ))}
      </Grid>

      {/* Metrics Overview */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Key Metrics
      </Typography>
      <MetricsOverview />

      {/* Recent Alerts and Activity */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Recent Activity
      </Typography>
      <RecentAlerts />
    </Box>
  );
};

export default Dashboard;