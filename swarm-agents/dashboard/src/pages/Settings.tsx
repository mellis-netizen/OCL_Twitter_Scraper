import React, { useState } from 'react';
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
  Switch,
  FormControlLabel,
  Button,
  Grid,
  Divider,
  Alert,
  Snackbar,
  Paper,
  Tab,
  Tabs,
  List,
  ListItem,
  ListItemText,
  ListItemSecondary,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Save as SaveIcon,
  RestoreFromTrash as ResetIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import { useHealthData } from '../contexts/HealthDataContext';

interface AlertRule {
  id: string;
  name: string;
  condition: string;
  threshold: number;
  severity: 'info' | 'warning' | 'critical';
  enabled: boolean;
}

const Settings: React.FC = () => {
  const { swarmConfig } = useHealthData();
  const [tabValue, setTabValue] = useState(0);
  const [saveStatus, setSaveStatus] = useState<'success' | 'error' | null>(null);
  const [editRuleDialog, setEditRuleDialog] = useState<AlertRule | null>(null);

  // Dashboard Settings
  const [dashboardSettings, setDashboardSettings] = useState({
    autoRefresh: true,
    refreshInterval: 30,
    theme: 'dark',
    showNotifications: true,
    soundAlerts: false,
    compactView: false,
  });

  // Monitoring Settings
  const [monitoringSettings, setMonitoringSettings] = useState({
    healthCheckInterval: 30,
    metricsRetention: 24,
    logLevel: 'info',
    enableTracing: false,
    maxLogEntries: 1000,
    alertCooldown: 300,
  });

  // Agent Configuration
  const [agentConfig, setAgentConfig] = useState({
    maxWorkers: 5,
    maxMemoryPerWorker: 200,
    maxExecutionTime: 20,
    syncInterval: 90,
    crossPollination: true,
    adaptiveFocus: true,
  });

  // Alert Rules
  const [alertRules, setAlertRules] = useState<AlertRule[]>([
    {
      id: '1',
      name: 'High Memory Usage',
      condition: 'memory_usage > threshold',
      threshold: 80,
      severity: 'warning',
      enabled: true,
    },
    {
      id: '2',
      name: 'Critical Memory Usage',
      condition: 'memory_usage > threshold',
      threshold: 95,
      severity: 'critical',
      enabled: true,
    },
    {
      id: '3',
      name: 'Agent Down',
      condition: 'agent_health < threshold',
      threshold: 1,
      severity: 'critical',
      enabled: true,
    },
    {
      id: '4',
      name: 'High False Positive Rate',
      condition: 'false_positive_rate > threshold',
      threshold: 10,
      severity: 'warning',
      enabled: true,
    },
  ]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSaveSettings = async () => {
    try {
      // Simulate API call to save settings
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSaveStatus('success');
    } catch (error) {
      setSaveStatus('error');
    }
  };

  const handleResetSettings = () => {
    // Reset to default values
    setDashboardSettings({
      autoRefresh: true,
      refreshInterval: 30,
      theme: 'dark',
      showNotifications: true,
      soundAlerts: false,
      compactView: false,
    });
    setMonitoringSettings({
      healthCheckInterval: 30,
      metricsRetention: 24,
      logLevel: 'info',
      enableTracing: false,
      maxLogEntries: 1000,
      alertCooldown: 300,
    });
  };

  const handleEditRule = (rule: AlertRule) => {
    setEditRuleDialog(rule);
  };

  const handleSaveRule = (rule: AlertRule) => {
    setAlertRules(prev => 
      prev.map(r => r.id === rule.id ? rule : r)
    );
    setEditRuleDialog(null);
  };

  const handleDeleteRule = (ruleId: string) => {
    setAlertRules(prev => prev.filter(r => r.id !== ruleId));
  };

  const handleAddRule = () => {
    const newRule: AlertRule = {
      id: Date.now().toString(),
      name: 'New Alert Rule',
      condition: 'custom_metric > threshold',
      threshold: 50,
      severity: 'warning',
      enabled: true,
    };
    setEditRuleDialog(newRule);
  };

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Settings
        </Typography>
        
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            startIcon={<ResetIcon />}
            onClick={handleResetSettings}
          >
            Reset to Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveSettings}
          >
            Save Changes
          </Button>
        </Box>
      </Box>

      {/* Tab Navigation */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Dashboard" />
          <Tab label="Monitoring" />
          <Tab label="Agents" />
          <Tab label="Alerts" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {/* Dashboard Preferences */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Dashboard Preferences
                </Typography>
                
                <Box display="flex" flexDirection="column" gap={2}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={dashboardSettings.autoRefresh}
                        onChange={(e) => setDashboardSettings(prev => ({
                          ...prev,
                          autoRefresh: e.target.checked
                        }))}
                      />
                    }
                    label="Auto-refresh data"
                  />

                  <TextField
                    label="Refresh Interval (seconds)"
                    type="number"
                    value={dashboardSettings.refreshInterval}
                    onChange={(e) => setDashboardSettings(prev => ({
                      ...prev,
                      refreshInterval: Number(e.target.value)
                    }))}
                    disabled={!dashboardSettings.autoRefresh}
                    fullWidth
                  />

                  <FormControl fullWidth>
                    <InputLabel>Theme</InputLabel>
                    <Select
                      value={dashboardSettings.theme}
                      label="Theme"
                      onChange={(e) => setDashboardSettings(prev => ({
                        ...prev,
                        theme: e.target.value
                      }))}
                    >
                      <MenuItem value="dark">Dark</MenuItem>
                      <MenuItem value="light">Light</MenuItem>
                      <MenuItem value="auto">Auto</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControlLabel
                    control={
                      <Switch
                        checked={dashboardSettings.compactView}
                        onChange={(e) => setDashboardSettings(prev => ({
                          ...prev,
                          compactView: e.target.checked
                        }))}
                      />
                    }
                    label="Compact view"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Notification Settings */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Notifications
                </Typography>
                
                <Box display="flex" flexDirection="column" gap={2}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={dashboardSettings.showNotifications}
                        onChange={(e) => setDashboardSettings(prev => ({
                          ...prev,
                          showNotifications: e.target.checked
                        }))}
                      />
                    }
                    label="Show notifications"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={dashboardSettings.soundAlerts}
                        onChange={(e) => setDashboardSettings(prev => ({
                          ...prev,
                          soundAlerts: e.target.checked
                        }))}
                      />
                    }
                    label="Sound alerts"
                    disabled={!dashboardSettings.showNotifications}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 1 && (
        <Grid container spacing={3}>
          {/* Health Monitoring */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Health Monitoring
                </Typography>
                
                <Box display="flex" flexDirection="column" gap={2}>
                  <TextField
                    label="Health Check Interval (seconds)"
                    type="number"
                    value={monitoringSettings.healthCheckInterval}
                    onChange={(e) => setMonitoringSettings(prev => ({
                      ...prev,
                      healthCheckInterval: Number(e.target.value)
                    }))}
                    fullWidth
                  />

                  <TextField
                    label="Metrics Retention (hours)"
                    type="number"
                    value={monitoringSettings.metricsRetention}
                    onChange={(e) => setMonitoringSettings(prev => ({
                      ...prev,
                      metricsRetention: Number(e.target.value)
                    }))}
                    fullWidth
                  />

                  <FormControl fullWidth>
                    <InputLabel>Log Level</InputLabel>
                    <Select
                      value={monitoringSettings.logLevel}
                      label="Log Level"
                      onChange={(e) => setMonitoringSettings(prev => ({
                        ...prev,
                        logLevel: e.target.value
                      }))}
                    >
                      <MenuItem value="debug">Debug</MenuItem>
                      <MenuItem value="info">Info</MenuItem>
                      <MenuItem value="warn">Warning</MenuItem>
                      <MenuItem value="error">Error</MenuItem>
                    </Select>
                  </FormControl>

                  <TextField
                    label="Alert Cooldown (seconds)"
                    type="number"
                    value={monitoringSettings.alertCooldown}
                    onChange={(e) => setMonitoringSettings(prev => ({
                      ...prev,
                      alertCooldown: Number(e.target.value)
                    }))}
                    fullWidth
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Logging Settings */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Logging & Tracing
                </Typography>
                
                <Box display="flex" flexDirection="column" gap={2}>
                  <TextField
                    label="Max Log Entries"
                    type="number"
                    value={monitoringSettings.maxLogEntries}
                    onChange={(e) => setMonitoringSettings(prev => ({
                      ...prev,
                      maxLogEntries: Number(e.target.value)
                    }))}
                    fullWidth
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={monitoringSettings.enableTracing}
                        onChange={(e) => setMonitoringSettings(prev => ({
                          ...prev,
                          enableTracing: e.target.checked
                        }))}
                      />
                    }
                    label="Enable distributed tracing"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 2 && (
        <Grid container spacing={3}>
          {/* Agent Configuration */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Agent Configuration
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Max Workers"
                      type="number"
                      value={agentConfig.maxWorkers}
                      onChange={(e) => setAgentConfig(prev => ({
                        ...prev,
                        maxWorkers: Number(e.target.value)
                      }))}
                      fullWidth
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Max Memory per Worker (MB)"
                      type="number"
                      value={agentConfig.maxMemoryPerWorker}
                      onChange={(e) => setAgentConfig(prev => ({
                        ...prev,
                        maxMemoryPerWorker: Number(e.target.value)
                      }))}
                      fullWidth
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Max Execution Time (minutes)"
                      type="number"
                      value={agentConfig.maxExecutionTime}
                      onChange={(e) => setAgentConfig(prev => ({
                        ...prev,
                        maxExecutionTime: Number(e.target.value)
                      }))}
                      fullWidth
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Sync Interval (seconds)"
                      type="number"
                      value={agentConfig.syncInterval}
                      onChange={(e) => setAgentConfig(prev => ({
                        ...prev,
                        syncInterval: Number(e.target.value)
                      }))}
                      fullWidth
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Box display="flex" flexDirection="column" gap={1} mt={1}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={agentConfig.crossPollination}
                            onChange={(e) => setAgentConfig(prev => ({
                              ...prev,
                              crossPollination: e.target.checked
                            }))}
                          />
                        }
                        label="Cross-pollination"
                      />

                      <FormControlLabel
                        control={
                          <Switch
                            checked={agentConfig.adaptiveFocus}
                            onChange={(e) => setAgentConfig(prev => ({
                              ...prev,
                              adaptiveFocus: e.target.checked
                            }))}
                          />
                        }
                        label="Adaptive focus"
                      />
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Current Swarm Configuration */}
          {swarmConfig && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Current Swarm Configuration
                  </Typography>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    Name: {swarmConfig.name} | Version: {swarmConfig.version} | Mode: {swarmConfig.mode}
                  </Typography>
                  
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Workers ({swarmConfig.workers.length})
                    </Typography>
                    <List dense>
                      {swarmConfig.workers.map((worker, index) => (
                        <ListItem key={index}>
                          <ListItemText
                            primary={worker.name}
                            secondary={`${worker.role} - ${worker.priority} priority`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      {tabValue === 3 && (
        <Grid container spacing={3}>
          {/* Alert Rules */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    Alert Rules
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleAddRule}
                    size="small"
                  >
                    Add Rule
                  </Button>
                </Box>
                
                <List>
                  {alertRules.map((rule, index) => (
                    <React.Fragment key={rule.id}>
                      <ListItem>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="body1">{rule.name}</Typography>
                              <Switch
                                checked={rule.enabled}
                                onChange={(e) => {
                                  setAlertRules(prev =>
                                    prev.map(r => r.id === rule.id ? { ...r, enabled: e.target.checked } : r)
                                  );
                                }}
                                size="small"
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="textSecondary">
                                Condition: {rule.condition.replace('threshold', rule.threshold.toString())}
                              </Typography>
                              <Box display="flex" gap={1} mt={0.5}>
                                <Typography
                                  variant="caption"
                                  sx={{
                                    px: 1,
                                    py: 0.25,
                                    borderRadius: 1,
                                    bgcolor: rule.severity === 'critical' ? 'error.main' : 
                                             rule.severity === 'warning' ? 'warning.main' : 'info.main',
                                    color: 'white',
                                  }}
                                >
                                  {rule.severity.toUpperCase()}
                                </Typography>
                              </Box>
                            </Box>
                          }
                        />
                        <Box>
                          <IconButton size="small" onClick={() => handleEditRule(rule)}>
                            <EditIcon />
                          </IconButton>
                          <IconButton size="small" onClick={() => handleDeleteRule(rule.id)}>
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </ListItem>
                      {index < alertRules.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Edit Rule Dialog */}
      <Dialog open={!!editRuleDialog} onClose={() => setEditRuleDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editRuleDialog?.name === 'New Alert Rule' ? 'Add Alert Rule' : 'Edit Alert Rule'}
        </DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <TextField
              label="Rule Name"
              value={editRuleDialog?.name || ''}
              onChange={(e) => setEditRuleDialog(prev => prev ? { ...prev, name: e.target.value } : null)}
              fullWidth
            />
            <TextField
              label="Condition"
              value={editRuleDialog?.condition || ''}
              onChange={(e) => setEditRuleDialog(prev => prev ? { ...prev, condition: e.target.value } : null)}
              fullWidth
            />
            <TextField
              label="Threshold"
              type="number"
              value={editRuleDialog?.threshold || 0}
              onChange={(e) => setEditRuleDialog(prev => prev ? { ...prev, threshold: Number(e.target.value) } : null)}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Severity</InputLabel>
              <Select
                value={editRuleDialog?.severity || 'warning'}
                label="Severity"
                onChange={(e) => setEditRuleDialog(prev => prev ? { ...prev, severity: e.target.value as any } : null)}
              >
                <MenuItem value="info">Info</MenuItem>
                <MenuItem value="warning">Warning</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditRuleDialog(null)}>Cancel</Button>
          <Button 
            onClick={() => editRuleDialog && handleSaveRule(editRuleDialog)} 
            variant="contained"
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Save Status Snackbar */}
      <Snackbar
        open={saveStatus !== null}
        autoHideDuration={6000}
        onClose={() => setSaveStatus(null)}
      >
        <Alert 
          onClose={() => setSaveStatus(null)} 
          severity={saveStatus === 'success' ? 'success' : 'error'}
        >
          {saveStatus === 'success' ? 'Settings saved successfully!' : 'Failed to save settings.'}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings;