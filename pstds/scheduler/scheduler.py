# pstds/scheduler/scheduler.py
# 任务调度器 - Phase 4 Task 3 (P4-T3)
# APScheduler 封装，支持定时任务和调度管理

from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, time
from dataclasses import dataclass
import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    CronTrigger = None
    IntervalTrigger = None
    DateTrigger = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """
    定时任务数据结构
    """
    task_id: str
    name: str
    func: Callable
    trigger_type: str  # "cron", "interval", "date"
    trigger_args: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    error_count: int = 0


class TaskScheduler:
    """
    任务调度器

    封装 APScheduler，支持：
    1. Cron 表达式定时任务
    2. 固定间隔任务
    3. 一次性定时任务
    4. 任务状态管理
    """

    def __init__(self, max_workers: int = 4):
        """
        初始化任务调度器

        Args:
            max_workers: 最大工作线程数
        """
        if not APSCHEDULER_AVAILABLE:
            logger.error("APScheduler 未安装，任务调度功能不可用。请运行: pip install apscheduler")
            self.scheduler = None
            return

        # 创建后台调度器
        self.scheduler = BackgroundScheduler(
            jobstores={
                'default': MemoryJobStore(),
            },
            executors={
                'default': ThreadPoolExecutor(max_workers=max_workers),
            },
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1,  # 每个任务最多一个实例
                'misfire_grace_time': 300,  # 错过任务的宽容时间（秒）
            }
        )

        # 任务注册表
        self.tasks: Dict[str, ScheduledTask] = {}

        # 启动调度器
        self.scheduler.start()
        logger.info("任务调度器已启动")

    def add_cron_job(
        self,
        task_id: str,
        func: Callable,
        name: str,
        cron_expr: str,
        **kwargs,
    ) -> bool:
        """
        添加 Cron 定时任务

        Args:
            task_id: 任务唯一标识
            func: 任务执行函数
            name: 任务名称
            cron_expr: Cron 表达式（如 "0 9 * * MON-FRI" 表示工作日早上9点）
            **kwargs: 传递给执行函数的额外参数

        Returns:
            是否添加成功
        """
        if self.scheduler is None:
            return False

        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=CronTrigger.from_crontab(cron_expr),
                id=task_id,
                name=name,
                replace_existing=True,
                **kwargs
            )

            # 记录任务
            self.tasks[task_id] = ScheduledTask(
                task_id=task_id,
                name=name,
                func=func,
                trigger_type="cron",
                trigger_args={"cron": cron_expr},
                enabled=True,
                next_run=job.next_run_time,
            )

            logger.info(f"已添加 Cron 任务: {name} ({cron_expr})")
            return True

        except Exception as e:
            logger.error(f"添加 Cron 任务失败: {e}")
            return False

    def add_interval_job(
        self,
        task_id: str,
        func: Callable,
        name: str,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        days: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """
        添加固定间隔任务

        Args:
            task_id: 任务唯一标识
            func: 任务执行函数
            name: 任务名称
            minutes: 间隔分钟数
            hours: 间隔小时数
            days: 间隔天数
            **kwargs: 传递给执行函数的额外参数

        Returns:
            是否添加成功
        """
        if self.scheduler is None:
            return False

        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(
                    minutes=minutes,
                    hours=hours,
                    days=days,
                ),
                id=task_id,
                name=name,
                replace_existing=True,
                **kwargs
            )

            # 记录任务
            self.tasks[task_id] = ScheduledTask(
                task_id=task_id,
                name=name,
                func=func,
                trigger_type="interval",
                trigger_args={"minutes": minutes, "hours": hours, "days": days},
                enabled=True,
                next_run=job.next_run_time,
            )

            logger.info(f"已添加间隔任务: {name}")
            return True

        except Exception as e:
            logger.error(f"添加间隔任务失败: {e}")
            return False

    def add_date_job(
        self,
        task_id: str,
        func: Callable,
        name: str,
        run_date: datetime,
        **kwargs,
    ) -> bool:
        """
        添加一次性定时任务

        Args:
            task_id: 任务唯一标识
            func: 任务执行函数
            name: 任务名称
            run_date: 执行日期时间
            **kwargs: 传递给执行函数的额外参数

        Returns:
            是否添加成功
        """
        if self.scheduler is None:
            return False

        try:
            job = self.scheduler.add_job(
                func=func,
                trigger=DateTrigger(run_date=run_date),
                id=task_id,
                name=name,
                replace_existing=True,
                **kwargs
            )

            # 记录任务
            self.tasks[task_id] = ScheduledTask(
                task_id=task_id,
                name=name,
                func=func,
                trigger_type="date",
                trigger_args={"run_date": run_date.isoformat()},
                enabled=True,
                next_run=run_date,
            )

            logger.info(f"已添加一次性任务: {name} ({run_date})")
            return True

        except Exception as e:
            logger.error(f"添加一次性任务失败: {e}")
            return False

    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务

        Args:
            task_id: 任务 ID

        Returns:
            是否暂停成功
        """
        if self.scheduler is None:
            return False

        try:
            job = self.scheduler.get_job(task_id)
            if job:
                job.pause()
                if task_id in self.tasks:
                    self.tasks[task_id].enabled = False
                logger.info(f"已暂停任务: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"暂停任务失败: {e}")
            return False

    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务

        Args:
            task_id: 任务 ID

        Returns:
            是否恢复成功
        """
        if self.scheduler is None:
            return False

        try:
            job = self.scheduler.get_job(task_id)
            if job:
                job.resume()
                if task_id in self.tasks:
                    self.tasks[task_id].enabled = True
                logger.info(f"已恢复任务: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """
        移除任务

        Args:
            task_id: 任务 ID

        Returns:
            是否移除成功
        """
        if self.scheduler is None:
            return False

        try:
            self.scheduler.remove_job(task_id)
            if task_id in self.tasks:
                del self.tasks[task_id]
            logger.info(f"已移除任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"移除任务失败: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态字典，不存在则返回 None
        """
        if self.scheduler is None:
            return None

        job = self.scheduler.get_job(task_id)
        if job is None:
            return None

        return {
            "task_id": task_id,
            "name": job.name,
            "enabled": not job.next_run_time is None,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        }

    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        列出所有任务

        Returns:
            任务列表
        """
        tasks = []
        for job in self.scheduler.get_jobs():
            tasks.append({
                "task_id": job.id,
                "name": job.name,
                "enabled": not job.next_run_time is None,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return tasks

    def shutdown(self, wait: bool = True):
        """
        关闭调度器

        Args:
            wait: 是否等待任务完成
        """
        if self.scheduler:
            self.scheduler.shutdown(wait=wait)
            logger.info("任务调度器已关闭")


# 全局调度器实例
_global_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> Optional[TaskScheduler]:
    """
    获取全局调度器实例（单例）

    Returns:
        TaskScheduler 实例
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler()
    return _global_scheduler


def init_scheduler(max_workers: int = 4) -> TaskScheduler:
    """
    初始化全局调度器

    Args:
        max_workers: 最大工作线程数

    Returns:
        TaskScheduler 实例
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler(max_workers=max_workers)
    return _global_scheduler
