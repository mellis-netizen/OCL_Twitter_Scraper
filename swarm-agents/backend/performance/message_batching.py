#!/usr/bin/env python3
"""
Message Batching and Bulk Operations for High-Performance TGE Swarm
Optimizes WebSocket broadcasting and message processing through intelligent batching
"""

import asyncio
import logging
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import weakref


class BatchType(Enum):
    """Types of batching strategies"""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    ADAPTIVE = "adaptive"
    PRIORITY_BASED = "priority_based"


@dataclass
class BatchMetrics:
    """Batch processing metrics"""
    total_batches: int = 0
    total_messages: int = 0
    avg_batch_size: float = 0.0
    avg_processing_time: float = 0.0
    compression_ratio: float = 0.0
    throughput_per_second: float = 0.0
    memory_saved_bytes: int = 0


@dataclass
class BatchedMessage:
    """Batched message container"""
    id: str
    timestamp: datetime
    batch_type: str
    message_count: int
    compressed_size: int
    original_size: int
    messages: List[Dict[str, Any]]


class MessageBatcher:
    """Intelligent message batching system"""
    
    def __init__(self,
                 max_batch_size: int = 100,
                 max_batch_delay: float = 0.5,
                 compression_threshold: int = 1024,
                 adaptive_sizing: bool = True):
        
        self.max_batch_size = max_batch_size
        self.max_batch_delay = max_batch_delay
        self.compression_threshold = compression_threshold
        self.adaptive_sizing = adaptive_sizing
        
        # Batching queues by type/priority
        self.batches: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.batch_timers: Dict[str, float] = {}
        self.batch_sizes: Dict[str, int] = defaultdict(int)
        
        # Processing callbacks
        self.processors: Dict[str, Callable] = {}
        
        # Adaptive parameters
        self.processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.optimal_batch_sizes: Dict[str, int] = defaultdict(lambda: max_batch_size)
        
        # Metrics
        self.metrics = BatchMetrics()
        
        # Background tasks
        self.running = False
        self.flush_task = None
        
        self.logger = logging.getLogger("MessageBatcher")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup message batcher logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize message batcher"""
        self.running = True
        self.flush_task = asyncio.create_task(self._batch_flush_loop())
        self.logger.info("Message batcher initialized")
    
    def register_processor(self, batch_type: str, processor: Callable):
        """Register batch processor for specific type"""
        self.processors[batch_type] = processor
        self.logger.info(f"Registered processor for batch type: {batch_type}")
    
    async def add_message(self, message: Dict[str, Any], batch_type: str = "default"):
        """Add message to batch"""
        try:
            current_time = time.time()
            
            # Add message to batch
            self.batches[batch_type].append(message)
            self.batch_sizes[batch_type] += self._estimate_message_size(message)
            
            # Set timer for first message in batch
            if batch_type not in self.batch_timers:
                self.batch_timers[batch_type] = current_time
            
            # Check if batch should be flushed immediately
            should_flush = await self._should_flush_batch(batch_type)
            
            if should_flush:
                await self._flush_batch(batch_type)
            
        except Exception as e:
            self.logger.error(f"Error adding message to batch {batch_type}: {e}")
    
    async def _should_flush_batch(self, batch_type: str) -> bool:
        """Determine if batch should be flushed"""
        batch = self.batches[batch_type]
        
        if not batch:
            return False
        
        current_time = time.time()
        batch_age = current_time - self.batch_timers.get(batch_type, current_time)
        
        # Size-based flushing
        if len(batch) >= self.optimal_batch_sizes[batch_type]:
            return True
        
        # Time-based flushing
        if batch_age >= self.max_batch_delay:
            return True
        
        # Memory-based flushing
        if self.batch_sizes[batch_type] >= self.compression_threshold:
            return True
        
        # Priority-based flushing (for critical messages)
        if any(msg.get('priority') == 'critical' for msg in batch):
            return True
        
        return False
    
    async def _flush_batch(self, batch_type: str):
        """Flush batch and process messages"""
        if not self.batches[batch_type]:
            return
        
        start_time = time.time()
        
        try:
            # Get batch messages
            messages = self.batches[batch_type].copy()
            self.batches[batch_type].clear()
            
            # Reset batch metadata
            original_size = self.batch_sizes[batch_type]
            self.batch_sizes[batch_type] = 0
            if batch_type in self.batch_timers:
                del self.batch_timers[batch_type]
            
            # Create batched message
            batched_message = await self._create_batched_message(messages, batch_type, original_size)
            
            # Process batch
            if batch_type in self.processors:
                processor = self.processors[batch_type]
                await processor(batched_message)
            else:
                self.logger.warning(f"No processor registered for batch type: {batch_type}")
            
            # Update metrics
            processing_time = time.time() - start_time
            await self._update_metrics(len(messages), processing_time, original_size, batched_message.compressed_size)
            
            # Update adaptive parameters
            if self.adaptive_sizing:
                await self._update_adaptive_parameters(batch_type, len(messages), processing_time)
            
            self.logger.debug(f"Flushed batch {batch_type}: {len(messages)} messages in {processing_time:.3f}s")
            
        except Exception as e:
            self.logger.error(f"Error flushing batch {batch_type}: {e}")
    
    async def _create_batched_message(self, messages: List[Dict[str, Any]], 
                                    batch_type: str, original_size: int) -> BatchedMessage:
        """Create batched message with compression"""
        try:
            # Serialize messages
            serialized = json.dumps(messages, default=str)
            
            # Apply compression if beneficial
            compressed_data = serialized
            compressed_size = len(serialized.encode('utf-8'))
            
            if len(serialized) > self.compression_threshold:
                try:
                    import gzip
                    compressed_bytes = gzip.compress(serialized.encode('utf-8'))
                    compressed_size = len(compressed_bytes)
                    
                    # Only use compression if it saves significant space
                    if compressed_size < len(serialized.encode('utf-8')) * 0.8:
                        compressed_data = compressed_bytes
                except ImportError:
                    pass  # Compression not available
            
            return BatchedMessage(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                batch_type=batch_type,
                message_count=len(messages),
                compressed_size=compressed_size,
                original_size=original_size,
                messages=messages
            )
            
        except Exception as e:
            self.logger.error(f"Error creating batched message: {e}")
            raise
    
    async def _update_metrics(self, message_count: int, processing_time: float, 
                            original_size: int, compressed_size: int):
        """Update batching metrics"""
        self.metrics.total_batches += 1
        self.metrics.total_messages += message_count
        
        # Update averages
        self.metrics.avg_batch_size = (
            (self.metrics.avg_batch_size * (self.metrics.total_batches - 1) + message_count) 
            / self.metrics.total_batches
        )
        
        self.metrics.avg_processing_time = (
            (self.metrics.avg_processing_time * (self.metrics.total_batches - 1) + processing_time)
            / self.metrics.total_batches
        )
        
        # Update compression metrics
        if original_size > 0:
            compression_ratio = 1.0 - (compressed_size / original_size)
            self.metrics.compression_ratio = (
                (self.metrics.compression_ratio * (self.metrics.total_batches - 1) + compression_ratio)
                / self.metrics.total_batches
            )
            self.metrics.memory_saved_bytes += original_size - compressed_size
        
        # Update throughput
        if processing_time > 0:
            self.metrics.throughput_per_second = message_count / processing_time
    
    async def _update_adaptive_parameters(self, batch_type: str, batch_size: int, processing_time: float):
        """Update adaptive batching parameters"""
        try:
            # Record processing time
            self.processing_times[batch_type].append(processing_time)
            
            # Calculate optimal batch size based on processing efficiency
            if len(self.processing_times[batch_type]) >= 10:
                times = list(self.processing_times[batch_type])
                avg_time = sum(times) / len(times)
                
                # Find optimal batch size (balance between throughput and latency)
                if avg_time < 0.1:  # Very fast processing
                    self.optimal_batch_sizes[batch_type] = min(self.max_batch_size, 
                                                             self.optimal_batch_sizes[batch_type] + 10)
                elif avg_time > 1.0:  # Slow processing
                    self.optimal_batch_sizes[batch_type] = max(10, 
                                                             self.optimal_batch_sizes[batch_type] - 10)
                
                self.logger.debug(f"Updated optimal batch size for {batch_type}: {self.optimal_batch_sizes[batch_type]}")
        
        except Exception as e:
            self.logger.error(f"Error updating adaptive parameters: {e}")
    
    async def _batch_flush_loop(self):
        """Background loop to flush batches based on time"""
        while self.running:
            try:
                current_time = time.time()
                
                # Check all batches for time-based flushing
                batches_to_flush = []
                for batch_type, batch_time in self.batch_timers.items():
                    if current_time - batch_time >= self.max_batch_delay:
                        batches_to_flush.append(batch_type)
                
                # Flush expired batches
                for batch_type in batches_to_flush:
                    await self._flush_batch(batch_type)
                
                # Sleep for a short interval
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in batch flush loop: {e}")
                await asyncio.sleep(1)
    
    def _estimate_message_size(self, message: Dict[str, Any]) -> int:
        """Estimate message size in bytes"""
        try:
            return len(json.dumps(message, default=str).encode('utf-8'))
        except Exception:
            return 512  # Default estimate
    
    async def flush_all_batches(self):
        """Flush all pending batches"""
        for batch_type in list(self.batches.keys()):
            await self._flush_batch(batch_type)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get batching metrics"""
        return {
            'total_batches': self.metrics.total_batches,
            'total_messages': self.metrics.total_messages,
            'avg_batch_size': self.metrics.avg_batch_size,
            'avg_processing_time': self.metrics.avg_processing_time,
            'compression_ratio': self.metrics.compression_ratio,
            'throughput_per_second': self.metrics.throughput_per_second,
            'memory_saved_bytes': self.metrics.memory_saved_bytes,
            'pending_batches': {k: len(v) for k, v in self.batches.items()},
            'optimal_batch_sizes': dict(self.optimal_batch_sizes)
        }
    
    async def shutdown(self):
        """Shutdown message batcher"""
        self.running = False
        
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush all pending batches
        await self.flush_all_batches()
        
        self.logger.info("Message batcher shutdown complete")


