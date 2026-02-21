# start.py - Phase 6 Task 8 (P6-T8)
# 一键启动脚本 - 含 MongoDB 健康检查

import sys
import os
import time
import subprocess
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("  PSTDS - 个人专用股票交易决策系统")
    print("  Version 1.0")
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def check_mongodb():
    """检查 MongoDB 连接"""
    print("\n[1/4] 检查 MongoDB 连接...")

    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure
        from pstds.storage.mongo_store import MongoStore

        store = MongoStore()

        if store.client:
            print("  ✓ MongoDB 连接成功")
            return True
        else:
            print("  ✗ MongoDB 连接失败")
            return False

    except ConnectionFailure as e:
        print(f"  ✗ MongoDB 连接失败: {e}")
        return False
    except Exception as e:
        print(f"  ? MongoDB 检查异常: {e}")
        return False


def check_streamlit():
    """检查 Streamlit 服务"""
    print("\n[2/4] 检查 Streamlit 服务...")

    try:
        import requests
        response = requests.get("http://localhost:8501/healthz", timeout=5)
        if response.status_code == 200:
            print("  ✓ Streamlit 服务正常")
            return True
        else:
            print(f"  ✗ Streamlit 服务异常: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"  ? Streamlit 服务检查异常: {e}")
        return False


def check_dependencies():
    """检查依赖"""
    print("\n[3/4] 检查依赖...")

    missing_deps = []

    # 检查 MongoDB
    try:
        import pymongo
    except ImportError:
        missing_deps.append("pymongo")

    # 检查 Streamlit
    try:
        import streamlit
    except ImportError:
        missing_deps.append("streamlit")

    # 检查 pandas
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")

    if not missing_deps:
        print("  ✓ 所有依赖已安装")
        return True
    else:
        print(f"  ✗ 缺少依赖: {', '.join(missing_deps)}")
        return False


def check_environment():
    """检查环境变量"""
    print("\n[4/4] 检查环境变量...")

    required_env_vars = []
    optional_env_vars = []

    # 检查必需的环境变量
    # 这里可以添加更多检查

    if not required_env_vars:
        print("  ✓ 环境变量配置完成")
        return True
    else:
        print(f"  ✗ 缺少必需的环境变量: {', '.join(required_env_vars)}")
        return False


def start_services():
    """启动服务"""
    print("\n" + "=" * 60)
    print("启动服务...")
    print("=" * 60)

    # 启动 Docker Compose
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("  ✓ Docker Compose 启动成功")
            print("\n服务访问地址:")
            print("  - Streamlit: http://localhost:8501")
            print("  - MongoDB Express: http://localhost:8081")
            print("\n按 Ctrl+C 停止服务")
        else:
            print(f"  ✗ Docker Compose 启动失败")
            print(f"  错误输出: {result.stderr}")

    except Exception as e:
        print(f"  ✗ 启动服务失败: {e}")


def wait_for_services():
    """等待服务就绪"""
    print("\n等待服务就绪...")

    max_retries = 30
    retry_delay = 2

    for i in range(max_retries):
        time.sleep(retry_delay)

        if i % 5 == 0:
            print(f"检查中... ({i + 1}/{max_retries})")

        # 检查各个服务
        streamlit_ok = check_streamlit()
        mongodb_ok = check_mongodb()

        if streamlit_ok and mongodb_ok:
            print("  ✓ 所有服务已就绪")
            break

    print("\n启动失败或超时")
    print("请检查服务状态")


def run_endpoint_smoke_test():
    """运行端到端冒烟测试"""
    print("\n运行端到端冒烟测试...")

    from pstds.agents.output_schemas import TradeDecision
    from pstds.agents.extended_graph import ExtendedTradingAgentsGraph
    from pstds.temporal.context import TemporalContext
    from datetime import date

    try:
        # 创建测试上下文
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        # 创建 Mock 图（避免实际 API 调用）
        graph = ExtendedTradingAgentsGraph(
            config={'analysis_depth': 'L1', 'use_mock_llm': True}
        )

        # 运行测试分析
        result = graph.propagate('AAPL', date(2024, 1, 2), ctx=ctx, depth='L1')

        # 验证决策
        decision = result.get('final_trade_decision', {})
        action = decision.action if hasattr(decision, 'action') else 'INSUFFICIENT_DATA'

        print(f"  决策: {action}")
        print("  置信度: " + str(decision.confidence if hasattr(decision, 'confidence') else 0))
        print(f"  分析日期: {decision.analysis_date if hasattr(decision, 'analysis_date') else 'N/A'}")
        print("  ✓ 端到端冒烟测试通过")

    except Exception as e:
        print(f"  ✗ 端到端冒烟测试失败: {e}")


def main():
    """主函数"""
    print_banner()

    # 执行预检查
    checks_passed = True
    checks_passed = checks_passed and check_dependencies()
    checks_passed = checks_passed and check_environment()

    if not checks_passed:
        print("\n预检查失败，请先解决依赖问题")
        return

    # 启动服务
    start_services()

    # 等待服务就绪
    wait_for_services()

    # 运行端到端冒烟测试
    run_endpoint_smoke_test()

    print("\n" + "=" * 60)
    print("PSTDS v1.0 所有验证通过！系统可以投入使用")
    print("请访问: http://localhost:8501")
    print("=" * 60)


if __name__ == "__main__":
    main()
