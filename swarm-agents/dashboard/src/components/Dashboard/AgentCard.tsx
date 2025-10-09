import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Grid,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Refresh as RestartIcon,
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as CriticalIcon,
  HelpOutline as UnknownIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Assignment as TasksIcon,
  AccessTime as ResponseTimeIcon,
} from '@mui/icons-material';
import { AgentStatus } from '../../types';

interface AgentCardProps {
  agent: AgentStatus;
  onAction: (agentId: string, action: 'start' | 'stop' | 'restart') => Promise<void>;
  isLoading?: boolean;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent, onAction, isLoading = false }) => {
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

  const getAgentTypeLabel = (type: string) => {
    switch (type) {
      case 'scraping-efficiency':
        return 'Scraping Efficiency';
      case 'keyword-precision':
        return 'Keyword Precision';
      case 'api-reliability':
        return 'API Reliability';
      case 'performance':
        return 'Performance';
      case 'data-quality':
        return 'Data Quality';
      default:
        return type;
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

  const getProgressColor = (value: number, threshold: number = 80) => {
    if (value >= threshold) return 'error';
    if (value >= threshold * 0.7) return 'warning';
    return 'primary';
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        {/* Header */}
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            {getStatusIcon(agent.status)}
            <Typography variant="h6" component="div" noWrap>
              {getAgentTypeLabel(agent.type)}
            </Typography>
          </Box>
          <Chip
            label={agent.status}
            color={getStatusColor(agent.status) as any}
            size="small"
          />
        </Box>

        {/* Agent Info */}
        <Box mb={2}>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            ID: {agent.id}
          </Typography>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Version: {agent.version}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Uptime: {formatUptime(agent.uptime)}
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Performance Metrics */}
        <Grid container spacing={2}>
          {/* Memory Usage */}
          <Grid item xs={6}>
            <Box>
              <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                <MemoryIcon fontSize="small" color="primary" />
                <Typography variant="caption" color="textSecondary">
                  Memory
                </Typography>
              </Box>
              <Typography variant="body2" fontWeight="bold">
                {agent.memoryUsage.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={agent.memoryUsage}
                color={getProgressColor(agent.memoryUsage)}
                size="small"
                sx={{ height: 4, borderRadius: 2, mt: 0.5 }}
              />
            </Box>
          </Grid>

          {/* CPU Usage */}
          <Grid item xs={6}>
            <Box>
              <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                <SpeedIcon fontSize="small" color="primary" />
                <Typography variant="caption" color="textSecondary">
                  CPU
                </Typography>
              </Box>
              <Typography variant="body2" fontWeight="bold">
                {agent.cpuUsage.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={agent.cpuUsage}
                color={getProgressColor(agent.cpuUsage)}
                size="small"
                sx={{ height: 4, borderRadius: 2, mt: 0.5 }}
              />
            </Box>
          </Grid>

          {/* Tasks */}
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={0.5}>
              <TasksIcon fontSize="small" color="secondary" />
              <Box>
                <Typography variant="caption" color="textSecondary" display="block">
                  Tasks
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {agent.tasksCompleted} / {agent.tasksActive} active
                </Typography>
              </Box>
            </Box>
          </Grid>

          {/* Response Time */}
          <Grid item xs={6}>
            <Box display="flex" alignItems="center" gap={0.5}>
              <ResponseTimeIcon fontSize="small" color="info" />
              <Box>
                <Typography variant="caption" color="textSecondary" display="block">
                  Response
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {agent.responseTime}ms
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>

        {/* Error Rate */}
        {agent.errorRate > 0 && (
          <Box mt={2}>
            <Typography variant="caption" color="textSecondary">
              Error Rate: {agent.errorRate.toFixed(2)}%
            </Typography>
            <LinearProgress
              variant="determinate"
              value={Math.min(agent.errorRate * 10, 100)}
              color="error"
              sx={{ height: 4, borderRadius: 2, mt: 0.5 }}
            />
          </Box>
        )}
      </CardContent>

      {/* Action Buttons */}
      <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
        <Box>
          <Typography variant="caption" color="textSecondary">
            Last seen: {new Date(agent.lastSeen).toLocaleTimeString()}
          </Typography>
        </Box>
        
        <Box>
          {isLoading ? (
            <CircularProgress size={24} />
          ) : (
            <>
              <Tooltip title="Start Agent">
                <IconButton
                  size="small"
                  color="success"
                  onClick={() => onAction(agent.id, 'start')}
                  disabled={agent.status === 'healthy'}
                >
                  <StartIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Restart Agent">
                <IconButton
                  size="small"
                  color="warning"
                  onClick={() => onAction(agent.id, 'restart')}
                >
                  <RestartIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Stop Agent">
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => onAction(agent.id, 'stop')}
                  disabled={agent.status === 'critical'}
                >
                  <StopIcon />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Box>
      </CardActions>
    </Card>
  );
};

export default AgentCard;