class BatchProcessor:
    """High-performance batch processor with parallel execution"""
    
    def __init__(self, max_workers: int = 5, queue_size: int = 1000):
        self.max_workers = max_workers
        self.queue_size = queue_size
        
        # Processing queue and workers
        self.processing_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Metrics
        self.processed_batches = 0
        self.processing_errors = 0
        self.total_processing_time = 0.0
        
        self.logger = logging.getLogger("BatchProcessor")
    
    async def initialize(self):
        """Initialize batch processor"""
        self.running = True
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.workers.append(worker)
        
        self.logger.info(f"Batch processor initialized with {self.max_workers} workers")
    
    async def process_batch(self, batch: BatchedMessage, processor_func: Callable):
        """Submit batch for processing"""
        try:
            await self.processing_queue.put((batch, processor_func))
        except asyncio.QueueFull:
            self.logger.warning("Processing queue full, dropping batch")
            raise
    
    async def _worker_loop(self, worker_id: str):
        """Worker loop for processing batches"""
        while self.running:
            try:
                # Get batch from queue
                batch, processor_func = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )
                
                # Process batch
                start_time = time.time()
                await processor_func(batch)
                processing_time = time.time() - start_time
                
                # Update metrics
                self.processed_batches += 1
                self.total_processing_time += processing_time
                
                self.logger.debug(f"{worker_id} processed batch {batch.id} in {processing_time:.3f}s")
                
            except asyncio.TimeoutError:
                continue  # No work available
            except Exception as e:
                self.processing_errors += 1
                self.logger.error(f"{worker_id} error processing batch: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics"""
        avg_processing_time = (
            self.total_processing_time / self.processed_batches 
            if self.processed_batches > 0 else 0.0
        )
        
        return {
            'processed_batches': self.processed_batches,
            'processing_errors': self.processing_errors,
            'avg_processing_time': avg_processing_time,
            'queue_size': self.processing_queue.qsize(),
            'active_workers': len(self.workers)
        }
    
    async def shutdown(self):
        """Shutdown batch processor"""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.logger.info("Batch processor shutdown complete")


# Specialized batchers for different use cases
class WebSocketMessageBatcher(MessageBatcher):
    """Specialized batcher for WebSocket messages"""
    
    def __init__(self, **kwargs):
        super().__init__(
            max_batch_size=50,  # Smaller batches for real-time updates
            max_batch_delay=0.2,  # Faster flush for low latency
            **kwargs
        )
    
    async def add_websocket_update(self, update_type: str, data: Dict[str, Any], 
                                 target_clients: List[str] = None):
        """Add WebSocket update to batch"""
        message = {
            'type': 'batch_update',
            'update_type': update_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'target_clients': target_clients
        }
        
        # Use update type as batch type for better organization
        await self.add_message(message, f"websocket_{update_type}")


class DatabaseBulkProcessor(BatchProcessor):
    """Specialized processor for database bulk operations"""
    
    def __init__(self, **kwargs):
        super().__init__(max_workers=3, **kwargs)  # Fewer workers for DB
    
    async def bulk_insert(self, table_name: str, records: List[Dict[str, Any]], 
                         session_factory: Callable):
        """Perform bulk insert operation"""
        try:
            async with session_factory() as session:
                # Use SQLAlchemy bulk operations
                from sqlalchemy import text
                
                if records:
                    # Build bulk insert query
                    columns = list(records[0].keys())
                    placeholders = ', '.join([f':{col}' for col in columns])
                    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    await session.execute(text(query), records)
                    await session.commit()
                    
                    self.logger.info(f"Bulk inserted {len(records)} records into {table_name}")
        
        except Exception as e:
            self.logger.error(f"Bulk insert failed: {e}")
            raise
    
    async def bulk_update(self, table_name: str, updates: List[Dict[str, Any]], 
                         session_factory: Callable):
        """Perform bulk update operation"""
        try:
            async with session_factory() as session:
                # Group updates by update pattern
                update_groups = defaultdict(list)
                
                for update in updates:
                    # Create update pattern (columns being updated)
                    update_cols = tuple(sorted(k for k in update.keys() if k != 'id'))
                    update_groups[update_cols].append(update)
                
                # Execute bulk updates for each pattern
                for columns, records in update_groups.items():
                    if records:
                        set_clause = ', '.join([f'{col} = :{col}' for col in columns])
                        query = f"UPDATE {table_name} SET {set_clause} WHERE id = :id"
                        
                        await session.execute(text(query), records)
                
                await session.commit()
                self.logger.info(f"Bulk updated {len(updates)} records in {table_name}")
        
        except Exception as e:
            self.logger.error(f"Bulk update failed: {e}")
            raise