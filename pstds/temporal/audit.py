# pstds/temporal/audit.py
# 审计日志模块 - 记录时间隔离违规行为

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json


@dataclass
class AuditRecord:
    """审计记录数据结构"""

    timestamp: datetime  # 记录时间

    session_id: str  # 会话 ID

    analysis_date: datetime  # 分析基准日期

    data_source: str  # 数据源名称

    data_timestamp: datetime  # 数据时间戳

    is_compliant: bool  # 是否合规

    violation_detail: str  # 违规详情（过滤数量、违规原因等）

    caller_module: str  # 调用方模块名称


class AuditLogger:
    """
    审计日志记录器

    将所有时间隔离相关操作以 JSONL 格式追加写入日志文件。
    """

    def __init__(self, log_path: str = "./data/logs/temporal_audit.jsonl"):
        """
        初始化审计日志记录器

        Args:
            log_path: 日志文件路径
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: AuditRecord) -> None:
        """
        记录审计条目

        Args:
            record: 审计记录对象
        """
        record_dict = {
            "timestamp": record.timestamp.isoformat(),
            "session_id": record.session_id,
            "analysis_date": record.analysis_date.isoformat(),
            "data_source": record.data_source,
            "data_timestamp": record.data_timestamp.isoformat(),
            "is_compliant": record.is_compliant,
            "violation_detail": record.violation_detail,
            "caller_module": record.caller_module,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_dict, ensure_ascii=False) + "\n")

    def get_violation_count(self, session_id: str) -> int:
        """
        返回指定会话的违规记录数量

        Args:
            session_id: 会话 ID

        Returns:
            违规记录数量
        """
        if not self.log_path.exists():
            return 0

        count = 0
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("session_id") == session_id and not record.get("is_compliant", True):
                        count += 1
                except json.JSONDecodeError:
                    continue

        return count

    def get_session_records(self, session_id: str) -> List[Dict]:
        """
        获取指定会话的所有审计记录

        Args:
            session_id: 会话 ID

        Returns:
            审计记录列表
        """
        records = []
        if not self.log_path.exists():
            return records

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("session_id") == session_id:
                        records.append(record)
                except json.JSONDecodeError:
                    continue

        return records
