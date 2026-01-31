#!/usr/bin/env python3
"""
Asynchronous Processing Pipeline for AI Brain

Implements async processing for embeddings, indexing, and memory consolidation
to improve throughput and resource utilization.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Callable
from queue import Queue, PriorityQueue
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(order=True)
class ProcessingTask:
    """Priority-based processing task"""
    priority: int
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)  # 'embedding', 'indexing', 'consolidation'
    data: Dict[str, Any] = field(compare=False)
    callback: Optional[Callable] = field(compare=False, default=None)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)


class AsyncProcessingPipeline:
    """Asynchronous processing pipeline for AI brain operations"""

    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        self.max_workers = max_workers
        self.queue_size = queue_size

        # Priority queue for tasks (lower number = higher priority)
        self.task_queue = PriorityQueue(maxsize=queue_size)

        # Thread pool for CPU-intensive tasks
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ai_brain_worker")

        # Processing state
        self.is_running = False
        self.workers = []
        self.processing_stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "avg_processing_time": 0.0,
            "queue_size": 0
        }

        # Task handlers
        self.task_handlers = {
            "embedding": self._process_embedding_task,
            "indexing": self._process_indexing_task,
            "consolidation": self._process_consolidation_task,
            "batch_embedding": self._process_batch_embedding_task
        }

    def start(self):
        """Start the async processing pipeline"""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"Starting async processing pipeline with {self.max_workers} workers")

        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"ai_brain_worker_{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

    def stop(self):
        """Stop the async processing pipeline"""
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("Async processing pipeline stopped")

    def submit_task(self, task: ProcessingTask) -> str:
        """Submit a task for async processing"""
        try:
            self.task_queue.put(task, timeout=1.0)
            self.processing_stats["queue_size"] = self.task_queue.qsize()
            return task.task_id
        except:
            logger.error(f"Failed to submit task {task.task_id}")
            raise

    def submit_embedding_task(self, texts: List[str], priority: int = 1,
                            callback: Callable = None) -> str:
        """Submit embedding generation task"""
        task = ProcessingTask(
            priority=priority,
            task_id=f"embed_{int(time.time() * 1000)}",
            task_type="embedding",
            data={"texts": texts},
            callback=callback
        )
        return self.submit_task(task)

    def submit_batch_embedding_task(self, text_batches: List[List[str]],
                                  priority: int = 1, callback: Callable = None) -> str:
        """Submit batch embedding generation task"""
        task = ProcessingTask(
            priority=priority,
            task_id=f"batch_embed_{int(time.time() * 1000)}",
            task_type="batch_embedding",
            data={"text_batches": text_batches},
            callback=callback
        )
        return self.submit_task(task)

    def submit_indexing_task(self, memories: List[Dict], priority: int = 2,
                           callback: Callable = None) -> str:
        """Submit vector indexing task"""
        task = ProcessingTask(
            priority=priority,
            task_id=f"index_{int(time.time() * 1000)}",
            task_type="indexing",
            data={"memories": memories},
            callback=callback
        )
        return self.submit_task(task)

    def submit_consolidation_task(self, partition_key: str, priority: int = 3,
                                callback: Callable = None) -> str:
        """Submit memory consolidation task"""
        task = ProcessingTask(
            priority=priority,
            task_id=f"consolidate_{int(time.time() * 1000)}",
            task_type="consolidation",
            data={"partition_key": partition_key},
            callback=callback
        )
        return self.submit_task(task)

    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        while self.is_running:
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=1.0)

                start_time = time.time()
                try:
                    # Process the task
                    self._process_task(task)
                    processing_time = time.time() - start_time

                    # Update stats
                    self.processing_stats["tasks_processed"] += 1
                    self._update_avg_processing_time(processing_time)

                except Exception as e:
                    logger.error(f"Task {task.task_id} failed: {e}")
                    self.processing_stats["tasks_failed"] += 1

                finally:
                    self.task_queue.task_done()
                    self.processing_stats["queue_size"] = self.task_queue.qsize()

            except:  # Queue timeout
                continue

    def _process_task(self, task: ProcessingTask):
        """Process a single task"""
        handler = self.task_handlers.get(task.task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task.task_type}")

        result = handler(task.data)

        # Call callback if provided
        if task.callback:
            try:
                task.callback(result)
            except Exception as e:
                logger.error(f"Callback failed for task {task.task_id}: {e}")

    def _process_embedding_task(self, data: Dict) -> List[List[float]]:
        """Process embedding generation task"""
        from .embeddings import embed_texts_batch

        texts = data["texts"]
        return embed_texts_batch(texts)

    def _process_batch_embedding_task(self, data: Dict) -> List[List[List[float]]]:
        """Process batch embedding generation task"""
        from .embeddings import embed_texts_batch

        text_batches = data["text_batches"]
        results = []

        for batch in text_batches:
            embeddings = embed_texts_batch(batch)
            results.append(embeddings)

        return results

    def _process_indexing_task(self, data: Dict) -> Dict[str, Any]:
        """Process vector indexing task"""
        from .hnsw_index import HNSWIndex

        memories = data["memories"]

        # This would integrate with the HNSW indexing system
        # For now, return success status
        return {
            "indexed_count": len(memories),
            "status": "completed"
        }

    def _process_consolidation_task(self, data: Dict) -> Dict[str, Any]:
        """Process memory consolidation task"""
        from .memory_consolidation import consolidate_old_memories
        from .db import get_session

        partition_key = data.get("partition_key")
        days_old = data.get("days_old", 30)

        # Use existing consolidation logic
        with get_session() as session:
            stats = consolidate_old_memories(
                session=session,
                days_old=days_old,
                batch_size=100,
                dry_run=False
            )

        return {
            "partition_key": partition_key,
            "consolidated_count": stats.get("consolidated", 0),
            "status": "completed"
        }

    def _update_avg_processing_time(self, processing_time: float):
        """Update rolling average processing time"""
        current_avg = self.processing_stats["avg_processing_time"]
        total_tasks = self.processing_stats["tasks_processed"]

        # Simple moving average
        self.processing_stats["avg_processing_time"] = (
            (current_avg * (total_tasks - 1)) + processing_time
        ) / total_tasks

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.processing_stats,
            "active_workers": len(self.workers),
            "is_running": self.is_running,
            "queue_size": self.task_queue.qsize()
        }


class ResourceManager:
    """Manages system resources for optimal performance"""

    def __init__(self, max_memory_mb: int = 1024, max_cpu_percent: int = 80):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent

        self.current_stats = {
            "memory_usage_mb": 0,
            "cpu_usage_percent": 0,
            "active_tasks": 0
        }

    def get_optimal_batch_size(self, base_batch_size: int = 32) -> int:
        """Determine optimal batch size based on current resource usage"""
        memory_usage = self.current_stats["memory_usage_mb"]
        cpu_usage = self.current_stats["cpu_usage_percent"]

        # Scale batch size based on available resources
        memory_factor = min(1.0, (self.max_memory_mb - memory_usage) / self.max_memory_mb)
        cpu_factor = min(1.0, (self.max_cpu_percent - cpu_usage) / self.max_cpu_percent)

        resource_factor = min(memory_factor, cpu_factor)

        # Adjust batch size (minimum 1, maximum base_batch_size * 2)
        optimal_size = max(1, int(base_batch_size * resource_factor))
        return min(optimal_size, base_batch_size * 2)

    def should_throttle(self) -> bool:
        """Check if processing should be throttled"""
        return (
            self.current_stats["memory_usage_mb"] > self.max_memory_mb * 0.9 or
            self.current_stats["cpu_usage_percent"] > self.max_cpu_percent
        )

    def update_stats(self, memory_mb: float = None, cpu_percent: float = None,
                    active_tasks: int = None):
        """Update current resource statistics"""
        if memory_mb is not None:
            self.current_stats["memory_usage_mb"] = memory_mb
        if cpu_percent is not None:
            self.current_stats["cpu_usage_percent"] = cpu_percent
        if active_tasks is not None:
            self.current_stats["active_tasks"] = active_tasks


# Global instances
async_pipeline = AsyncProcessingPipeline()
resource_manager = ResourceManager()