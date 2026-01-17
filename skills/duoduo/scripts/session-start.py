#!/usr/bin/env python3
"""
session-start.py <name> <model> <pr_number> [--daemon]
创建 session，用 FIFO 持续接收消息

--daemon: 后台模式，持续运行
无参数: 只启动并输出 session ID，然后退出（daemon 由 wrapper 启动）
"""
import sys
import os
import json
import subprocess
import time

NAME = sys.argv[1]
MODEL = sys.argv[2]
PR = sys.argv[3]
DAEMON = "--daemon" in sys.argv
DROID = "/Users/notdp/.local/bin/droid"

FIFO = f"/tmp/duo-{PR}-{NAME}"
LOG = f"/tmp/duo-{PR}-{NAME}.log"

if DAEMON:
    # Daemon 模式：持续运行，从 FIFO 读取消息发给 droid
    log_file = open(LOG, "a", buffering=1)  # 行缓冲，支持 tail -f
    proc = subprocess.Popen(
        [DROID, "exec", "--input-format", "stream-jsonrpc", "--output-format", "stream-jsonrpc",
         "-m", MODEL, "--auto", "high", "--allow-background-processes"],
        stdin=subprocess.PIPE,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=os.environ.copy()  # 继承环境变量
    )
    
    # 发送 initialize_session
    init_req = {
        "jsonrpc": "2.0",
        "type": "request",
        "factoryApiVersion": "1.0.0",
        "method": "droid.initialize_session",
        "params": {"machineId": os.uname().nodename, "cwd": os.getcwd()},
        "id": "init"
    }
    proc.stdin.write(json.dumps(init_req) + "\n")
    proc.stdin.flush()
    
    # 持续从 FIFO 读取并转发
    while True:
        try:
            with open(FIFO, "r") as f:
                for line in f:
                    if line.strip():
                        proc.stdin.write(line)
                        proc.stdin.flush()
        except Exception as e:
            time.sleep(0.1)
            continue

else:
    # 启动模式：启动 daemon，等待 session ID，输出后退出
    
    # 清理旧 FIFO
    if os.path.exists(FIFO):
        os.remove(FIFO)
    os.mkfifo(FIFO)
    
    # 清空日志
    open(LOG, "w").close()
    
    # 启动 daemon 进程（继承环境变量）
    daemon_proc = subprocess.Popen(
        ["nohup", sys.executable, __file__, NAME, MODEL, PR, "--daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=os.environ.copy()  # 继承环境变量（包括 FACTORY_API_KEY）
    )
    
    # 等待 session ID（最多 10 秒）
    session_id = None
    for _ in range(20):
        time.sleep(0.5)
        try:
            with open(LOG, "r") as f:
                for line in f:
                    if '"sessionId"' in line:
                        data = json.loads(line)
                        if "result" in data and "sessionId" in data["result"]:
                            session_id = data["result"]["sessionId"]
                            break
            if session_id:
                break
        except:
            pass
    
    # 存到 Redis
    subprocess.run(["redis-cli", "HSET", f"duo:{PR}", f"{NAME}:session", session_id or ""], 
                   capture_output=True)
    subprocess.run(["redis-cli", "HSET", f"duo:{PR}", f"{NAME}:fifo", FIFO], 
                   capture_output=True)
    subprocess.run(["redis-cli", "HSET", f"duo:{PR}", f"{NAME}:pid", str(daemon_proc.pid)], 
                   capture_output=True)
    subprocess.run(["redis-cli", "HSET", f"duo:{PR}", f"{NAME}:log", LOG], 
                   capture_output=True)
    
    print(session_id or "")
