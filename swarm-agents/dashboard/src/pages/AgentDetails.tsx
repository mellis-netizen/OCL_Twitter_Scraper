import React from 'react';
import { useParams, Navigate } from 'react-router-dom';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Tab,
  Tabs,
} from '@mui/material';
import {
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as CriticalIcon,
  HelpOutline as UnknownIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Assignment as TasksIcon,
  AccessTime as ResponseTimeIcon,
} from '@mui/icons-material';
import { useHealthData } from '../contexts/HealthDataContext';
import { AgentStatus } from '../types';

const AgentDetails: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const { agentStatuses, swarmConfig } = useHealthData();
  const [tabValue, setTabValue] = React.useState(0);

  const agent = agentStatuses.find(a => a.id === agentId);

  if (!agent) {
    return <Navigate to="/dashboard" replace />;
  }

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
    
    if (days > 0) return `${days} days, ${hours} hours, ${minutes} minutes`;
    if (hours > 0) return `${hours} hours, ${minutes} minutes`;
    return `${minutes} minutes`;
  };

  const getProgressColor = (value: number, threshold: number = 80) => {
    if (value >= threshold) return 'error';
    if (value >= threshold * 0.7) return 'warning';
    return 'primary';
  };

  const getAgentConfig = () => {
    return swarmConfig?.workers.find(w => w.name.includes(agent.type));
  };

  const agentConfig = getAgentConfig();

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      {/* Header */}
      <Box mb={3}>
        <Box display="flex" alignItems="center" gap={2} mb={1}>
          {getStatusIcon(agent.status)}
          <Typography variant="h4" component="h1">
            {agent.name}
          </Typography>
          <Chip
            label={agent.status}
            color={getStatusColor(agent.status) as any}
          />
        </Box>
        <Typography variant="subtitle1" color="textSecondary">
          Agent ID: {agent.id} • Version: {agent.version}
        </Typography>
      </Box>

      {/* Tab Navigation */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Overview" />
          <Tab label="Performance" />
          <Tab label="Configuration" />
          <Tab label="Logs" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {/* Status Overview */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Status Overview
                </Typography>
                <List>
                  <ListItem>
                    <ListItemText
                      primary="Status"
                      secondary={
                        <Chip
                          label={agent.status}
                          color={getStatusColor(agent.status) as any}
                          size="small"
                        />
                      }
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Uptime"
                      secondary={formatUptime(agent.uptime)}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Last Seen"
                      secondary={new Date(agent.lastSeen).toLocaleString()}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Version"
                      secondary={agent.version}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* Performance Metrics */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Metrics
                </Typography>
                
                {/* Memory Usage */}
                <Box mb={3}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <MemoryIcon color="primary" />
                    <Typography variant="body1">Memory Usage</Typography>
                  </Box>
                  <Typography variant="h6" color="primary">
                    {agent.memoryUsage.toFixed(1)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={agent.memoryUsage}
                    color={getProgressColor(agent.memoryUsage)}
                    sx={{ height: 8, borderRadius: 4, mt: 1 }}
                  />
                </Box>

                {/* CPU Usage */}
                <Box mb={3}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <SpeedIcon color="primary" />
                    <Typography variant="body1">CPU Usage</Typography>
                  </Box>
                  <Typography variant="h6" color="primary">
                    {agent.cpuUsage.toFixed(1)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={agent.cpuUsage}
                    color={getProgressColor(agent.cpuUsage)}
                    sx={{ height: 8, borderRadius: 4, mt: 1 }}
                  />
                </Box>

                {/* Tasks */}
                <Box mb={2}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <TasksIcon color="secondary" />
                    <Typography variant="body1">Task Statistics</Typography>
                  </Box>
                  <Typography variant="body2" color="textSecondary">
                    Completed: {agent.tasksCompleted}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Active: {agent.tasksActive}
                  </Typography>
                </Box>

                {/* Response Time */}
                <Box>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <ResponseTimeIcon color="info" />
                    <Typography variant="body1">Response Time</Typography>
                  </Box>
                  <Typography variant="h6" color="info.main">
                    {agent.responseTime}ms
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Error Information */}
          {agent.errorRate > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom color="error">
                    Error Information
                  </Typography>
                  <Typography variant="body1">
                    Error Rate: {agent.errorRate.toFixed(2)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(agent.errorRate * 10, 100)}
                    color="error"
                    sx={{ height: 8, borderRadius: 4, mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      {tabValue === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Performance History
            </Typography>
            <Typography color="textSecondary">
              Performance charts and historical data will be displayed here.
            </Typography>
          </CardContent>
        </Card>
      )}

      {tabValue === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Agent Configuration
            </Typography>
            {agentConfig ? (
              <Box>
                <Typography variant="body1" gutterBottom>
                  <strong>Role:</strong> {agentConfig.role}
                </Typography>
                <Typography variant="body1" gutterBottom>
                  <strong>Priority:</strong> {agentConfig.priority}
                </Typography>
                
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Focus Areas
                </Typography>
                <List dense>
                  {agentConfig.focus.map((focus, index) => (
                    <ListItem key={index}>
                      <ListItemText primary={focus} />
                    </ListItem>
                  ))}
                </List>

                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Goals
                </Typography>
                <List dense>
                  {agentConfig.goals.map((goal, index) => (
                    <ListItem key={index}>
                      <ListItemText primary={goal} />
                    </ListItem>
                  ))}
                </List>

                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Monitored Files
                </Typography>
                <List dense>
                  {agentConfig.files.map((file, index) => (
                    <ListItem key={index}>
                      <ListItemText primary={file} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            ) : (
              <Typography color="textSecondary">
                No configuration data available for this agent.
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {tabValue === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Agent Logs
            </Typography>
            <Typography color="textSecondary">
              Agent-specific logs will be displayed here.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default AgentDetails;