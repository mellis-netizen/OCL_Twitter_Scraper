#!/usr/bin/env python3
"""
Cost Optimizer for TGE Swarm Ultra-Low-Cost Deployment
Monitors costs, manages auto-shutdown, and optimizes resource usage
Cost Optimization Engineer: Claude
"""

import json
import logging
import os
import subprocess
import time
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/cost-optimizer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CostOptimizer:
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.cost_threshold = float(os.getenv('COST_THRESHOLD', '150'))
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '3600'))
        self.auto_shutdown_enabled = os.getenv('ENABLE_AUTO_SHUTDOWN', 'true').lower() == 'true'
        
        # AWS clients
        self.ce_client = boto3.client('ce', region_name=self.region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.sns = boto3.client('sns', region_name=self.region)
        
        # Try to get SNS topic ARN from SSM
        try:
            ssm = boto3.client('ssm', region_name=self.region)
            response = ssm.get_parameter(Name='/tge-swarm/sns-topic-arn')
            self.sns_topic_arn = response['Parameter']['Value']
        except Exception:
            self.sns_topic_arn = None
            logger.warning("SNS topic ARN not found in SSM")

    def get_current_month_cost(self) -> float:
        """Get current month's AWS costs"""
        try:
            now = datetime.now()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            total_cost = 0.0
            service_costs = {}
            
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    service_costs[service] = cost
                    total_cost += cost
            
            logger.info(f"Current month cost: ${total_cost:.2f}")
            return total_cost, service_costs
            
        except Exception as e:
            logger.error(f"Error getting cost data: {e}")
            return 0.0, {}

    def send_cost_alert(self, current_cost: float, service_costs: Dict[str, float]):
        """Send cost alert via SNS"""
        if not self.sns_topic_arn:
            logger.warning("No SNS topic configured for alerts")
            return
            
        try:
            message = f"""
TGE Swarm Cost Alert

Current month cost: ${current_cost:.2f}
Threshold: ${self.cost_threshold:.2f}
Status: {'⚠️  OVER BUDGET' if current_cost > self.cost_threshold else '✅ Within budget'}

Top service costs:
"""
            # Add top 5 service costs
            sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
            for service, cost in sorted_services:
                message += f"- {service}: ${cost:.2f}\n"
            
            message += f"\nTimestamp: {datetime.now().isoformat()}"
            
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject="TGE Swarm Cost Alert",
                Message=message
            )
            
            logger.info("Cost alert sent via SNS")
            
        except Exception as e:
            logger.error(f"Error sending cost alert: {e}")

    def publish_cost_metrics(self, cost: float, service_costs: Dict[str, float]):
        """Publish cost metrics to CloudWatch"""
        try:
            # Overall cost metric
            self.cloudwatch.put_metric_data(
                Namespace='TGE-Swarm/Cost',
                MetricData=[
                    {
                        'MetricName': 'MonthlySpend',
                        'Value': cost,
                        'Unit': 'None',
                        'Timestamp': datetime.now()
                    }
                ]
            )
            
            # Service-specific costs
            for service, service_cost in service_costs.items():
                if service_cost > 0:
                    self.cloudwatch.put_metric_data(
                        Namespace='TGE-Swarm/Cost',
                        MetricData=[
                            {
                                'MetricName': 'ServiceCost',
                                'Value': service_cost,
                                'Unit': 'None',
                                'Dimensions': [
                                    {
                                        'Name': 'Service',
                                        'Value': service
                                    }
                                ],
                                'Timestamp': datetime.now()
                            }
                        ]
                    )
            
            logger.info("Cost metrics published to CloudWatch")
            
        except Exception as e:
            logger.error(f"Error publishing cost metrics: {e}")

    def get_container_stats(self) -> Dict[str, Dict]:
        """Get Docker container resource usage stats"""
        try:
            # Get container stats
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Error getting container stats: {result.stderr}")
                return {}
            
            stats = {}
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 4:
                    container = parts[0]
                    cpu_perc = parts[1].replace('%', '')
                    mem_usage = parts[2]
                    mem_perc = parts[3].replace('%', '')
                    
                    stats[container] = {
                        'cpu_percent': float(cpu_perc) if cpu_perc else 0.0,
                        'memory_usage': mem_usage,
                        'memory_percent': float(mem_perc) if mem_perc else 0.0
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting container stats: {e}")
            return {}

    def optimize_container_resources(self, stats: Dict[str, Dict]):
        """Optimize container resources based on usage"""
        try:
            for container, stat in stats.items():
                cpu_percent = stat['cpu_percent']
                mem_percent = stat['memory_percent']
                
                # Log resource usage
                logger.info(f"{container}: CPU {cpu_percent}%, Memory {mem_percent}%")
                
                # Publish metrics
                self.cloudwatch.put_metric_data(
                    Namespace='TGE-Swarm/Containers',
                    MetricData=[
                        {
                            'MetricName': 'CPUUtilization',
                            'Value': cpu_percent,
                            'Unit': 'Percent',
                            'Dimensions': [{'Name': 'Container', 'Value': container}],
                            'Timestamp': datetime.now()
                        },
                        {
                            'MetricName': 'MemoryUtilization',
                            'Value': mem_percent,
                            'Unit': 'Percent',
                            'Dimensions': [{'Name': 'Container', 'Value': container}],
                            'Timestamp': datetime.now()
                        }
                    ]
                )
                
                # Alert on high resource usage
                if cpu_percent > 90 or mem_percent > 90:
                    logger.warning(f"High resource usage detected: {container}")
                    if self.sns_topic_arn:
                        self.sns.publish(
                            TopicArn=self.sns_topic_arn,
                            Subject="TGE Swarm Resource Alert",
                            Message=f"High resource usage detected:\n"
                                   f"Container: {container}\n"
                                   f"CPU: {cpu_percent}%\n"
                                   f"Memory: {mem_percent}%"
                        )
                        
        except Exception as e:
            logger.error(f"Error optimizing container resources: {e}")

    def cleanup_old_logs(self):
        """Clean up old log files to save space"""
        try:
            log_dirs = ['/app/logs', '/opt/tge-swarm/logs']
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    # Remove files older than 7 days
                    cutoff = time.time() - (7 * 24 * 60 * 60)
                    
                    for filename in os.listdir(log_dir):
                        filepath = os.path.join(log_dir, filename)
                        if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                            os.remove(filepath)
                            logger.info(f"Removed old log file: {filename}")
                            
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")

    def check_disk_space(self):
        """Check disk space and alert if running low"""
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    fields = lines[1].split()
                    if len(fields) >= 5:
                        usage_percent = int(fields[4].replace('%', ''))
                        
                        if usage_percent > 85:
                            logger.warning(f"Disk usage high: {usage_percent}%")
                            if self.sns_topic_arn:
                                self.sns.publish(
                                    TopicArn=self.sns_topic_arn,
                                    Subject="TGE Swarm Disk Space Alert",
                                    Message=f"Disk usage is {usage_percent}%. Consider cleanup."
                                )
                        
                        # Publish metric
                        self.cloudwatch.put_metric_data(
                            Namespace='TGE-Swarm/System',
                            MetricData=[
                                {
                                    'MetricName': 'DiskUtilization',
                                    'Value': usage_percent,
                                    'Unit': 'Percent',
                                    'Timestamp': datetime.now()
                                }
                            ]
                        )
                        
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")

    def run_optimization_cycle(self):
        """Run a complete optimization cycle"""
        logger.info("Starting cost optimization cycle")
        
        try:
            # Check costs
            current_cost, service_costs = self.get_current_month_cost()
            
            # Send alert if over threshold
            if current_cost > self.cost_threshold:
                logger.warning(f"Cost threshold exceeded: ${current_cost:.2f} > ${self.cost_threshold:.2f}")
                self.send_cost_alert(current_cost, service_costs)
            
            # Publish cost metrics
            self.publish_cost_metrics(current_cost, service_costs)
            
            # Check container resources
            container_stats = self.get_container_stats()
            self.optimize_container_resources(container_stats)
            
            # System maintenance
            self.cleanup_old_logs()
            self.check_disk_space()
            
            logger.info("Cost optimization cycle completed")
            
        except Exception as e:
            logger.error(f"Error in optimization cycle: {e}")

    def run(self):
        """Main run loop"""
        logger.info("TGE Swarm Cost Optimizer started")
        logger.info(f"Cost threshold: ${self.cost_threshold:.2f}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        while True:
            try:
                self.run_optimization_cycle()
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Cost optimizer stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)  # Wait before retrying

def lambda_handler(event, context):
    """AWS Lambda handler for scheduled cost optimization"""
    optimizer = CostOptimizer()
    optimizer.run_optimization_cycle()
    
    return {
        'statusCode': 200,
        'body': json.dumps('Cost optimization completed')
    }

if __name__ == "__main__":
    optimizer = CostOptimizer()
    optimizer.run()