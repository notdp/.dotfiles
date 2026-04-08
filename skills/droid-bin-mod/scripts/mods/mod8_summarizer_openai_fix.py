#!/usr/bin/env python3
"""mod14: summarizer compress 对 OpenAI custom model 改用 Chat Completions API (+28 bytes)

问题根因:
 summarizer (compress) 对 provider==="openai" 使用 OpenAI Responses API
 (responses.create → output_text)，但自定义代理 (LiteLLM 等) 通常不实现
 /v1/responses 端点，导致 output_text 为 undefined → compress 报错。

修改逻辑:
 1. 在 openai 条件加 &&!1 使其短路永不匹配 (+4 bytes)
 2. generic-chat-completion-api 条件扩展: ||N.provider=="openai" (+24 bytes)

效果:
 compress 时 provider==="openai" 的 custom model 改走 chat.completions.create 路径。
"""
import sys
import re
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from common import load_droid, save_droid, V

data = load_droid()
original_size = len(data)

if b'provider==="openai"&&!1)return(' in data:
    print("mod14 已应用，跳过")
    sys.exit(0)

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
    print("mod14 失败: 未找到 summarizer openai+generic 路径")
    print("  检查: strings ~/.local/bin/droid | grep 'store:!1,instructions:'")
    sys.exit(1)

m = matches[0]
g1 = m.group(1)
g2 = m.group(2)

var_match = re.match(V, g2)
if not var_match:
    print("mod14 失败: 无法提取 generic 条件变量名")
    sys.exit(1)
var_name = var_match.group(0)

new_g1 = g1.replace(b'provider==="openai")', b'provider==="openai"&&!1)')
new_g2 = (b'(' + var_name + b'.provider==="generic-chat-completion-api"||'
           + var_name + b'.provider=="openai")){')

old_full = g1 + g2
new_full = new_g1 + new_g2
delta = len(new_full) - len(old_full)

assert delta == 28, f"预期 +28 bytes，实际 {delta:+d}"

data = data.replace(old_full, new_full, 1)
assert len(data) == original_size + 28, f"大小异常: {len(data) - original_size:+d} bytes"

save_droid(data)
print(f"mod14 summarizer OpenAI → ChatCompletions fallback 完成 ({delta:+d} bytes)")
