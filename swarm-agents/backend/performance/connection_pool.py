#!/usr/bin/env python3
"""
Connection Pool Management for High-Performance TGE Swarm
Provides Redis and Database connection pooling with health monitoring
"""

import asyncio
import logging
import time
import weakref
from typing import Dict, List, Any, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError
import aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
import psutil


@dataclass
class ConnectionMetrics:
    """Connection pool metrics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    connection_errors: int = 0
    avg_connection_time: float = 0.0
    peak_connections: int = 0
    pool_exhaustion_count: int = 0


class HealthChecker:
    """Health checking for connections"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.running = False
    
    async def check_redis_connection(self, connection) -> bool:
        """Check Redis connection health"""
        try:
            await connection.ping()
            return True
        except Exception:
            return False
    
    async def check_database_connection(self, connection) -> bool:
        """Check database connection health"""
        try:
            await connection.execute("SELECT 1")
            return True
        except Exception:
            return False


class RedisConnectionPool:
    """High-performance Redis connection pool with health monitoring"""
    
    def __init__(self, 
                 redis_urls: List[str],
                 min_connections: int = 5,
                 max_connections: int = 50,
                 connection_timeout: int = 10,
                 retry_on_timeout: bool = True,
                 health_check_interval: int = 30):
        
        self.redis_urls = redis_urls
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.retry_on_timeout = retry_on_timeout
        
        # Connection pools for each Redis instance
        self.pools: Dict[str, aioredis.ConnectionPool] = {}
        self.connections: Dict[str, List[redis.Redis]] = {}
        self.connection_metrics = ConnectionMetrics()
        
        # Load balancing
        self.current_pool_index = 0
        self.pool_weights: Dict[str, float] = {}
        
        # Health monitoring
        self.health_checker = HealthChecker(health_check_interval)
        self.unhealthy_pools: set = set()
        
        # Performance tracking
        self.connection_times: List[float] = []
        self.last_cleanup = time.time()
        
        self.logger = logging.getLogger("RedisConnectionPool")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup connection pool logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize connection pools"""
        try:
            for url in self.redis_urls:
                host, port = url.split(':')
                pool_key = f"{host}:{port}"
                
                # Create connection pool with optimized settings
                pool = aioredis.ConnectionPool(
                    host=host,
                    port=int(port),
                    min_size=self.min_connections,
                    max_size=self.max_connections,
                    retry_on_timeout=self.retry_on_timeout,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                
                self.pools[pool_key] = pool
                self.connections[pool_key] = []
                self.pool_weights[pool_key] = 1.0
                
                # Pre-warm the pool
                await self._prewarm_pool(pool_key)
                
                self.logger.info(f"Initialized Redis pool for {pool_key}")
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())
            asyncio.create_task(self._cleanup_loop())
            
            self.logger.info(f"Redis connection pool initialized with {len(self.pools)} pools")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connection pool: {e}")
            raise
    
    async def _prewarm_pool(self, pool_key: str):
        """Pre-warm connection pool"""
        try:
            pool = self.pools[pool_key]
            
            # Create minimum connections
            for _ in range(self.min_connections):
                connection = redis.Redis(connection_pool=pool)
                await connection.ping()  # Test connection
                self.connections[pool_key].append(connection)
                self.connection_metrics.total_connections += 1
                self.connection_metrics.idle_connections += 1
            
            self.logger.info(f"Pre-warmed pool {pool_key} with {self.min_connections} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to pre-warm pool {pool_key}: {e}")
    
    @asynccontextmanager
    async def get_connection(self, preferred_pool: str = None) -> AsyncContextManager[redis.Redis]:
        """Get Redis connection from pool with automatic return"""
        connection = None
        pool_key = None
        start_time = time.time()
        
        try:
            # Select pool using load balancing
            pool_key = await self._select_best_pool(preferred_pool)
            
            if pool_key in self.unhealthy_pools:
                raise ConnectionError(f"Pool {pool_key} is unhealthy")
            
            # Get connection from pool
            connection = await self._get_connection_from_pool(pool_key)
            
            # Update metrics
            connection_time = time.time() - start_time
            self.connection_times.append(connection_time)
            self.connection_metrics.active_connections += 1
            self.connection_metrics.idle_connections -= 1
            
            if self.connection_metrics.active_connections > self.connection_metrics.peak_connections:
                self.connection_metrics.peak_connections = self.connection_metrics.active_connections
            
            yield connection
            
        except Exception as e:
            self.connection_metrics.connection_errors += 1
            self.logger.error(f"Failed to get Redis connection: {e}")
            raise
        
        finally:
            # Return connection to pool
            if connection and pool_key:
                await self._return_connection_to_pool(connection, pool_key)
                self.connection_metrics.active_connections -= 1
                self.connection_metrics.idle_connections += 1
    
    async def _select_best_pool(self, preferred_pool: str = None) -> str:
        """Select best pool using weighted round-robin"""
        if preferred_pool and preferred_pool in self.pools and preferred_pool not in self.unhealthy_pools:
            return preferred_pool
        
        # Filter healthy pools
        healthy_pools = [key for key in self.pools.keys() if key not in self.unhealthy_pools]
        
        if not healthy_pools:
            raise ConnectionError("No healthy Redis pools available")
        
        # Weighted selection based on performance
        best_pool = None
        best_score = float('inf')
        
        for pool_key in healthy_pools:
            # Calculate score based on active connections and weight
            active_conns = len([c for c in self.connections[pool_key] if hasattr(c, '_in_use')])
            weight = self.pool_weights[pool_key]
            score = active_conns / weight
            
            if score < best_score:
                best_score = score
                best_pool = pool_key
        
        return best_pool or healthy_pools[0]
    
    async def _get_connection_from_pool(self, pool_key: str) -> redis.Redis:
        """Get connection from specific pool"""
        pool = self.pools[pool_key]
        
        try:
            # Try to get existing idle connection
            for connection in self.connections[pool_key]:
                if not hasattr(connection, '_in_use') or not connection._in_use:
                    connection._in_use = True
                    
                    # Test connection health
                    if await self.health_checker.check_redis_connection(connection):
                        return connection
                    else:
                        # Remove unhealthy connection
                        self.connections[pool_key].remove(connection)
                        self.connection_metrics.failed_connections += 1
            
            # Create new connection if pool not at max
            if len(self.connections[pool_key]) < self.max_connections:
                connection = redis.Redis(connection_pool=pool)
                await connection.ping()  # Test connection
                connection._in_use = True
                self.connections[pool_key].append(connection)
                self.connection_metrics.total_connections += 1
                return connection
            
            # Pool exhausted
            self.connection_metrics.pool_exhaustion_count += 1
            raise ConnectionError(f"Pool {pool_key} exhausted")
            
        except Exception as e:
            self.logger.error(f"Failed to get connection from pool {pool_key}: {e}")
            raise
    
    async def _return_connection_to_pool(self, connection: redis.Redis, pool_key: str):
        """Return connection to pool"""
        try:
            if hasattr(connection, '_in_use'):
                connection._in_use = False
        except Exception as e:
            self.logger.error(f"Error returning connection to pool {pool_key}: {e}")
    
    async def execute_command(self, command: str, *args, **kwargs) -> Any:
        """Execute Redis command with connection pooling"""
        async with self.get_connection() as connection:
            return await connection.execute_command(command, *args, **kwargs)
    
    async def pipeline(self, pool_key: str = None) -> AsyncContextManager:
        """Get Redis pipeline with connection pooling"""
        async with self.get_connection(pool_key) as connection:
            return connection.pipeline()
    
    async def _health_monitoring_loop(self):
        """Monitor pool health"""
        while True:
            try:
                await asyncio.sleep(self.health_checker.check_interval)
                
                for pool_key, pool in self.pools.items():
                    try:
                        # Test pool with a ping
                        test_connection = redis.Redis(connection_pool=pool)
                        await asyncio.wait_for(test_connection.ping(), timeout=5)
                        
                        # Mark as healthy
                        if pool_key in self.unhealthy_pools:
                            self.unhealthy_pools.remove(pool_key)
                            self.logger.info(f"Pool {pool_key} recovered")
                        
                        # Update weight based on performance
                        await self._update_pool_weight(pool_key)
                        
                    except Exception as e:
                        # Mark as unhealthy
                        self.unhealthy_pools.add(pool_key)
                        self.logger.warning(f"Pool {pool_key} health check failed: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
    
    async def _update_pool_weight(self, pool_key: str):
        """Update pool weight based on performance"""
        try:
            # Calculate average response time for this pool
            pool_connections = self.connections[pool_key]
            if pool_connections:
                # Simple weight calculation based on active connections
                active_count = len([c for c in pool_connections if hasattr(c, '_in_use') and c._in_use])
                max_conns = self.max_connections
                utilization = active_count / max_conns
                
                # Lower weight for higher utilization
                self.pool_weights[pool_key] = max(0.1, 1.0 - utilization)
        
        except Exception as e:
            self.logger.error(f"Error updating pool weight for {pool_key}: {e}")
    
    async def _cleanup_loop(self):
        """Cleanup idle connections periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = time.time()
                
                for pool_key in self.pools.keys():
                    connections_to_remove = []
                    
                    for connection in self.connections[pool_key]:
                        # Remove connections that have been idle too long
                        if (hasattr(connection, '_last_used') and 
                            current_time - connection._last_used > 600 and  # 10 minutes
                            len(self.connections[pool_key]) > self.min_connections):
                            
                            connections_to_remove.append(connection)
                    
                    # Remove idle connections
                    for connection in connections_to_remove:
                        try:
                            self.connections[pool_key].remove(connection)
                            self.connection_metrics.total_connections -= 1
                            self.connection_metrics.idle_connections -= 1
                        except Exception as e:
                            self.logger.error(f"Error removing idle connection: {e}")
                
                # Update average connection time
                if self.connection_times:
                    self.connection_metrics.avg_connection_time = sum(self.connection_times) / len(self.connection_times)
                    # Keep only recent measurements
                    self.connection_times = self.connection_times[-1000:]
                
                self.logger.debug(f"Cleanup completed. Active pools: {len(self.pools) - len(self.unhealthy_pools)}")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics"""
        return {
            'total_connections': self.connection_metrics.total_connections,
            'active_connections': self.connection_metrics.active_connections,
            'idle_connections': self.connection_metrics.idle_connections,
            'failed_connections': self.connection_metrics.failed_connections,
            'connection_errors': self.connection_metrics.connection_errors,
            'avg_connection_time': self.connection_metrics.avg_connection_time,
            'peak_connections': self.connection_metrics.peak_connections,
            'pool_exhaustion_count': self.connection_metrics.pool_exhaustion_count,
            'healthy_pools': len(self.pools) - len(self.unhealthy_pools),
            'total_pools': len(self.pools),
            'pool_weights': self.pool_weights.copy()
        }
    
    async def close(self):
        """Close all connections and pools"""
        for pool_key, connections in self.connections.items():
            for connection in connections:
                try:
                    await connection.close()
                except Exception:
                    pass
        
        for pool in self.pools.values():
            try:
                await pool.disconnect()
            except Exception:
                pass
        
        self.logger.info("Redis connection pool closed")


class DatabaseConnectionPool:
    """High-performance database connection pool"""
    
    def __init__(self,
                 database_url: str,
                 min_connections: int = 5,
                 max_connections: int = 20,
                 pool_timeout: int = 30,
                 pool_recycle: int = 3600,
                 echo: bool = False):
        
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        
        self.engine = None
        self.session_factory = None
        self.connection_metrics = ConnectionMetrics()
        
        self.logger = logging.getLogger("DatabaseConnectionPool")
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.min_connections,
                max_overflow=self.max_connections - self.min_connections,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # Health check connections
                echo=False,
                future=True
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            self.logger.info("Database connection pool initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncContextManager[AsyncSession]:
        """Get database session from pool"""
        start_time = time.time()
        session = None
        
        try:
            session = self.session_factory()
            self.connection_metrics.active_connections += 1
            
            yield session
            
            await session.commit()
            
        except Exception as e:
            if session:
                await session.rollback()
            self.connection_metrics.connection_errors += 1
            raise
        
        finally:
            if session:
                await session.close()
                self.connection_metrics.active_connections -= 1
                
                # Update metrics
                connection_time = time.time() - start_time
                self.connection_metrics.avg_connection_time = (
                    (self.connection_metrics.avg_connection_time + connection_time) / 2
                )
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager:
        """Get raw database connection from pool"""
        async with self.engine.begin() as connection:
            self.connection_metrics.active_connections += 1
            try:
                yield connection
            finally:
                self.connection_metrics.active_connections -= 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database pool metrics"""
        pool = self.engine.pool
        
        return {
            'active_connections': self.connection_metrics.active_connections,
            'pool_size': pool.size(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'checked_in': pool.checkedin(),
            'avg_connection_time': self.connection_metrics.avg_connection_time,
            'connection_errors': self.connection_metrics.connection_errors
        }
    
    async def close(self):
        """Close database connection pool"""
        if self.engine:
            await self.engine.dispose()
        self.logger.info("Database connection pool closed")


# Connection pool manager for coordinating multiple pools
class ConnectionPoolManager:
    """Manages multiple connection pools"""
    
    def __init__(self):
        self.redis_pools: Dict[str, RedisConnectionPool] = {}
        self.database_pools: Dict[str, DatabaseConnectionPool] = {}
        self.logger = logging.getLogger("ConnectionPoolManager")
    
    def add_redis_pool(self, name: str, pool: RedisConnectionPool):
        """Add Redis connection pool"""
        self.redis_pools[name] = pool
    
    def add_database_pool(self, name: str, pool: DatabaseConnectionPool):
        """Add database connection pool"""
        self.database_pools[name] = pool
    
    async def initialize_all(self):
        """Initialize all connection pools"""
        tasks = []
        
        for name, pool in self.redis_pools.items():
            tasks.append(pool.initialize())
        
        for name, pool in self.database_pools.items():
            tasks.append(pool.initialize())
        
        await asyncio.gather(*tasks)
        self.logger.info("All connection pools initialized")
    
    def get_redis_pool(self, name: str = 'default') -> RedisConnectionPool:
        """Get Redis connection pool by name"""
        return self.redis_pools.get(name)
    
    def get_database_pool(self, name: str = 'default') -> DatabaseConnectionPool:
        """Get database connection pool by name"""
        return self.database_pools.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics from all pools"""
        metrics = {
            'redis_pools': {},
            'database_pools': {}
        }
        
        for name, pool in self.redis_pools.items():
            metrics['redis_pools'][name] = pool.get_metrics()
        
        for name, pool in self.database_pools.items():
            metrics['database_pools'][name] = pool.get_metrics()
        
        return metrics
    
    async def close_all(self):
        """Close all connection pools"""
        tasks = []
        
        for pool in self.redis_pools.values():
            tasks.append(pool.close())
        
        for pool in self.database_pools.values():
            tasks.append(pool.close())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("All connection pools closed")