import React, { useState } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Tab,
  Tabs,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ComposedChart,
  ReferenceLine,
} from 'recharts';
import { useHealthData } from '../contexts/HealthDataContext';

const PerformanceMetrics: React.FC = () => {
  const { performanceMetrics } = useHealthData();
  const [timeRange, setTimeRange] = useState('24h');
  const [tabValue, setTabValue] = useState(0);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    if (timeRange === '1h') {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } else {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    }
  };

  const handleTimeRangeChange = (
    event: React.MouseEvent<HTMLElement>,
    newTimeRange: string,
  ) => {
    if (newTimeRange !== null) {
      setTimeRange(newTimeRange);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (!performanceMetrics) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Typography variant="h6" color="textSecondary">
          Loading performance metrics...
        </Typography>
      </Box>
    );
  }

  // Prepare comprehensive data for charts
  const tgeMetricsData = performanceMetrics.tgeDetectionTotal.map((point, index) => ({
    time: formatTime(point.timestamp),
    fullTime: point.timestamp,
    detected: point.value,
    falsePositives: performanceMetrics.tgeFalsePositives[index]?.value || 0,
    accuracy: performanceMetrics.detectionAccuracy[index]?.value || 0,
    precision: Math.max(0, 100 - (performanceMetrics.tgeFalsePositives[index]?.value || 0) / Math.max(point.value, 1) * 100),
  }));

  const systemPerformanceData = performanceMetrics.memoryUsage.map((point, index) => ({
    time: formatTime(point.timestamp),
    fullTime: point.timestamp,
    memory: point.value,
    cpu: performanceMetrics.cpuUsage[index]?.value || 0,
    agentHealth: performanceMetrics.agentHealthRatio[index]?.value || 0,
    responseTime: performanceMetrics.scrapingDuration[index]?.value || 0,
  }));

  const apiPerformanceData = performanceMetrics.apiCallsTotal.map((point, index) => ({
    time: formatTime(point.timestamp),
    fullTime: point.timestamp,
    apiCalls: point.value,
    efficiency: performanceMetrics.apiEfficiency[index]?.value || 0,
    keywordMatches: performanceMetrics.keywordMatches[index]?.value || 0,
    detectedPerCall: (performanceMetrics.tgeDetectionTotal[index]?.value || 0) / Math.max(point.value, 1),
  }));

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Performance Metrics
        </Typography>
        
        <ToggleButtonGroup
          value={timeRange}
          exclusive
          onChange={handleTimeRangeChange}
          size="small"
        >
          <ToggleButton value="1h">1H</ToggleButton>
          <ToggleButton value="6h">6H</ToggleButton>
          <ToggleButton value="24h">24H</ToggleButton>
          <ToggleButton value="7d">7D</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Tab Navigation */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="TGE Detection" />
          <Tab label="System Performance" />
          <Tab label="API Efficiency" />
          <Tab label="Comparative Analysis" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <Grid container spacing={3}>
          {/* TGE Detection Over Time */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  TGE Detection Performance
                </Typography>
                <Box height={400}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={tgeMetricsData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#9CA3AF"
                        fontSize={12}
                      />
                      <YAxis yAxisId="left" stroke="#9CA3AF" fontSize={12} />
                      <YAxis yAxisId="right" orientation="right" stroke="#9CA3AF" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="detected"
                        fill="#4FC3F7"
                        name="TGEs Detected"
                        radius={[2, 2, 0, 0]}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="falsePositives"
                        fill="#F44336"
                        name="False Positives"
                        radius={[2, 2, 0, 0]}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="accuracy"
                        stroke="#4CAF50"
                        strokeWidth={3}
                        dot={{ fill: '#4CAF50', strokeWidth: 2, r: 4 }}
                        name="Accuracy (%)"
                      />
                      <ReferenceLine yAxisId="right" y={95} stroke="#FF9800" strokeDasharray="5 5" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Accuracy Trends */}
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Accuracy Trends
                </Typography>
                <Box height={400}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={tgeMetricsData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#9CA3AF"
                        fontSize={10}
                      />
                      <YAxis stroke="#9CA3AF" fontSize={12} domain={[80, 100]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="accuracy"
                        stroke="#4CAF50"
                        fill="#4CAF50"
                        fillOpacity={0.3}
                        name="Accuracy (%)"
                      />
                      <Area
                        type="monotone"
                        dataKey="precision"
                        stroke="#2196F3"
                        fill="#2196F3"
                        fillOpacity={0.2}
                        name="Precision (%)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 1 && (
        <Grid container spacing={3}>
          {/* System Resource Usage */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Resource Usage
                </Typography>
                <Box height={400}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={systemPerformanceData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#9CA3AF"
                        fontSize={12}
                      />
                      <YAxis stroke="#9CA3AF" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="memory"
                        stroke="#FF9800"
                        strokeWidth={2}
                        dot={{ fill: '#FF9800', strokeWidth: 2, r: 3 }}
                        name="Memory Usage (%)"
                      />
                      <Line
                        type="monotone"
                        dataKey="cpu"
                        stroke="#2196F3"
                        strokeWidth={2}
                        dot={{ fill: '#2196F3', strokeWidth: 2, r: 3 }}
                        name="CPU Usage (%)"
                      />
                      <Line
                        type="monotone"
                        dataKey="agentHealth"
                        stroke="#4CAF50"
                        strokeWidth={2}
                        dot={{ fill: '#4CAF50', strokeWidth: 2, r: 3 }}
                        name="Agent Health (%)"
                      />
                      <ReferenceLine y={80} stroke="#F44336" strokeDasharray="5 5" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Response Time */}
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Response Time Trends
                </Typography>
                <Box height={400}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={systemPerformanceData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#9CA3AF"
                        fontSize={10}
                      />
                      <YAxis stroke="#9CA3AF" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="responseTime"
                        stroke="#9C27B0"
                        fill="#9C27B0"
                        fillOpacity={0.3}
                        name="Response Time (ms)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 2 && (
        <Grid container spacing={3}>
          {/* API Efficiency */}
          <Grid item xs={12} lg={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  API Call Efficiency
                </Typography>
                <Box height={400}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={apiPerformanceData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#9CA3AF"
                        fontSize={12}
                      />
                      <YAxis yAxisId="left" stroke="#9CA3AF" fontSize={12} />
                      <YAxis yAxisId="right" orientation="right" stroke="#9CA3AF" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="apiCalls"
                        fill="#81C784"
                        name="API Calls"
                        radius={[2, 2, 0, 0]}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="efficiency"
                        stroke="#FF5722"
                        strokeWidth={3}
                        dot={{ fill: '#FF5722', strokeWidth: 2, r: 4 }}
                        name="Efficiency Ratio"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Keyword Matching */}
          <Grid item xs={12} lg={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Detection per API Call
                </Typography>
                <Box height={400}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={apiPerformanceData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#9CA3AF"
                        fontSize={10}
                      />
                      <YAxis stroke="#9CA3AF" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                        formatter={(value: any) => [value.toFixed(4), 'TGEs per API Call']}
                      />
                      <Line
                        type="monotone"
                        dataKey="detectedPerCall"
                        stroke="#E91E63"
                        strokeWidth={2}
                        dot={{ fill: '#E91E63', strokeWidth: 2, r: 3 }}
                        name="TGEs per API Call"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tabValue === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Comparative Analysis
            </Typography>
            <Typography color="textSecondary">
              Comparative analysis charts and correlation matrices will be displayed here.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default PerformanceMetrics;