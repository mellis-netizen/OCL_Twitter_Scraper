import React, { useState } from 'react';
import {
  AppBar,
  Box,
  CssBaseline,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Badge,
  Chip,
  Tooltip,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Analytics as AnalyticsIcon,
  ViewList as LogsIcon,
  Settings as SettingsIcon,
  Memory as AgentsIcon,
  Refresh as RefreshIcon,
  CloudOff as DisconnectedIcon,
  CloudDone as ConnectedIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { useHealthData } from '../../contexts/HealthDataContext';

const drawerWidth = 240;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { isConnected, connectionError } = useWebSocket();
  const { systemStats, isLoading, refreshData, agentStatuses } = useHealthData();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const navigationItems = [
    {
      text: 'Dashboard',
      icon: <DashboardIcon />,
      path: '/dashboard',
      badge: null,
    },
    {
      text: 'Agents',
      icon: <AgentsIcon />,
      path: '/agents',
      badge: systemStats ? systemStats.healthyAgents : null,
    },
    {
      text: 'Performance Metrics',
      icon: <AnalyticsIcon />,
      path: '/metrics',
      badge: null,
    },
    {
      text: 'Logs',
      icon: <LogsIcon />,
      path: '/logs',
      badge: null,
    },
    {
      text: 'Settings',
      icon: <SettingsIcon />,
      path: '/settings',
      badge: null,
    },
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const getHealthyAgentsCount = () => {
    return agentStatuses.filter(agent => agent.status === 'healthy').length;
  };

  const getTotalAgentsCount = () => {
    return agentStatuses.length;
  };

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div" color="primary">
          TGE Swarm
        </Typography>
      </Toolbar>
      <List>
        {navigationItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'rgba(79, 195, 247, 0.1)',
                  borderRight: '3px solid',
                  borderRightColor: 'primary.main',
                },
              }}
            >
              <ListItemIcon>
                {item.badge !== null ? (
                  <Badge badgeContent={item.badge} color="secondary">
                    {item.icon}
                  </Badge>
                ) : (
                  item.icon
                )}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          zIndex: theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            TGE Swarm Optimization Dashboard
          </Typography>

          {/* System Status Indicators */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Agent Status */}
            <Tooltip title={`${getHealthyAgentsCount()}/${getTotalAgentsCount()} agents healthy`}>
              <Chip
                icon={<AgentsIcon />}
                label={`${getHealthyAgentsCount()}/${getTotalAgentsCount()}`}
                color={getHealthyAgentsCount() === getTotalAgentsCount() ? 'success' : 'warning'}
                size="small"
              />
            </Tooltip>

            {/* Connection Status */}
            <Tooltip title={isConnected ? 'Connected to monitoring system' : connectionError || 'Disconnected'}>
              <IconButton color="inherit" size="small">
                {isConnected ? (
                  <ConnectedIcon color="success" />
                ) : (
                  <DisconnectedIcon color="error" />
                )}
              </IconButton>
            </Tooltip>

            {/* Refresh Button */}
            <Tooltip title="Refresh data">
              <IconButton
                color="inherit"
                onClick={refreshData}
                disabled={isLoading}
                size="small"
              >
                <RefreshIcon sx={{
                  animation: isLoading ? 'spin 1s linear infinite' : 'none',
                  '@keyframes spin': {
                    '0%': {
                      transform: 'rotate(0deg)',
                    },
                    '100%': {
                      transform: 'rotate(360deg)',
                    },
                  },
                }} />
              </IconButton>
            </Tooltip>

            {/* TGE Detection Stats */}
            {systemStats && (
              <Chip
                label={`${systemStats.totalTgeDetected} TGEs | ${systemStats.accuracy.toFixed(1)}% accuracy`}
                color="primary"
                size="small"
                sx={{ display: { xs: 'none', md: 'flex' } }}
              />
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="navigation"
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: 'background.default',
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
};

export default Layout;