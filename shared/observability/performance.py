"""性能监控模块

提供日志写入性能基准和运行时监控
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable

_perf_stats: ContextVar[PerformanceStats | None] = ContextVar("perf_stats", default=None)


@dataclass
class PerformanceStats:
    """性能统计"""
    
    total_writes: int = 0
    total_bytes: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    errors: int = 0
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_writes == 0:
            return 0.0
        return self.total_latency_ms / self.total_writes
    
    @property
    def throughput_mbps(self) -> float:
        if self.total_latency_ms == 0:
            return 0.0
        return (self.total_bytes / 1024 / 1024) / (self.total_latency_ms / 1000)


def measure(func: Callable) -> Callable:
    """装饰器：测量函数执行时间"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            stats = _perf_stats.get()
            if stats:
                stats.total_latency_ms += elapsed
                stats.max_latency_ms = max(stats.max_latency_ms, elapsed)
    return wrapper


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self) -> None:
        self.stats = PerformanceStats()
        self._token = None
    
    def start(self) -> None:
        """开始监控"""
        self._token = _perf_stats.set(self.stats)
    
    def stop(self) -> None:
        """停止监控"""
        if self._token:
            _perf_stats.reset(self._token)
    
    def record_write(self, bytes_written: int) -> None:
        """记录写入"""
        self.stats.total_writes += 1
        self.stats.total_bytes += bytes_written
    
    def record_error(self) -> None:
        """记录错误"""
        self.stats.errors += 1
    
    def get_report(self) -> dict:
        """获取性能报告"""
        return {
            "total_writes": self.stats.total_writes,
            "total_bytes_mb": round(self.stats.total_bytes / 1024 / 1024, 2),
            "avg_latency_ms": round(self.stats.avg_latency_ms, 3),
            "max_latency_ms": round(self.stats.max_latency_ms, 3),
            "throughput_mbps": round(self.stats.throughput_mbps, 2),
            "error_rate": round(self.stats.errors / max(self.stats.total_writes, 1), 4),
        }


def run_benchmark(iterations: int = 10000) -> dict:
    """运行性能基准测试
    
    Args:
        iterations: 迭代次数
        
    Returns:
        基准测试结果
    """
    import json
    import logging
    import tempfile
    from pathlib import Path
    
    payload = {
        "timestamp": "2024-01-15T10:30:00Z",
        "level": "INFO",
        "logger": "benchmark",
        "message": "benchmark message",
        "request_id": "req_benchmark",
        "trace_id": "a" * 32,
        "extra": {"key": "value"},
    }
    
    results = {}
    
    # JSON序列化基准
    start = time.perf_counter()
    for _ in range(iterations):
        json.dumps(payload)
    elapsed = time.perf_counter() - start
    results["json_serialize_ops_per_sec"] = round(iterations / elapsed, 2)
    results["json_serialize_ms_per_op"] = round((elapsed / iterations) * 1000, 4)
    
    # 文件写入基准
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        log_path = f.name
    
    logger = logging.getLogger("benchmark")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    start = time.perf_counter()
    for _ in range(iterations):
        logger.info(json.dumps(payload))
    elapsed = time.perf_counter() - start
    
    import os
    file_size = os.path.getsize(log_path)
    os.unlink(log_path)
    
    results["log_write_ops_per_sec"] = round(iterations / elapsed, 2)
    results["log_write_mb_total"] = round(file_size / 1024 / 1024, 4)
    results["log_write_latency_ms_avg"] = round((elapsed / iterations) * 1000, 4)
    
    return results
