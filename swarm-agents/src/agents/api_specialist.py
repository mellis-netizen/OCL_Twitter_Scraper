#!/usr/bin/env python3
"""
API Reliability Optimizer Agent
Enhances error handling and API resilience for TGE detection
"""

import asyncio
import re
from typing import Dict, List, Any, Tuple
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from .base_agent import TGEAgent, AgentCapability, TaskResult


class APIReliabilityOptimizer(TGEAgent):
    """
    Specialized agent for API reliability and error handling
    Focuses on:
    - Error handling robustness
    - Retry mechanism optimization
    - Circuit breaker implementation
    - Rate limit intelligent backoff
    """

    def __init__(self, agent_id: str, config: Dict[str, Any] = None):
        super().__init__(
            agent_id=agent_id,
            agent_type="api-reliability-optimizer",
            capabilities=[
                AgentCapability.ERROR_HANDLING,
                AgentCapability.CIRCUIT_BREAKERS,
                AgentCapability.API_OPTIMIZATION
            ],
            specializations=[
                "twitter-api-optimization",
                "news-api-reliability",
                "graceful-degradation",
                "backoff-strategies"
            ],
            config=config
        )

        # Reliability-specific configuration
        self.target_error_reduction = 0.90  # 90% error reduction goal
        self.target_uptime = 0.999  # 99.9% uptime goal

    async def execute_specialized_task(
        self,
        task: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Execute API reliability optimization task"""

        task_type = task.get('type', 'analyze')
        target_files = task.get('target_files', [])

        findings = []
        optimizations = []

        try:
            if task_type == 'analyze':
                # Analyze API error handling
                for file_path in target_files:
                    file_findings, file_optimizations = await self._analyze_error_handling(file_path)
                    findings.extend(file_findings)
                    optimizations.extend(file_optimizations)

            elif task_type == 'implement_circuit_breakers':
                # Generate circuit breaker implementation
                cb_optimizations = await self._implement_circuit_breakers()
                optimizations.extend(cb_optimizations)

            elif task_type == 'optimize_retry_logic':
                # Optimize retry mechanisms
                retry_optimizations = await self._optimize_retry_logic()
                optimizations.extend(retry_optimizations)

            elif task_type == 'rate_limit_handling':
                # Improve rate limit handling
                rl_optimizations = await self._improve_rate_limit_handling()
                optimizations.extend(rl_optimizations)

        except Exception as e:
            self.logger.error(f"Error executing API reliability task: {e}")
            findings.append({
                'type': 'error',
                'severity': 'high',
                'message': str(e)
            })

        return findings, optimizations

    async def _analyze_error_handling(
        self,
        file_path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Analyze error handling patterns for reliability improvements"""

        findings = []
        optimizations = []

        try:
            full_path = Path(file_path)
            if not full_path.exists():
                full_path = Path('../') / file_path

            if not full_path.exists():
                return findings, optimizations

            with open(full_path, 'r') as f:
                content = f.read()

            # Pattern 1: Bare except clauses
            bare_except_pattern = r'except\s*:'
            bare_except_matches = re.findall(bare_except_pattern, content)

            if bare_except_matches:
                optimizations.append({
                    'type': 'specific_exceptions',
                    'file': str(file_path),
                    'severity': 'critical',
                    'current_issue': f'Found {len(bare_except_matches)} bare except clauses',
                    'recommendation': 'Use specific exception types for better error handling',
                    'implementation': {
                        'pattern': '''
try:
    result = await api_call()
except aiohttp.ClientError as e:
    # Handle connection errors
except asyncio.TimeoutError as e:
    # Handle timeouts
except KeyError as e:
    # Handle missing data
                        ''',
                        'benefits': [
                            'Better error recovery',
                            'Improved debugging',
                            'Targeted retry logic'
                        ]
                    },
                    'potential_improvement': '60-80% better error recovery',
                    'priority': 'critical'
                })

            # Pattern 2: No retry mechanism
            retry_indicators = ['retry', 'attempt', 'Retry', 'backoff', 'tenacity']
            has_retry = any(indicator in content for indicator in retry_indicators)

            if ('requests.' in content or 'ClientSession' in content) and not has_retry:
                optimizations.append({
                    'type': 'retry_mechanism',
                    'file': str(file_path),
                    'severity': 'critical',
                    'current_issue': 'No retry mechanism detected for API calls',
                    'recommendation': 'Implement exponential backoff retry strategy',
                    'implementation': {
                        'library': 'tenacity or custom implementation',
                        'pattern': '''
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def api_call_with_retry():
    # API call implementation
                        ''',
                        'parameters': {
                            'max_attempts': 3,
                            'initial_wait': '2 seconds',
                            'max_wait': '60 seconds',
                            'exponential_base': 2
                        }
                    },
                    'potential_improvement': '80-90% error recovery rate',
                    'priority': 'critical'
                })

            # Pattern 3: No circuit breaker
            cb_indicators = ['CircuitBreaker', 'circuit_breaker', 'breaker', 'failing_threshold']
            has_circuit_breaker = any(indicator in content for indicator in cb_indicators)

            if ('requests.' in content or 'ClientSession' in content) and not has_circuit_breaker:
                optimizations.append({
                    'type': 'circuit_breaker',
                    'file': str(file_path),
                    'severity': 'high',
                    'current_issue': 'No circuit breaker pattern detected',
                    'recommendation': 'Implement circuit breaker to prevent cascade failures',
                    'implementation': {
                        'pattern': '''
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise
                        ''',
                        'benefits': [
                            'Prevent cascade failures',
                            'Automatic recovery',
                            'Protect downstream services'
                        ]
                    },
                    'potential_improvement': '95%+ uptime under failure conditions',
                    'priority': 'high'
                })

            # Pattern 4: Poor timeout handling
            timeout_count = content.count('timeout')
            api_call_count = content.count('requests.') + content.count('ClientSession')

            if api_call_count > 0 and timeout_count < api_call_count:
                optimizations.append({
                    'type': 'timeout_handling',
                    'file': str(file_path),
                    'severity': 'high',
                    'current_issue': 'Missing or insufficient timeout configuration',
                    'recommendation': 'Implement comprehensive timeout strategy',
                    'implementation': {
                        'total_timeout': '30 seconds (end-to-end)',
                        'connect_timeout': '10 seconds',
                        'read_timeout': '20 seconds',
                        'pattern': '''
async with aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(
        total=30,
        connect=10,
        sock_read=20
    )
) as session:
    async with session.get(url) as response:
        return await response.json()
                        '''
                    },
                    'potential_improvement': 'Prevent hanging requests',
                    'priority': 'high'
                })

            # Pattern 5: No rate limit handling
            rate_limit_indicators = ['rate_limit', 'RateLimit', '429', 'X-RateLimit', 'Retry-After']
            has_rate_limit = any(indicator in content for indicator in rate_limit_indicators)

            if ('twitter' in file_path.lower() or 'api' in file_path.lower()) and not has_rate_limit:
                optimizations.append({
                    'type': 'rate_limit_handling',
                    'file': str(file_path),
                    'severity': 'critical',
                    'current_issue': 'No rate limit handling detected',
                    'recommendation': 'Implement intelligent rate limit handling',
                    'implementation': {
                        'detection': 'Check for 429 status codes and Retry-After headers',
                        'response': 'Honor Retry-After header or use exponential backoff',
                        'prevention': 'Track request counts and implement sliding window',
                        'pattern': '''
async def handle_rate_limit(response):
    if response.status == 429:
        retry_after = response.headers.get('Retry-After', 60)
        logger.warning(f"Rate limited, waiting {retry_after}s")
        await asyncio.sleep(int(retry_after))
        return await retry_request()
    return response
                        '''
                    },
                    'potential_improvement': 'Zero API bans, sustained operation',
                    'priority': 'critical'
                })

            # Pattern 6: No graceful degradation
            fallback_indicators = ['fallback', 'default', 'degraded', 'alternative']
            has_fallback = any(indicator in content for indicator in fallback_indicators)

            if not has_fallback and ('api' in file_path.lower() or 'scraper' in file_path.lower()):
                optimizations.append({
                    'type': 'graceful_degradation',
                    'file': str(file_path),
                    'severity': 'medium',
                    'current_issue': 'No graceful degradation strategy',
                    'recommendation': 'Implement fallback mechanisms',
                    'implementation': {
                        'strategies': [
                            'Use cached data when API fails',
                            'Fall back to alternative data source',
                            'Return partial results instead of failing completely',
                            'Degrade to read-only mode'
                        ],
                        'pattern': '''
async def fetch_data_with_fallback(primary_source, cache):
    try:
        data = await primary_source.fetch()
        await cache.store(data)
        return data
    except Exception as e:
        logger.warning(f"Primary source failed: {e}, using cache")
        cached_data = await cache.get()
        if cached_data:
            return cached_data
        raise ServiceDegradedError("All sources unavailable")
                        '''
                    },
                    'potential_improvement': '40-60% better availability',
                    'priority': 'medium'
                })

        except Exception as e:
            self.logger.error(f"Error analyzing error handling in {file_path}: {e}")

        return findings, optimizations

    async def _implement_circuit_breakers(self) -> List[Dict[str, Any]]:
        """Generate circuit breaker implementation recommendations"""

        optimizations = []

        # Twitter API circuit breaker
        optimizations.append({
            'type': 'twitter_circuit_breaker',
            'recommendation': 'Implement circuit breaker for Twitter API',
            'implementation': {
                'failure_threshold': 5,
                'timeout': 300,  # 5 minutes
                'half_open_requests': 1,
                'success_threshold': 2,
                'monitored_errors': [
                    'ConnectionError',
                    'Timeout',
                    'HTTPError (status >= 500)',
                    'Rate limit (429)'
                ],
                'recovery_strategy': 'Exponential backoff + health check'
            },
            'potential_improvement': '99.9% service availability',
            'priority': 'critical'
        })

        # News RSS circuit breaker
        optimizations.append({
            'type': 'news_circuit_breaker',
            'recommendation': 'Per-source circuit breakers for news feeds',
            'implementation': {
                'individual_breakers': 'One circuit breaker per news source',
                'failure_threshold': 3,
                'timeout': 180,  # 3 minutes
                'benefit': 'One failing source doesn\'t affect others',
                'fallback': 'Continue with healthy sources only'
            },
            'potential_improvement': '95%+ data collection uptime',
            'priority': 'high'
        })

        return optimizations

    async def _optimize_retry_logic(self) -> List[Dict[str, Any]]:
        """Generate retry logic optimization recommendations"""

        optimizations = []

        # Exponential backoff
        optimizations.append({
            'type': 'exponential_backoff',
            'recommendation': 'Implement exponential backoff with jitter',
            'implementation': {
                'formula': 'wait_time = min(base * 2^attempt + random_jitter, max_wait)',
                'parameters': {
                    'base': '2 seconds',
                    'max_attempts': 5,
                    'max_wait': '300 seconds',
                    'jitter': '0-1 seconds random'
                },
                'benefits': [
                    'Reduces server load during failures',
                    'Prevents thundering herd problem',
                    'Better recovery rates'
                ]
            },
            'potential_improvement': '80-90% successful retries',
            'priority': 'critical'
        })

        # Retry decision logic
        optimizations.append({
            'type': 'smart_retry',
            'recommendation': 'Implement intelligent retry decision logic',
            'implementation': {
                'retry_conditions': {
                    'always_retry': [
                        'Connection timeout',
                        'Connection refused',
                        'Temporary DNS failure',
                        'Status 500, 502, 503, 504'
                    ],
                    'conditional_retry': [
                        'Status 429 (if Retry-After present)',
                        'Read timeout (partial response)'
                    ],
                    'never_retry': [
                        'Status 400, 401, 403, 404',
                        'Invalid API key',
                        'Malformed request'
                    ]
                },
                'optimization': 'Don\'t waste retries on unrecoverable errors'
            },
            'potential_improvement': '60-70% fewer wasted retries',
            'priority': 'high'
        })

        return optimizations

    async def _improve_rate_limit_handling(self) -> List[Dict[str, Any]]:
        """Generate rate limit handling improvements"""

        optimizations = []

        # Adaptive rate limiting
        optimizations.append({
            'type': 'adaptive_rate_limiting',
            'recommendation': 'Implement adaptive rate limiting',
            'implementation': {
                'method': 'Token bucket algorithm',
                'parameters': {
                    'initial_rate': '100 requests/minute',
                    'burst_capacity': '150 requests',
                    'refill_rate': '100 tokens/minute'
                },
                'adaptation': {
                    'on_429_response': 'Reduce rate by 50%',
                    'on_success_streak': 'Gradually increase rate by 10%',
                    'max_rate': 'Never exceed API limits',
                    'min_rate': 'Maintain minimum viable rate'
                },
                'benefits': [
                    'Maximize API utilization',
                    'Never hit rate limits',
                    'Automatic recovery'
                ]
            },
            'potential_improvement': '90-95% API quota utilization without bans',
            'priority': 'critical'
        })

        # Distributed rate limiting
        optimizations.append({
            'type': 'distributed_rate_limiting',
            'recommendation': 'Coordinate rate limits across multiple instances',
            'implementation': {
                'method': 'Redis-based distributed counter',
                'key_pattern': 'rate_limit:{service}:{timewindow}',
                'sliding_window': 'Use sorted sets for accurate sliding window',
                'coordination': 'All instances check/update shared counter',
                'fallback': 'Local rate limiting if Redis unavailable'
            },
            'potential_improvement': 'Prevent quota exhaustion in distributed setup',
            'priority': 'high'
        })

        # Backoff strategies
        optimizations.append({
            'type': 'intelligent_backoff',
            'recommendation': 'Implement multiple backoff strategies',
            'implementation': {
                'strategies': {
                    'exponential': 'For transient failures',
                    'linear': 'For gradual degradation',
                    'fibonacci': 'For unpredictable services'
                },
                'strategy_selection': {
                    'twitter_api': 'Exponential with 2^n seconds',
                    'news_rss': 'Linear with 30s increments',
                    'unreliable_sources': 'Fibonacci sequence'
                },
                'max_backoff': '600 seconds (10 minutes)'
            },
            'potential_improvement': '70-85% better service recovery',
            'priority': 'high'
        })

        return optimizations
