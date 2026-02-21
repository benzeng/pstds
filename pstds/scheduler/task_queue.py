# pstds/scheduler/task_queue.py
# 任务队列 - Phase 4 Task 3 (P4-T3)
# asyncio 令牌桶队列实现

from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueuedTask:
    """
    队列任务数据结构
    """
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 0  # 优先级，数字越小优先级越高
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TokenBucket:
    """
    令牌桶限流器

    用于控制任务执行速率，防止 API 调用过快。
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        初始化令牌桶

        Args:
            capacity: 桶容量（最大令牌数）
            refill_rate: 补充速率（令牌/秒）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, timeout: float = 60.0) -> bool:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数
            timeout: 超时时间（秒）

        Returns:
            是否成功获取令牌
        """
        async with self._lock:
            # 补充令牌
            now = datetime.utcnow()
            elapsed = (now - self.last_refill).total_seconds()
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            # 检查是否有足够令牌
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # 等待令牌补充
            wait_time = (tokens - self.tokens) / self.refill_rate
            if wait_time <= timeout:
                await asyncio.sleep(wait_time)
                self.tokens -= tokens
                return True

            return False

    def get_available_tokens(self) -> int:
        """
        获取可用令牌数

        Returns:
            可用令牌数
        """
        async with self._lock:
            # 补充令牌
            now = datetime.utcnow()
            elapsed = (now - self.last_refill).total_seconds()
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            return int(self.tokens)


class TaskQueue:
    """
    异步任务队列

    支持优先级队列和令牌桶限流。
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        token_capacity: int = 10,
        refill_rate: float = 0.1,
    ):
        """
        初始化任务队列

        Args:
            max_concurrent: 最大并发任务数
            token_capacity: 令牌桶容量
            refill_rate: 令牌补充速率（令牌/秒）
        """
        self.max_concurrent = max_concurrent
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running_tasks: Dict[str, QueuedTask] = {}
        self.completed_tasks: Dict[str, QueuedTask] = {}
        self.failed_tasks: Dict[str, QueuedTask] = {}
        self.token_bucket = TokenBucket(token_capacity, refill_rate)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def submit(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 0,
    ) -> str:
        """
        提交任务到队列

        Args:
            task_id: 任务 ID
            func: 任务执行函数
            args: 位置参数
            kwargs: 关键字参数
            priority: 优先级（数字越小优先级越高）

        Returns:
            任务 ID
        """
        if kwargs is None:
            kwargs = {}

        task = QueuedTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
        )

        # 使用优先级队列（priority, created_at, task）作为排序键
        await self.queue.put((priority, task.created_at, task))
        logger.info(f"任务已提交到队列: {task_id} (优先级: {priority})")

        # 启动 worker（如果尚未运行）
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())

        return task_id

    async def _worker(self):
        """
        队列工作协程
        """
        while self._running:
            try:
                # 从队列获取任务
                _, _, task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                # 检查是否已取消或完成
                if task.task_id in self.completed_tasks:
                    continue

                # 使用信号量控制并发
                async with self._semaphore:
                    # 等待令牌
                    if not await self.token_bucket.acquire(timeout=30.0):
                        logger.warning(f"任务 {task.task_id} 获取令牌超时，跳过")
                        self._mark_failed(task, "获取令牌超时")
                        continue

                    # 执行任务
                    task.status = "running"
                    task.started_at = datetime.utcnow()
                    self.running_tasks[task.task_id] = task
                    logger.info(f"开始执行任务: {task.task_id}")

                    try:
                        # 执行函数
                        if asyncio.iscoroutinefunction(task.func):
                            result = await task.func(*task.args, **task.kwargs)
                        else:
                            result = task.func(*task.args, **task.kwargs)

                        task.result = result
                        task.completed_at = datetime.utcnow()
                        task.status = "completed"
                        self.completed_tasks[task.task_id] = task
                        logger.info(f"任务完成: {task.task_id}")

                    except Exception as e:
                        task.error = str(e)
                        task.completed_at = datetime.utcnow()
                        task.status = "failed"
                        self.failed_tasks[task.task_id] = task
                        logger.error(f"任务失败: {task.task_id}, 错误: {e}")

                    finally:
                        if task.task_id in self.running_tasks:
                            del self.running_tasks[task.task_id]

            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"Worker 错误: {e}")

    def _mark_failed(self, task: QueuedTask, error: str):
        """
        标记任务失败
        """
        task.error = error
        task.completed_at = datetime.utcnow()
        task.status = "failed"
        self.failed_tasks[task.task_id] = task

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态字典，不存在则返回 None
        """
        # 检查运行中的任务
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            return self._task_to_dict(task)

        # 检查已完成的任务
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return self._task_to_dict(task)

        # 检查失败的任务
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            return self._task_to_dict(task)

        return None

    def _task_to_dict(self, task: QueuedTask) -> Dict[str, Any]:
        """将任务转换为字典"""
        return {
            "task_id": task.task_id,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error,
            "result": task.result if task.status == "completed" else None,
        }

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出任务

        Args:
            status: 状态过滤（可选）

        Returns:
            任务列表
        """
        tasks = []

        if status is None or status == "running":
            for task in self.running_tasks.values():
                tasks.append(self._task_to_dict(task))

        if status is None or status == "completed":
            for task in self.completed_tasks.values():
                tasks.append(self._task_to_dict(task))

        if status is None or status == "failed":
            for task in self.failed_tasks.values():
                tasks.append(self._task_to_dict(task))

        # 按创建时间排序
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        return tasks

    def get_queue_size(self) -> int:
        """
        获取队列大小（不包括运行中的任务）

        Returns:
            队列中的任务数
        """
        return self.queue.qsize()

    def get_available_tokens(self) -> int:
        """
        获取可用令牌数

        Returns:
            可用令牌数
        """
        return self.token_bucket.get_available_tokens()

    async def shutdown(self, wait: bool = True):
        """
        关闭任务队列

        Args:
            wait: 是否等待任务完成
        """
        self._running = False

        if wait:
            # 等待运行中的任务完成
            while self.running_tasks:
                await asyncio.sleep(0.1)

        # 取消 worker task
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("任务队列已关闭")


# 全局任务队列实例
_global_queue: Optional[TaskQueue] = None


def get_task_queue() -> Optional[TaskQueue]:
    """
    获取全局任务队列实例（单例）

    Returns:
        TaskQueue 实例
    """
    global _global_queue
    if _global_queue is None:
        _global_queue = TaskQueue()
    return _global_queue


def init_task_queue(
    max_concurrent: int = 4,
    token_capacity: int = 10,
    refill_rate: float = 0.1,
) -> TaskQueue:
    """
    初始化全局任务队列

    Args:
        max_concurrent: 最大并发任务数
        token_capacity: 令牌桶容量
        refill_rate: 令牌补充速率（令牌/秒）

    Returns:
        TaskQueue 实例
    """
    global _global_queue
    if _global_queue is None:
        _global_queue = TaskQueue(max_concurrent, token_capacity, refill_rate)
    return _global_queue
