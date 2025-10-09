import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
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
} from 'recharts';
import { useHealthData } from '../../contexts/HealthDataContext';

const MetricsOverview: React.FC = () => {
  const { performanceMetrics } = useHealthData();

  if (!performanceMetrics) {
    return (
      <Grid container spacing={3}>
        {Array.from({ length: 4 }).map((_, index) => (
          <Grid item xs={12} md={6} key={index}>
            <Card>
              <CardContent>
                <Box height={200} display="flex" alignItems="center" justifyContent="center">
                  <Typography color="textSecondary">Loading metrics...</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Prepare data for charts
  const tgeDetectionData = performanceMetrics.tgeDetectionTotal.map((point, index) => ({
    time: formatTime(point.timestamp),
    detected: point.value,
    falsePositives: performanceMetrics.tgeFalsePositives[index]?.value || 0,
    accuracy: performanceMetrics.detectionAccuracy[index]?.value || 0,
  }));

  const apiMetricsData = performanceMetrics.apiCallsTotal.map((point, index) => ({
    time: formatTime(point.timestamp),
    apiCalls: point.value,
    efficiency: performanceMetrics.apiEfficiency[index]?.value || 0,
    responseTime: performanceMetrics.scrapingDuration[index]?.value || 0,
  }));

  const systemMetricsData = performanceMetrics.memoryUsage.map((point, index) => ({
    time: formatTime(point.timestamp),
    memory: point.value,
    cpu: performanceMetrics.cpuUsage[index]?.value || 0,
    agentHealth: performanceMetrics.agentHealthRatio[index]?.value || 0,
  }));

  const keywordMatchData = performanceMetrics.keywordMatches.map((point) => ({
    time: formatTime(point.timestamp),
    matches: point.value,
  }));

  return (
    <Grid container spacing={3}>
      {/* TGE Detection Metrics */}
      <Grid item xs={12} lg={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              TGE Detection Performance
            </Typography>
            <Box height={250}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={tgeDetectionData}>
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
                    dataKey="detected"
                    stroke="#4FC3F7"
                    strokeWidth={2}
                    dot={{ fill: '#4FC3F7', strokeWidth: 2, r: 3 }}
                    name="TGEs Detected"
                  />
                  <Line
                    type="monotone"
                    dataKey="falsePositives"
                    stroke="#F44336"
                    strokeWidth={2}
                    dot={{ fill: '#F44336', strokeWidth: 2, r: 3 }}
                    name="False Positives"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* API Metrics */}
      <Grid item xs={12} lg={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              API Performance
            </Typography>
            <Box height={250}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={apiMetricsData}>
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
                  <Area
                    type="monotone"
                    dataKey="apiCalls"
                    stroke="#81C784"
                    fill="#81C784"
                    fillOpacity={0.3}
                    name="API Calls"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* System Health Metrics */}
      <Grid item xs={12} lg={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              System Health
            </Typography>
            <Box height={250}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={systemMetricsData}>
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
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Keyword Matching */}
      <Grid item xs={12} lg={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Keyword Matching Activity
            </Typography>
            <Box height={250}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={keywordMatchData}>
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
                  <Bar
                    dataKey="matches"
                    fill="#9C27B0"
                    name="Keyword Matches"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default MetricsOverview;