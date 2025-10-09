import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  CircularProgress,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  CloudDone as ApiIcon,
  Assessment as AccuracyIcon,
  BugReport as DetectionIcon,
} from '@mui/icons-material';
import { SystemStats, HealthSummary } from '../../types';

interface SystemOverviewProps {
  systemStats: SystemStats | null;
  healthSummary: HealthSummary | null;
}

const SystemOverview: React.FC<SystemOverviewProps> = ({ systemStats, healthSummary }) => {
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getHealthColor = (health: string) => {
    switch (health) {
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

  const getProgressColor = (value: number, threshold: number = 80) => {
    if (value >= threshold) return 'error';
    if (value >= threshold * 0.7) return 'warning';
    return 'primary';
  };

  if (!systemStats) {
    return (
      <Grid container spacing={3}>
        {Array.from({ length: 6 }).map((_, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="center" alignItems="center" height={80}>
                  <CircularProgress size={30} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  return (
    <Grid container spacing={3}>
      {/* Overall Health */}
      <Grid item xs={12} sm={6} md={4}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  System Health
                </Typography>
                <Typography variant="h6">
                  <Chip
                    label={healthSummary?.overallHealth || 'Unknown'}
                    color={getHealthColor(healthSummary?.overallHealth || 'unknown') as any}
                    size="small"
                  />
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Uptime: {formatUptime(systemStats.uptime)}
                </Typography>
              </Box>
              <TrendingUpIcon color="primary" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* TGE Detection Count */}
      <Grid item xs={12} sm={6} md={4}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  TGEs Detected Today
                </Typography>
                <Typography variant="h4" color="primary">
                  {systemStats.totalTgeDetected}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  {systemStats.accuracy.toFixed(1)}% accuracy
                </Typography>
              </Box>
              <DetectionIcon color="secondary" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* API Calls */}
      <Grid item xs={12} sm={6} md={4}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  API Calls Today
                </Typography>
                <Typography variant="h5">
                  {systemStats.apiCallsToday.toLocaleString()}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Efficiency: {(systemStats.totalTgeDetected / systemStats.apiCallsToday * 100).toFixed(2)}%
                </Typography>
              </Box>
              <ApiIcon color="info" sx={{ fontSize: 40 }} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Memory Usage */}
      <Grid item xs={12} sm={6} md={4}>
        <Card>
          <CardContent>
            <Box>
              <Typography color="textSecondary" gutterBottom variant="body2">
                Memory Usage
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Typography variant="h6">
                  {systemStats.memoryUsagePercent.toFixed(1)}%
                </Typography>
                <MemoryIcon color="primary" />
              </Box>
              <LinearProgress
                variant="determinate"
                value={systemStats.memoryUsagePercent}
                color={getProgressColor(systemStats.memoryUsagePercent)}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* CPU Usage */}
      <Grid item xs={12} sm={6} md={4}>
        <Card>
          <CardContent>
            <Box>
              <Typography color="textSecondary" gutterBottom variant="body2">
                CPU Usage
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Typography variant="h6">
                  {systemStats.cpuUsagePercent.toFixed(1)}%
                </Typography>
                <SpeedIcon color="primary" />
              </Box>
              <LinearProgress
                variant="determinate"
                value={systemStats.cpuUsagePercent}
                color={getProgressColor(systemStats.cpuUsagePercent)}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Agent Health */}
      <Grid item xs={12} sm={6} md={4}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  Agent Health
                </Typography>
                <Typography variant="h5">
                  {systemStats.healthyAgents}/{systemStats.totalAgents}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  {((systemStats.healthyAgents / systemStats.totalAgents) * 100).toFixed(0)}% healthy
                </Typography>
              </Box>
              <AccuracyIcon 
                color={systemStats.healthyAgents === systemStats.totalAgents ? 'success' : 'warning'}
                sx={{ fontSize: 40 }}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default SystemOverview;