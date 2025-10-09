import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import AgentDetails from './pages/AgentDetails';
import PerformanceMetrics from './pages/PerformanceMetrics';
import LogViewer from './pages/LogViewer';
import Settings from './pages/Settings';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { HealthDataProvider } from './contexts/HealthDataContext';

const App: React.FC = () => {
  return (
    <WebSocketProvider>
      <HealthDataProvider>
        <Box sx={{ display: 'flex', minHeight: '100vh' }}>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/agent/:agentId" element={<AgentDetails />} />
              <Route path="/metrics" element={<PerformanceMetrics />} />
              <Route path="/logs" element={<LogViewer />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </Box>
      </HealthDataProvider>
    </WebSocketProvider>
  );
};

export default App;