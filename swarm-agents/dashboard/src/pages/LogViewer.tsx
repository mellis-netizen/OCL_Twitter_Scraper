import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Divider,
  Grid,
  Switch,
  FormControlLabel,
  IconButton,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Debug as DebugIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useHealthData } from '../contexts/HealthDataContext';
import { LogEntry } from '../types';

const LogViewer: React.FC = () => {
  const { recentLogs, refreshData } = useHealthData();
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [componentFilter, setComponentFilter] = useState<string>('all');
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showMetadata, setShowMetadata] = useState(false);

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warn':
        return <WarningIcon color="warning" />;
      case 'info':
        return <InfoIcon color="info" />;
      case 'debug':
        return <DebugIcon color="disabled" />;
      default:
        return <InfoIcon color="primary" />;
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
        return 'primary';
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const formatRelativeTime = (timestamp: string) => {
    const now = new Date();
    const logTime = new Date(timestamp);
    const diffMs = now.getTime() - logTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  // Extract unique values for filters
  const uniqueComponents = useMemo(() => {
    const components = new Set(recentLogs.map(log => log.component));
    return Array.from(components).sort();
  }, [recentLogs]);

  const uniqueAgents = useMemo(() => {
    const agents = new Set(recentLogs.filter(log => log.agent).map(log => log.agent!));
    return Array.from(agents).sort();
  }, [recentLogs]);

  // Filter logs based on search and filter criteria
  const filteredLogs = useMemo(() => {
    return recentLogs.filter(log => {
      // Search term filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const matchesMessage = log.message.toLowerCase().includes(searchLower);
        const matchesComponent = log.component.toLowerCase().includes(searchLower);
        const matchesAgent = log.agent?.toLowerCase().includes(searchLower) || false;
        
        if (!matchesMessage && !matchesComponent && !matchesAgent) {
          return false;
        }
      }

      // Level filter
      if (levelFilter !== 'all' && log.level !== levelFilter) {
        return false;
      }

      // Component filter
      if (componentFilter !== 'all' && log.component !== componentFilter) {
        return false;
      }

      // Agent filter
      if (agentFilter !== 'all' && log.agent !== agentFilter) {
        return false;
      }

      return true;
    });
  }, [recentLogs, searchTerm, levelFilter, componentFilter, agentFilter]);

  const handleClearFilters = () => {
    setSearchTerm('');
    setLevelFilter('all');
    setComponentFilter('all');
    setAgentFilter('all');
  };

  const handleExportLogs = () => {
    const logsText = filteredLogs.map(log => 
      `${log.timestamp} [${log.level.toUpperCase()}] ${log.component}${log.agent ? ` (${log.agent})` : ''}: ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tge-swarm-logs-${new Date().toISOString().slice(0, 19)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Log Viewer
        </Typography>
        
        <Box display="flex" gap={1}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto-refresh"
          />
          
          <Tooltip title="Refresh logs">
            <IconButton onClick={refreshData}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Export logs">
            <IconButton onClick={handleExportLogs}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            {/* Search */}
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />,
                  endAdornment: searchTerm && (
                    <IconButton size="small" onClick={() => setSearchTerm('')}>
                      <ClearIcon />
                    </IconButton>
                  ),
                }}
              />
            </Grid>

            {/* Level Filter */}
            <Grid item xs={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Level</InputLabel>
                <Select
                  value={levelFilter}
                  label="Level"
                  onChange={(e) => setLevelFilter(e.target.value)}
                >
                  <MenuItem value="all">All Levels</MenuItem>
                  <MenuItem value="error">Error</MenuItem>
                  <MenuItem value="warn">Warning</MenuItem>
                  <MenuItem value="info">Info</MenuItem>
                  <MenuItem value="debug">Debug</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {/* Component Filter */}
            <Grid item xs={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Component</InputLabel>
                <Select
                  value={componentFilter}
                  label="Component"
                  onChange={(e) => setComponentFilter(e.target.value)}
                >
                  <MenuItem value="all">All Components</MenuItem>
                  {uniqueComponents.map((component) => (
                    <MenuItem key={component} value={component}>
                      {component}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Agent Filter */}
            <Grid item xs={6} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel>Agent</InputLabel>
                <Select
                  value={agentFilter}
                  label="Agent"
                  onChange={(e) => setAgentFilter(e.target.value)}
                >
                  <MenuItem value="all">All Agents</MenuItem>
                  {uniqueAgents.map((agent) => (
                    <MenuItem key={agent} value={agent}>
                      {agent}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {/* Options */}
            <Grid item xs={6} md={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={showMetadata}
                    onChange={(e) => setShowMetadata(e.target.checked)}
                    size="small"
                  />
                }
                label="Show metadata"
              />
            </Grid>

            {/* Clear Filters */}
            <Grid item xs={6} md={1}>
              <Tooltip title="Clear all filters">
                <IconButton onClick={handleClearFilters}>
                  <ClearIcon />
                </IconButton>
              </Tooltip>
            </Grid>
          </Grid>

          {/* Active Filters Display */}
          {(searchTerm || levelFilter !== 'all' || componentFilter !== 'all' || agentFilter !== 'all') && (
            <Box mt={2} display="flex" gap={1} flexWrap="wrap">
              {searchTerm && (
                <Chip
                  label={`Search: ${searchTerm}`}
                  onDelete={() => setSearchTerm('')}
                  size="small"
                />
              )}
              {levelFilter !== 'all' && (
                <Chip
                  label={`Level: ${levelFilter}`}
                  onDelete={() => setLevelFilter('all')}
                  size="small"
                />
              )}
              {componentFilter !== 'all' && (
                <Chip
                  label={`Component: ${componentFilter}`}
                  onDelete={() => setComponentFilter('all')}
                  size="small"
                />
              )}
              {agentFilter !== 'all' && (
                <Chip
                  label={`Agent: ${agentFilter}`}
                  onDelete={() => setAgentFilter('all')}
                  size="small"
                />
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Results Summary */}
      <Box mb={2}>
        <Typography variant="body2" color="textSecondary">
          Showing {filteredLogs.length} of {recentLogs.length} log entries
        </Typography>
      </Box>

      {/* Log Entries */}
      {filteredLogs.length === 0 ? (
        <Alert severity="info">
          No log entries match the current filters. Try adjusting your search criteria.
        </Alert>
      ) : (
        <Paper>
          <List dense>
            {filteredLogs.map((log, index) => (
              <React.Fragment key={`${log.timestamp}-${index}`}>
                <ListItem alignItems="flex-start">
                  <ListItemIcon sx={{ minWidth: 40, mt: 0.5 }}>
                    {getLogIcon(log.level)}
                  </ListItemIcon>
                  
                  <ListItemText
                    primary={
                      <Box>
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
                        
                        <Box display="flex" alignItems="center" gap={2}>
                          <Typography variant="caption" color="textSecondary">
                            {formatTime(log.timestamp)}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {formatRelativeTime(log.timestamp)}
                          </Typography>
                          <Chip
                            label={log.component}
                            size="small"
                            variant="outlined"
                            sx={{ height: 18, fontSize: '0.6rem' }}
                          />
                          {log.agent && (
                            <Chip
                              label={log.agent}
                              size="small"
                              variant="outlined"
                              color="secondary"
                              sx={{ height: 18, fontSize: '0.6rem' }}
                            />
                          )}
                        </Box>

                        {showMetadata && log.metadata && (
                          <Box mt={1} p={1} bgcolor="action.hover" borderRadius={1}>
                            <Typography variant="caption" color="textSecondary" component="pre">
                              {JSON.stringify(log.metadata, null, 2)}
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                
                {index < filteredLogs.length - 1 && (
                  <Divider variant="inset" component="li" />
                )}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};

export default LogViewer;