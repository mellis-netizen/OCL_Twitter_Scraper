import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondary,
  Chip,
  Box,
  Divider,
} from '@mui/material';
import {
  Info as InfoIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { useHealthData } from '../../contexts/HealthDataContext';

const RecentAlerts: React.FC = () => {
  const { recentLogs } = useHealthData();

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warn':
        return <WarningIcon color="warning" />;
      case 'info':
        return <InfoIcon color="info" />;
      case 'debug':
        return <InfoIcon color="disabled" />;
      default:
        return <SuccessIcon color="success" />;
    }
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'error';
      case 'warn':
        return 'warning';
      case 'info':
        return 'info';
      case 'debug':
        return 'default';
      default:
        return 'success';
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatRelativeTime = (timestamp: string) => {
    const now = new Date();
    const logTime = new Date(timestamp);
    const diffMs = now.getTime() - logTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return logTime.toLocaleDateString();
  };

  if (!recentLogs || recentLogs.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          <Typography color="textSecondary" textAlign="center" py={4}>
            No recent activity to display
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const recentActivity = recentLogs.slice(0, 10);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Recent Activity
        </Typography>
        
        <List dense>
          {recentActivity.map((log, index) => (
            <React.Fragment key={`${log.timestamp}-${index}`}>
              <ListItem alignItems="flex-start">
                <ListItemIcon sx={{ minWidth: 40, mt: 0.5 }}>
                  {getLogIcon(log.level)}
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <Typography variant="body2" component="span">
                        {log.message}
                      </Typography>
                      <Chip
                        label={log.level.toUpperCase()}
                        color={getLogColor(log.level) as any}
                        size="small"
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="caption" color="textSecondary" display="block">
                        Component: {log.component}
                        {log.agent && ` • Agent: ${log.agent}`}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {formatTime(log.timestamp)} • {formatRelativeTime(log.timestamp)}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
              
              {index < recentActivity.length - 1 && (
                <Divider variant="inset" component="li" />
              )}
            </React.Fragment>
          ))}
        </List>

        {recentLogs.length > 10 && (
          <Box textAlign="center" mt={2}>
            <Typography variant="caption" color="textSecondary">
              Showing 10 of {recentLogs.length} recent entries
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default RecentAlerts;