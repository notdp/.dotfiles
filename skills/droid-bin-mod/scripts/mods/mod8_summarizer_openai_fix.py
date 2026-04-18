#!/usr/bin/env python3
"""mod8: summarizer/compress 对 OpenAI custom model 改用 Chat Completions API (+8 bytes)

问题根因:
 droid 里有两条 OpenAI custom model 的压缩路径仍会优先走 Responses API：
 1. BYOK custom model: lxH(h.provider) → responses.create → output_text
 2. proxy 路径:        lxH(W) → responses.create → output_text

很多 OpenAI-compatible 代理（LiteLLM / OneAPI 等）不实现 /v1/responses，
或返回体没有 output_text，导致 compress 报错。

修改逻辑:
 两处 if(lxH(...)) 条件加 &&!1 短路，使其自然落到后面的 chat.completions.create 路径。
 lxH 是 minified 函数名，定义为 function lxH(H){return H==="openai"||H==="xai"}
 不同版本函数名可能不同，用动态模式匹配。

v0.96.0: 使用 provider==="openai" 直接判断 (+32 bytes)
v0.99.0: 使用 lxH(provider) 函数调用 (+8 bytes)

效果:
 两条 compress/summarizer 路径不再调用 responses.create，都走 chat.completions.create。
"""
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import V, load_droid, save_droid

FN = rb'[A-Za-z_$][A-Za-z0-9_$]{0,5}'


def find_lxH_name(data):
    """动态查找 lxH 等效函数: function XX(H){return H==="openai"||H==="xai"}"""
    m = re.search(
        rb'function (' + FN + rb')\(' + V + rb'\)\{return ' + V +
        rb'==="openai"\|\|' + V + rb'==="xai"\}',
        data
    )
    if not m:
        raise ValueError("mod8 失败: 未找到 lxH 等效函数定义")
    return m.group(1)


def apply_byok_patch(data, fn_name):
    """路径1: BYOK custom model - lxH(h.provider) → lxH(h.provider)&&!1"""
    pat_patched = re.compile(
        fn_name + rb'\(' + V + rb'\.provider\)&&!1\)return\(await ' + V +
        rb'\.responses\.create\(\{model:' + V + rb',input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\},\{signal:' + V + rb'\}\)\)\.output_text'
    )
    if pat_patched.search(data):
        print("mod8 路径1 已应用，跳过")
        return data, 0

    pat_orig = re.compile(
        rb'(if\()(' + fn_name + rb'\(' + V + rb'\.provider\))(\)return\(await ' + V +
        rb'\.responses\.create\(\{model:' + V + rb',input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\},\{signal:' + V + rb'\}\)\)\.output_text)'
    )
    m = pat_orig.search(data)
    if not m:
        raise ValueError("mod8 失败: 未找到 BYOK summarizer openai 路径")

    old = m.group(0)
    new = m.group(1) + m.group(2) + b'&&!1' + m.group(3)
    delta = len(new) - len(old)
    assert delta == 4, f"mod8 路径1 预期 +4 bytes，实际 {delta:+d}"

    data = data.replace(old, new, 1)
    print(f"mod8 路径1: BYOK lxH(provider)&&!1 ({delta:+d} bytes)")
    return data, delta


def apply_proxy_patch(data, fn_name):
    """路径2: proxy - lxH(W) → lxH(W)&&!1"""
    pat_patched = re.compile(
        fn_name + rb'\(' + V + rb'\)&&!1\)return\(await ' + V +
        rb'\.responses\.create\(\{model:' + V + rb',input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\},\{headers:' + V + rb',signal:' + V + rb'\}\)\)\.output_text'
    )
    if pat_patched.search(data):
        print("mod8 路径2 已应用，跳过")
        return data, 0

    pat_orig = re.compile(
        rb'(if\()(' + fn_name + rb'\(' + V + rb'\))(\)return\(await ' + V +
        rb'\.responses\.create\(\{model:' + V + rb',input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\},\{headers:' + V + rb',signal:' + V + rb'\}\)\)\.output_text)'
    )
    m = pat_orig.search(data)
    if not m:
        raise ValueError("mod8 失败: 未找到 proxy summarizer openai 路径")

    old = m.group(0)
    new = m.group(1) + m.group(2) + b'&&!1' + m.group(3)
    delta = len(new) - len(old)
    assert delta == 4, f"mod8 路径2 预期 +4 bytes，实际 {delta:+d}"

    data = data.replace(old, new, 1)
    print(f"mod8 路径2: proxy lxH(W)&&!1 ({delta:+d} bytes)")
    return data, delta


data = load_droid()
original_size = len(data)

fn_name = find_lxH_name(data)
print(f"mod8: lxH 等效函数名 = {fn_name.decode()}")

total_delta = 0
for patcher in (apply_byok_patch, apply_proxy_patch):
    data, delta = patcher(data, fn_name)
    total_delta += delta

if total_delta == 0:
    print("mod8 已应用，跳过")
    sys.exit(0)

assert len(data) == original_size + total_delta, (
    f"大小异常: {len(data) - original_size:+d} bytes"
)

save_droid(data)
print(f"mod8 summarizer/compress OpenAI → ChatCompletions fallback 完成 ({total_delta:+d} bytes)")
