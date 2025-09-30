#!/usr/bin/env python3
"""
Health Check Endpoint for Crypto TGE Monitor
Provides HTTP endpoints for monitoring system health
"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import validate_config
from src.utils import HealthChecker

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks"""
    
    def __init__(self, *args, health_checker=None, **kwargs):
        self.health_checker = health_checker
        self.logger = logging.getLogger("health_endpoint")
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == '/health':
                self._handle_health()
            elif self.path == '/status':
                self._handle_status()
            elif self.path == '/metrics':
                self._handle_metrics()
            elif self.path == '/ready':
                self._handle_ready()
            else:
                self._send_response(404, {'error': 'Not found'})
        except Exception as e:
            self.logger.error(f"Error handling request {self.path}: {e}")
            self._send_response(500, {'error': 'Internal server error'})
    
    def _handle_health(self):
        """Basic health check - is the service running?"""
        try:
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'crypto-tge-monitor',
                'version': '1.0.0'
            }
            self._send_response(200, health_data)
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self._send_response(503, {'status': 'unhealthy', 'error': str(e)})
    
    def _handle_status(self):
        """Detailed status including component health"""
        try:
            # Get configuration validation
            config_status = validate_config()
            
            # Get service health if health_checker is available
            component_health = {}
            if self.health_checker:
                try:
                    component_health = self.health_checker.get_all_health_status()
                except Exception as e:
                    self.logger.warning(f"Failed to get component health: {e}")
            
            # Check system resources
            system_status = self._get_system_status()
            
            # Check application state
            app_status = self._get_app_status()
            
            # Determine overall status
            overall_healthy = (
                all(config_status.values()) and
                all(component_health.values()) if component_health else True and
                system_status.get('disk_usage', 0) < 90 and
                system_status.get('memory_usage', 0) < 90
            )
            
            status_data = {
                'status': 'healthy' if overall_healthy else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'configuration': config_status,
                'components': component_health,
                'system': system_status,
                'application': app_status
            }
            
            status_code = 200 if overall_healthy else 503
            self._send_response(status_code, status_data)
            
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            self._send_response(500, {'status': 'error', 'error': str(e)})
    
    def _handle_metrics(self):
        """Prometheus-style metrics"""
        try:
            metrics = []
            
            # Service uptime
            uptime = self._get_service_uptime()
            metrics.append(f'crypto_tge_monitor_uptime_seconds {uptime}')
            
            # System metrics
            system_status = self._get_system_status()
            metrics.append(f'crypto_tge_monitor_cpu_usage_percent {system_status.get("cpu_usage", 0)}')
            metrics.append(f'crypto_tge_monitor_memory_usage_percent {system_status.get("memory_usage", 0)}')
            metrics.append(f'crypto_tge_monitor_disk_usage_percent {system_status.get("disk_usage", 0)}')
            
            # Application metrics
            app_status = self._get_app_status()
            if app_status.get('last_run_time'):
                last_run_timestamp = int(datetime.fromisoformat(app_status['last_run_time'].replace('Z', '+00:00')).timestamp())
                metrics.append(f'crypto_tge_monitor_last_run_timestamp {last_run_timestamp}')
            
            metrics.append(f'crypto_tge_monitor_total_alerts {app_status.get("total_alerts", 0)}')
            
            # Configuration status
            config_status = validate_config()
            metrics.append(f'crypto_tge_monitor_config_valid {1 if all(config_status.values()) else 0}')
            
            metrics_text = '\n'.join(metrics) + '\n'
            self._send_text_response(200, metrics_text)
            
        except Exception as e:
            self.logger.error(f"Metrics collection failed: {e}")
            self._send_response(500, {'error': 'Failed to collect metrics'})
    
    def _handle_ready(self):
        """Readiness check - is the service ready to handle requests?"""
        try:
            # Check if configuration is valid
            config_status = validate_config()
            config_ready = all(config_status.values())
            
            # Check if required files exist
            required_files = [
                '/opt/crypto-tge-monitor/.env',
                '/var/lib/crypto-tge-monitor',
                '/var/log/crypto-tge-monitor'
            ]
            
            files_ready = all(os.path.exists(f) for f in required_files)
            
            # Check if we can connect to external services
            network_ready = self._check_network_connectivity()
            
            ready = config_ready and files_ready and network_ready
            
            ready_data = {
                'ready': ready,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'checks': {
                    'configuration': config_ready,
                    'files': files_ready,
                    'network': network_ready
                }
            }
            
            status_code = 200 if ready else 503
            self._send_response(status_code, ready_data)
            
        except Exception as e:
            self.logger.error(f"Readiness check failed: {e}")
            self._send_response(500, {'ready': False, 'error': str(e)})
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get system resource status"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Load average (Unix only)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except (AttributeError, OSError):
                pass
            
            return {
                'cpu_usage': round(cpu_percent, 2),
                'memory_usage': round(memory_percent, 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage': round(disk_percent, 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'load_average': load_avg
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': f'Failed to get system status: {e}'}
    
    def _get_app_status(self) -> Dict[str, Any]:
        """Get application-specific status"""
        try:
            status = {}
            
            # Check state directory
            state_dir = '/var/lib/crypto-tge-monitor'
            if os.path.exists(state_dir):
                status['state_directory'] = 'exists'
                
                # Check for state files
                state_files = ['monitor_state.json', 'seen.json', 'twitter_since.json']
                status['state_files'] = {}
                
                for file_name in state_files:
                    file_path = os.path.join(state_dir, file_name)
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        status['state_files'][file_name] = {
                            'exists': True,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                        }
                    else:
                        status['state_files'][file_name] = {'exists': False}
            
            # Check log files
            log_dir = '/var/log/crypto-tge-monitor'
            if os.path.exists(log_dir):
                log_file = os.path.join(log_dir, 'crypto_monitor.log')
                if os.path.exists(log_file):
                    stat = os.stat(log_file)
                    status['log_file'] = {
                        'exists': True,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                    }
            
            # Try to read monitor state
            try:
                state_file = os.path.join(state_dir, 'monitor_state.json')
                if os.path.exists(state_file):
                    with open(state_file, 'r') as f:
                        monitor_state = json.load(f)
                        status.update({
                            'last_run_time': monitor_state.get('last_run_time'),
                            'total_alerts': monitor_state.get('total_alerts_sent', 0),
                            'total_news_processed': monitor_state.get('total_news_processed', 0),
                            'total_tweets_processed': monitor_state.get('total_tweets_processed', 0)
                        })
            except Exception as e:
                status['monitor_state_error'] = str(e)
            
            return status
            
        except Exception as e:
            return {'error': f'Failed to get app status: {e}'}
    
    def _get_service_uptime(self) -> int:
        """Get service uptime in seconds"""
        try:
            import psutil
            
            # Find the main process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if 'crypto-tge-monitor' in ' '.join(proc.info['cmdline'] or []):
                        create_time = proc.info['create_time']
                        uptime = time.time() - create_time
                        return int(uptime)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return 0
        except ImportError:
            return 0
        except Exception:
            return 0
    
    def _check_network_connectivity(self) -> bool:
        """Check if we can reach external services"""
        try:
            import urllib.request
            import socket
            
            # Test DNS resolution and HTTP connectivity
            test_urls = [
                'https://www.google.com',
                'https://api.twitter.com',
                'https://feeds.feedburner.com'
            ]
            
            for url in test_urls:
                try:
                    req = urllib.request.Request(url, method='HEAD')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        if response.status == 200:
                            return True
                except:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _send_response(self, status_code: int, data: Dict[str, Any]):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        response_data = json.dumps(data, indent=2)
        self.wfile.write(response_data.encode('utf-8'))
    
    def _send_text_response(self, status_code: int, text: str):
        """Send plain text response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        self.wfile.write(text.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        self.logger.info(format % args)


class HealthServer:
    """HTTP server for health checks"""
    
    def __init__(self, port: int = 8080, health_checker=None):
        self.port = port
        self.health_checker = health_checker
        self.server = None
        self.thread = None
        self.logger = logging.getLogger("health_server")
    
    def start(self):
        """Start the health check server"""
        try:
            # Create handler class with our health_checker
            handler_class = lambda *args, **kwargs: HealthHandler(*args, health_checker=self.health_checker, **kwargs)
            
            self.server = HTTPServer(('127.0.0.1', self.port), handler_class)
            
            # Start in a separate thread
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            self.logger.info(f"Health check server started on port {self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start health server: {e}")
    
    def stop(self):
        """Stop the health check server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            
        if self.thread:
            self.thread.join(timeout=5)
        
        self.logger.info("Health check server stopped")


def main():
    """Run health server standalone for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = HealthServer(port=8080)
    server.start()
    
    try:
        print("Health server running on http://localhost:8080")
        print("Endpoints:")
        print("  /health  - Basic health check")
        print("  /status  - Detailed status")
        print("  /metrics - Prometheus metrics")
        print("  /ready   - Readiness check")
        print("\nPress Ctrl+C to stop")
        
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping health server...")
        server.stop()


if __name__ == "__main__":
    main()