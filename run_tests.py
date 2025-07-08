#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本

提供便捷的测试运行命令和选项
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list, cwd: str = None) -> int:
    """
    运行命令并返回退
    """
    print(f"运行命令: {' '.join(cmd)}")
    if cwd:
        print(f"工作目录: {cwd}")
    
    try:
        result = subprocess.run(cmd, cwd=cwd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return 1


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description="运行项目测试")
    
    # 测试类型选项
    parser.add_argument(
        "-t", "--type",
        choices=["unit", "integration", "api", "all"],
        default="all",
        help="测试类型 (默认: all)"
    )
    
    # 测试文件或目录
    parser.add_argument(
        "-f", "--file",
        help="指定测试文件或目录"
    )
    
    # 详细输出
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )
    
    # 覆盖率报告
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="生成覆盖率报告"
    )
    
    # 并行运行
    parser.add_argument(
        "-n", "--numprocesses",
        type=int,
        help="并行进程数"
    )
    
    # 失败时停止
    parser.add_argument(
        "-x", "--exitfirst",
        action="store_true",
        help="第一个失败时停止"
    )
    
    # 只运行失败的测试
    parser.add_argument(
        "--lf", "--last-failed",
        action="store_true",
        help="只运行上次失败的测试"
    )
    
    # 生成HTML报告
    parser.add_argument(
        "--html",
        action="store_true",
        help="生成HTML测试报告"
    )
    
    # 清理缓存
    parser.add_argument(
        "--clean",
        action="store_true",
        help="清理pytest缓存"
    )
    
    args = parser.parse_args()
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    env["TESTING"] = "true"
    
    # 清理缓存
    if args.clean:
        cache_dirs = [
            project_root / ".pytest_cache",
            project_root / "__pycache__",
            project_root / ".coverage",
            project_root / "htmlcov",
            project_root / "test-results"
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                if cache_dir.is_file():
                    cache_dir.unlink()
                    print(f"删除文件: {cache_dir}")
                else:
                    import shutil
                    shutil.rmtree(cache_dir)
                    print(f"删除目录: {cache_dir}")
        
        print("缓存清理完成")
        return 0
    
    # 构建pytest命令
    cmd = ["python", "-m", "pytest"]
    
    # 添加测试目录或文件
    if args.file:
        cmd.append(args.file)
    else:
        cmd.append("tests/")
    
    # 添加标记过滤
    if args.type != "all":
        cmd.extend(["-m", args.type])
    
    # 详细输出
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # 覆盖率
    if args.coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=80"
        ])
    
    # 并行运行
    if args.numprocesses:
        cmd.extend(["-n", str(args.numprocesses)])
    
    # 失败时停止
    if args.exitfirst:
        cmd.append("-x")
    
    # 只运行失败的测试
    if getattr(args, 'last_failed', False):
        cmd.append("--lf")
    
    # HTML报告
    if args.html:
        cmd.extend(["--html=test-results/report.html", "--self-contained-html"])
        # 确保报告目录存在
        (project_root / "test-results").mkdir(exist_ok=True)
    
    # 其他有用的选项
    cmd.extend([
        "--tb=short",  # 简短的回溯信息
        "--strict-markers",  # 严格标记模式
        "--disable-warnings",  # 禁用警告
    ])
    
    print("="*60)
    print("开始运行测试")
    print("="*60)
    
    # 运行测试
    exit_code = run_command(cmd, cwd=str(project_root))
    
    print("="*60)
    if exit_code == 0:
        print("✅ 所有测试通过!")
        if args.coverage:
            print("📊 覆盖率报告已生成: htmlcov/index.html")
        if args.html:
            print("📋 HTML报告已生成: test-results/report.html")
    else:
        print("❌ 测试失败")
    print("="*60)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())