"""日志保留和轮转策略

提供TimedRotatingFileHandler配置和自动清理功能
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


class RetentionPolicy:
    """日志保留策略"""
    
    def __init__(
        self,
        log_dir: Path,
        max_age_days: int = 30,
        max_size_mb: int = 1000,
        compress_after_days: int = 7,
    ) -> None:
        """
        
        Args:
            log_dir: 日志目录
            max_age_days: 最大保留天数
            max_size_mb: 最大总大小(MB)
            compress_after_days: 超过此天数后压缩
        """
        self.log_dir = Path(log_dir)
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self.compress_after_days = compress_after_days
    
    def cleanup(self) -> CleanupResult:
        """执行清理"""
        result = CleanupResult()
        
        if not self.log_dir.exists():
            return result
        
        now = datetime.now()
        total_size = 0
        
        for log_file in self.log_dir.glob("**/*.log"):
            try:
                stat = log_file.stat()
                file_age_days = (now - datetime.fromtimestamp(stat.st_mtime)).days
                file_size_mb = stat.st_size / (1024 * 1024)
                
                # 压缩旧日志
                if file_age_days > self.compress_after_days and not log_file.suffix == ".gz":
                    self._compress(log_file)
                    result.compressed += 1
                
                # 删除过期日志
                if file_age_days > self.max_age_days:
                    log_file.unlink()
                    result.deleted += 1
                    continue
                
                total_size += file_size_mb
                
            except Exception:
                continue
        
        # 如果总大小超过限制，删除最旧的
        if total_size > self.max_size_mb:
            result.size_cleaned = self._cleanup_by_size(total_size)
        
        return result
    
    def _compress(self, log_file: Path) -> None:
        """压缩日志文件"""
        gz_path = log_file.with_suffix(log_file.suffix + ".gz")
        with open(log_file, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        log_file.unlink()
    
    def _cleanup_by_size(self, current_size_mb: float) -> int:
        """按大小清理，返回删除的文件数"""
        deleted = 0
        target_size = self.max_size_mb * 0.8  # 清理到80%
        
        # 按修改时间排序，删除最旧的
        log_files = sorted(
            self.log_dir.glob("**/*.log*"),
            key=lambda p: p.stat().st_mtime
        )
        
        for log_file in log_files:
            if current_size_mb <= target_size:
                break
            try:
                size_mb = log_file.stat().st_size / (1024 * 1024)
                log_file.unlink()
                current_size_mb -= size_mb
                deleted += 1
            except Exception:
                continue
        
        return deleted


class CleanupResult:
    """清理结果"""
    
    def __init__(self) -> None:
        self.compressed: int = 0
        self.deleted: int = 0
        self.size_cleaned: int = 0
    
    def __repr__(self) -> str:
        return f"CleanupResult(compressed={self.compressed}, deleted={self.deleted}, size_cleaned={self.size_cleaned})"


def setup_rotation_handler(
    logger_name: str,
    log_dir: Path,
    filename: str,
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 30,
) -> logging.Handler:
    """设置轮转日志处理器
    
    Args:
        logger_name: logger名称
        log_dir: 日志目录
        filename: 日志文件名
        when: 轮转时机 (midnight, h, d, w0-w6)
        interval: 轮转间隔
        backup_count: 保留备份数
        
    Returns:
        配置好的Handler
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / filename
    
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding="utf-8",
    )
    
    return handler
