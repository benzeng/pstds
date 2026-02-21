#!/usr/bin/env python3
# PSTDS 数据库连接测试

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, UTC
import yaml

def test_mongodb_import():
    """测试 MongoDB 驱动导入"""
    print("=== 测试 MongoDB 驱动导入 ===")

    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure
        print("[SUCCESS] pymongo 驱动导入成功")
        return True
    except ImportError as e:
        print(f"[ERROR] pymongo 驱动导入失败: {e}")
        print("建议安装: pip install pymongo")
        return False

def test_mongo_store_import():
    """测试 MongoStore 类导入"""
    print("\n=== 测试 MongoStore 类导入 ===")

    try:
        from pstds.storage.mongo_store import MongoStore
        print("[SUCCESS] MongoStore 类导入成功")
        return True
    except ImportError as e:
        print(f"[ERROR] MongoStore 类导入失败: {e}")
        return False

def test_configuration_loading():
    """测试配置文件加载"""
    print("\n=== 测试配置文件加载 ===")

    try:
        with open('config/default.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        mongodb_config = config.get('mongodb', {})
        connection_string = mongodb_config.get('connection_string')
        database_name = mongodb_config.get('database_name')

        print(f"[SUCCESS] 配置文件加载成功")
        print(f"  连接字符串: {connection_string}")
        print(f"  数据库名称: {database_name}")

        return connection_string and database_name
    except Exception as e:
        print(f"[ERROR] 配置文件加载失败: {e}")
        return False

def test_mongodb_connection():
    """测试 MongoDB 连接"""
    print("\n=== 测试 MongoDB 连接 ===")

    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure

        # 从配置文件读取连接信息
        with open('config/default.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        connection_string = config['mongodb']['connection_string']
        database_name = config['mongodb']['database_name']

        print(f"尝试连接: {connection_string}")
        print(f"目标数据库: {database_name}")

        # 创建连接
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

        # 测试连接
        try:
            client.admin.command('ping')
            print("[SUCCESS] MongoDB 连接成功")

            # 测试数据库访问
            db = client[database_name]
            print(f"[SUCCESS] 数据库 '{database_name}' 访问成功")

            # 列出集合
            collections = db.list_collection_names()
            print(f"[INFO] 数据库中的集合: {collections}")

            return True

        except ConnectionFailure as e:
            print(f"[ERROR] MongoDB 连接失败: {e}")
            print("可能原因:")
            print("  1. MongoDB 服务未启动")
            print("  2. 连接字符串配置错误")
            print("  3. 网络连接问题")
            return False

    except Exception as e:
        print(f"[ERROR] 连接测试异常: {e}")
        return False

def test_mongo_store_functionality():
    """测试 MongoStore 功能"""
    print("\n=== 测试 MongoStore 功能 ===")

    try:
        from pstds.storage.mongo_store import MongoStore

        # 初始化 MongoStore
        store = MongoStore()

        if store.client is None:
            print("[WARNING] MongoStore 初始化失败 (pymongo 未安装或连接失败)")
            return False

        print("[SUCCESS] MongoStore 初始化成功")
        print(f"  客户端: {store.client}")
        print(f"  数据库: {store.db}")
        print(f"  集合: {store.analyses_collection}")

        # 测试基本功能
        if store.analyses_collection is not None:
            # 检查集合是否存在
            collection_names = store.db.list_collection_names()
            if 'analyses' in collection_names:
                print("[SUCCESS] analyses 集合存在")
                # 获取文档数量
                count = store.analyses_collection.count_documents({})
                print(f"[INFO] analyses 集合中有 {count} 个文档")
            else:
                print("[INFO] analyses 集合不存在 (首次使用)")

        return True

    except Exception as e:
        print(f"[ERROR] MongoStore 功能测试失败: {e}")
        return False

def test_environment_variables():
    """测试环境变量配置"""
    print("\n=== 测试环境变量配置 ===")

    # 检查环境变量
    mongodb_env = os.getenv('MONGODB_CONNECTION_STRING')
    if mongodb_env:
        print(f"[INFO] 检测到环境变量 MONGODB_CONNECTION_STRING: {mongodb_env[:20]}...")
    else:
        print("[INFO] 未设置 MONGODB_CONNECTION_STRING 环境变量，使用默认配置")

    return True

def main():
    """主测试函数"""
    print("PSTDS 数据库连接测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now(UTC)}")
    print("=" * 60)

    results = {
        'mongodb_import': False,
        'mongo_store_import': False,
        'config_loading': False,
        'mongodb_connection': False,
        'mongo_store_functionality': False,
        'environment_variables': False
    }

    try:
        # 测试 MongoDB 驱动导入
        results['mongodb_import'] = test_mongodb_import()

        # 测试 MongoStore 类导入
        results['mongo_store_import'] = test_mongo_store_import()

        # 测试配置文件加载
        results['config_loading'] = test_configuration_loading()

        # 测试环境变量
        results['environment_variables'] = test_environment_variables()

        # 测试 MongoDB 连接
        results['mongodb_connection'] = test_mongodb_connection()

        # 测试 MongoStore 功能
        results['mongo_store_functionality'] = test_mongo_store_functionality()

        # 总结结果
        print("\n" + "=" * 60)
        print("数据库连接测试总结")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            display_name = test_name.replace('_', ' ').title()
            print(f"{status} {display_name}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] 所有数据库连接测试通过！")
            print("MongoDB 已准备好在 PSTDS 中使用")
        else:
            print("[WARNING] 部分测试失败")
            print("建议检查:")
            print("  1. 是否安装了 pymongo: pip install pymongo")
            print("  2. 是否启动了 MongoDB 服务")
            print("  3. 连接字符串配置是否正确")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] 测试执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()