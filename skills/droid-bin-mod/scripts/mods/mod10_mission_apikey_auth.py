#!/usr/bin/env python3
"""mod10: Mission spawn 支持 API key 认证

问题: mission worker spawn 需要 access_token (OAuth)，仅 API key 登录时无 access_token → 报错
修复: 客户端 fallback 到 API key + daemon 端正确路由 API-key-as-token

两处 patch:
  A) 获取 access_token 的函数: 不存在时 fallback 到 FACTORY_API_KEY
  B) daemon 认证路由函数: token 以 "fk-" 开头时走 API key 验证路径

字节: +37 bytes，由 comp_universal.py 统一补偿
"""
import re
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()

# === 双点检测: 两处 patch 都已应用才算完成 ===
has_a = b'||process.env.FACTORY_API_KEY;' in data and b'No access token available' in data
has_b = bool(re.search(
    rb'\(' + V + rb'\|\|' + V + rb'\)\?\.startsWith\(' + V + rb'\)\)return ' + V + rb'\(', data))

if has_a and has_b:
    print("mod10 已应用 (A+B)，跳过")
    sys.exit(0)
elif has_a:
    print("mod10 部分应用 (仅A)，继续补 Patch B")
elif has_b:
    print("mod10 部分应用 (仅B)，继续补 Patch A")

total_diff = 0

# === Patch A: access_token fallback to FACTORY_API_KEY ===
# 结构: ?.access_token?.trim();if(!VAR)throw new VAR("No access token available");return VAR
if not has_a:
    pat_a = (rb'(\?\.access_token\?\.trim\(\));if\(!(' + V + rb')\)throw new ('
             + V + rb')\("No access token available"\);return \2')
    m_a = re.search(pat_a, data)
    if not m_a:
        raise ValueError("Patch A: 未找到 access_token + throw 模式")
    old_a = m_a.group(0)
    if data.count(old_a) != 1:
        raise ValueError(f"Patch A: 找到 {data.count(old_a)} 处 (期望1)")
    var = m_a.group(2)
    err_cls = m_a.group(3)
    new_a = (m_a.group(1) + b'||process.env.FACTORY_API_KEY;if(!' + var
             + b')throw new ' + err_cls + b'("No access token available");return ' + var)
    data = data.replace(old_a, new_a, 1)
    diff_a = len(new_a) - len(old_a)
    total_diff += diff_a
    print(f"mod10a fallback: +{diff_a} bytes")

# === Patch B: daemon 认证路由 API-key-as-token ===
# 结构: if(VAR?.startsWith(VAR))return VAR(VAR,VAR);if(VAR)return
# VAR1=apiKey, VAR2=prefix const("fk-"), VAR3=validator, VAR1 again, VAR4=baseUrl, VAR5=token
if not has_b:
    pat_b = (rb'if\((' + V + rb')\?\.startsWith\((' + V + rb')\)\)return ('
             + V + rb')\(\1,(' + V + rb')\);if\((' + V + rb')\)return')
    m_b = re.search(pat_b, data)
    if not m_b:
        raise ValueError("Patch B: 未找到 startsWith 路由模式")
    old_b = m_b.group(0)
    if data.count(old_b) != 1:
        raise ValueError(f"Patch B: 找到 {data.count(old_b)} 处 (期望1)")
    apiKey, prefix, validator, baseUrl, token = (
        m_b.group(1), m_b.group(2), m_b.group(3), m_b.group(4), m_b.group(5))
    new_b = (b'if((' + apiKey + b'||' + token + b')?.startsWith(' + prefix
             + b'))return ' + validator + b'(' + apiKey + b'||' + token + b','
             + baseUrl + b');if(' + token + b')return')
    data = data.replace(old_b, new_b, 1)
    diff_b = len(new_b) - len(old_b)
    total_diff += diff_b
    print(f"mod10b route: +{diff_b} bytes")

save_droid(data)
print(f"mod10 完成 (本次 +{total_diff} bytes，需要 comp_universal.py 补偿)")
