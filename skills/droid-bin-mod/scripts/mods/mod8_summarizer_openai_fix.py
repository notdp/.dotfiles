#!/usr/bin/env python3
"""mod8: summarizer/compress 对 OpenAI custom model 改用 Chat Completions API (+32 bytes)

问题根因:
 droid 里有两条 OpenAI custom model 的压缩路径仍会优先走 Responses API：
 1. summarizer openai → generic-chat-completion-api 分支
 2. 直接 openai → chat.completions fallback 分支

很多 OpenAI-compatible 代理（LiteLLM / OneAPI 等）不实现 /v1/responses，
或返回体没有 output_text，导致 compress 报错。

修改逻辑:
 1. 路径1: 在 openai 条件加 &&!1，并把 openai 并入 generic-chat-completion-api 分支 (+28 bytes)
 2. 路径2: 在 openai 条件加 &&!1，使其自然落到后面的 chat.completions.create 路径 (+4 bytes)

效果:
 两条 compress/summarizer 路径里的 provider==="openai" 都不再调用 responses.create。
"""
import re
import sys

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import V, load_droid, save_droid


def apply_generic_branch_patch(data):
    patched = (
        rb'provider==="openai"&&!1\)return\(await new ' + V + rb'\(\{apiKey:' + V +
        rb'\.apiKey,baseURL:' + V + rb'\.baseUrl,organization:null,project:null,defaultHeaders:' +
        V + rb'\.extraHeaders\}\)\.responses\.create\(\{model:' + V + rb',input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\}\)\)\.output_text;if\(' + V + rb'&&\(' +
        V + rb'\.provider==="generic-chat-completion-api"\|\|' + V + rb'\.provider=="openai"\)\)\{'
    )
    if re.search(patched, data):
        print("mod8 路径1 已应用，跳过")
        return data, 0

    pattern = (
        rb'(provider==="openai"\)return\(await new ' + V + rb'\(\{apiKey:' + V +
        rb'\.apiKey,baseURL:' + V + rb'\.baseUrl,organization:null,project:null,defaultHeaders:' +
        V + rb'\.extraHeaders\}\)\.responses\.create\(\{model:' + V + rb',input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\}\)\)\.output_text;if\(' + V + rb'&&)(' +
        V + rb'\.provider==="generic-chat-completion-api"\)\{)'
    )
    matches = list(re.finditer(pattern, data))
    if not matches:
        raise ValueError("mod8 失败: 未找到 summarizer openai+generic 路径")

    m = matches[0]
    g1 = m.group(1)
    g2 = m.group(2)

    var_match = re.match(V, g2)
    if not var_match:
        raise ValueError("mod8 失败: 无法提取 generic 条件变量名")
    var_name = var_match.group(0)

    new_g1 = g1.replace(b'provider==="openai")', b'provider==="openai"&&!1)')
    new_g2 = (b'(' + var_name + b'.provider==="generic-chat-completion-api"||'
              + var_name + b'.provider=="openai")){')

    old_full = g1 + g2
    new_full = new_g1 + new_g2
    delta = len(new_full) - len(old_full)
    assert delta == 28, f"mod8 路径1 预期 +28 bytes，实际 {delta:+d}"

    data = data.replace(old_full, new_full, 1)
    print(f"mod8 路径1: summarizer openai→generic fallback 完成 ({delta:+d} bytes)")
    return data, delta


def apply_direct_fallback_patch(data):
    patched = (
        rb'provider==="openai"&&!1\)return\(await ' + V +
        rb'\.responses\.create\(\{model:' + V + rb'\.model,input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\}\)\)\.output_text\|\|"";let ' + V +
        rb'=\(await ' + V + rb'\.chat\.completions\.create\('
    )
    if re.search(patched, data):
        print("mod8 路径2 已应用，跳过")
        return data, 0

    pattern = (
        rb'(provider==="openai"\)return\(await ' + V +
        rb'\.responses\.create\(\{model:' + V + rb'\.model,input:' + V +
        rb',store:!1,instructions:' + V + rb',max_output_tokens:' + V +
        rb'\}\)\)\.output_text\|\|"";let ' + V +
        rb'=\(await ' + V + rb'\.chat\.completions\.create\()'
    )
    matches = list(re.finditer(pattern, data))
    if not matches:
        raise ValueError("mod8 失败: 未找到 direct openai→chat 路径")

    old = matches[0].group(1)
    new = old.replace(b'provider==="openai")', b'provider==="openai"&&!1)', 1)
    delta = len(new) - len(old)
    assert delta == 4, f"mod8 路径2 预期 +4 bytes，实际 {delta:+d}"

    data = data.replace(old, new, 1)
    print(f"mod8 路径2: direct openai fallback 完成 ({delta:+d} bytes)")
    return data, delta


data = load_droid()
original_size = len(data)
total_delta = 0

for patcher in (apply_generic_branch_patch, apply_direct_fallback_patch):
    data, delta = patcher(data)
    total_delta += delta

if total_delta == 0:
    print("mod8 已应用，跳过")
    sys.exit(0)

assert len(data) == original_size + total_delta, (
    f"大小异常: {len(data) - original_size:+d} bytes"
)

save_droid(data)
print(f"mod8 summarizer/compress OpenAI → ChatCompletions fallback 完成 ({total_delta:+d} bytes)")
