#!/usr/bin/env python3
"""
Data Partitioning System for AI Brain

Implements time-based and source-based partitioning for better performance
and scalability of memory storage and retrieval.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json


class DataPartitioner:
    """Handles data partitioning for scalable memory management"""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or "/tmp/ai_brain_partitions")
        self.base_path.mkdir(exist_ok=True)

    def get_time_partition_key(self, timestamp: datetime = None) -> str:
        """Generate time-based partition key (YYYY-MM format)"""
        dt = timestamp or datetime.utcnow()
        return f"time_{dt.strftime('%Y-%m')}"

    def get_source_partition_key(self, source: str) -> str:
        """Generate source-based partition key"""
        return f"source_{source.lower().replace(' ', '_')}"

    def get_user_partition_key(self, user_id: str) -> str:
        """Generate user-based partition key for multi-tenancy"""
        return f"user_{user_id}"

    def get_partition_keys(self, memory_data: Dict) -> List[str]:
        """Generate all relevant partition keys for a memory entry"""
        keys = []

        # Time-based partitioning
        created_at = memory_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            keys.append(self.get_time_partition_key(created_at))

        # Source-based partitioning
        source = memory_data.get('source')
        if source:
            keys.append(self.get_source_partition_key(source))

        # User-based partitioning (if user_id in metadata)
        metadata = memory_data.get('metadata_json')
        if metadata:
            try:
                meta_dict = json.loads(metadata)
                user_id = meta_dict.get('user_id')
                if user_id:
                    keys.append(self.get_user_partition_key(user_id))
            except:
                pass

        return keys

    def should_create_partition(self, partition_key: str, current_size: int, max_size: int = 10000) -> bool:
        """Determine if a new partition should be created"""
        return current_size >= max_size

    def get_partition_stats(self) -> Dict[str, Dict]:
        """Get statistics for all partitions"""
        stats = {}
        for partition_dir in self.base_path.iterdir():
            if partition_dir.is_dir():
                partition_key = partition_dir.name
                file_count = len(list(partition_dir.glob("*.json")))
                total_size = sum(f.stat().st_size for f in partition_dir.glob("*.json"))

                stats[partition_key] = {
                    "file_count": file_count,
                    "total_size_mb": total_size / (1024 * 1024),
                    "avg_file_size_kb": (total_size / max(file_count, 1)) / 1024
                }

        return stats

    def cleanup_old_partitions(self, retention_days: int = 365) -> List[str]:
        """Clean up partitions older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        removed_partitions = []

        for partition_dir in self.base_path.iterdir():
            if partition_dir.is_dir() and partition_dir.name.startswith("time_"):
                try:
                    # Extract date from partition name (time_YYYY-MM)
                    date_str = partition_dir.name.replace("time_", "") + "-01"
                    partition_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if partition_date < cutoff_date:
                        import shutil
                        shutil.rmtree(partition_dir)
                        removed_partitions.append(partition_dir.name)
                except ValueError:
                    continue

        return removed_partitions


class PartitionedMemoryStore:
    """Memory store with partitioning support"""

    def __init__(self, partitioner: DataPartitioner = None):
        self.partitioner = partitioner or DataPartitioner()
        self.partition_cache = {}  # Cache for partition metadata

    def store_memory(self, memory_data: Dict, partition_keys: List[str] = None) -> str:
        """Store memory in appropriate partitions"""
        if not partition_keys:
            partition_keys = self.partitioner.get_partition_keys(memory_data)

        memory_id = memory_data.get('id', str(datetime.utcnow().timestamp()))

        # Store in each relevant partition
        for partition_key in partition_keys:
            partition_dir = self.partitioner.base_path / partition_key
            partition_dir.mkdir(exist_ok=True)

            memory_file = partition_dir / f"{memory_id}.json"
            with open(memory_file, 'w') as f:
                json.dump(memory_data, f, default=str)

        return memory_id

    def retrieve_from_partition(self, partition_key: str, memory_id: str) -> Optional[Dict]:
        """Retrieve specific memory from a partition"""
        partition_dir = self.partitioner.base_path / partition_key
        memory_file = partition_dir / f"{memory_id}.json"

        if memory_file.exists():
            with open(memory_file, 'r') as f:
                return json.load(f)
        return None

    def search_partition(self, partition_key: str, query: Dict) -> List[Dict]:
        """Search memories within a specific partition"""
        partition_dir = self.partitioner.base_path / partition_key
        if not partition_dir.exists():
            return []

        results = []
        for memory_file in partition_dir.glob("*.json"):
            try:
                with open(memory_file, 'r') as f:
                    memory_data = json.load(f)

                # Simple filtering based on query
                if self._matches_query(memory_data, query):
                    results.append(memory_data)
            except:
                continue

        return results

    def _matches_query(self, memory_data: Dict, query: Dict) -> bool:
        """Check if memory matches search query"""
        for key, value in query.items():
            if key not in memory_data:
                return False
            if memory_data[key] != value:
                return False
        return True

    def get_partition_info(self, partition_key: str) -> Dict:
        """Get information about a partition"""
        if partition_key in self.partition_cache:
            return self.partition_cache[partition_key]

        partition_dir = self.partitioner.base_path / partition_key
        if not partition_dir.exists():
            return {"exists": False}

        files = list(partition_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)

        info = {
            "exists": True,
            "file_count": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "last_modified": max(f.stat().st_mtime for f in files) if files else None
        }

        self.partition_cache[partition_key] = info
        return info


# Global instances
data_partitioner = DataPartitioner()
partitioned_store = PartitionedMemoryStore(data_partitioner)