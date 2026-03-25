#promt的前缀
# 不带图片，不搜索的
import os
PREFIX_PAGE_PROMPT = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有“内容页特例”说明，不得新增字段或改变数组长度。
3. 统一输出为{language}；专有名词可带英文小写缩写。
4. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
5. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。
"""

# 带搜索图片的
PREFIX_PAGE_PROMPT_WITH_IMAGE = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有“内容页特例”说明，不得新增字段或改变数组长度。
   - 例外：你需要在 JSON 顶层新增 images 字段（数组），用于配图。
3. 统一输出为{language}；专有名词可带英文小写缩写。
4. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
5. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。

# 重要：图片搜索工具使用
你必须为每个页面搜索合适的配图！使用 SearchImage 工具搜索相关图片，然后将图片信息添加到返回的 JSON 中。
- 你必须自己生成英文检索 query（不要用纯中文），并调用 SearchImage(query, count=6) 返回 6 张候选图。
- images 字段必须放在 JSON 顶层（与 type 同级），不要放在 data 内。

# 图片搜索规则（关键：必须“贴主题”，避免泛化）：
- query 必须包含本页的主题关键词（英文，来自 data.title 或 data.text 的翻译/提取），不要只用 technology/business/abstract 这类泛词。
- 对 content 页：query 还必须额外包含 1～2 个更具体的“内容锚点词”（英文，来自 data.items[*].title 的翻译/提取），例如 object detection / camera / classroom / factory / chart 等。
- 风格词建议：diagram / illustration / background / minimal（按页型选择）。
- 若 SearchImage 返回结果的 alt 大量出现 laptop/keyboard/office/desk 等“通用电脑办公图”，说明 query 过泛或缺少锚点词：请把锚点词写得更具体后重试 1 次 SearchImage（最多重试 1 次），并使用更相关那次的结果写入 images。

# 图片质量要求：
- 优先选择“简洁、干净、适合作为演示背景/插图”的图片（尽量避免强人物特写、明显水印/大段文字）。

# 图片数据格式：
在 JSON 中添加 images 字段，包含搜索到的图片信息：
{{
  "type": "cover",
  "data": {{ ... }},
  "images": [
    {{
      "id": "图片ID",
      "src": "图片URL",
      "alt": "图片描述"
    }}
  ]
}}
"""
# 带搜索的prompt
PREFIX_PAGE_PROMPT_WITH_SEARCH = """
# 通用约束：
1. 你将收到一段 单行 JSON，键名固定为 type 和 data（如有）。
2. 保持原有结构与键名尽量不变：**不得修改已有字段的名称**；**不得删除既有字段**。除非另有“内容页特例”说明，不得新增字段或改变数组长度。
   - 例外：若可用工具包含 SearchImage，则允许在 JSON 顶层新增 images 字段（数组），用于配图。
3. 必须使用搜索工具{tool_names}进行搜索，然后完成内容扩充。
4. 统一输出为{language}；专有名词可带英文小写缩写。
5. 文风：简洁、商务演示友好，避免夸张或无法证实的数字。
6. 严禁输出除 JSON 外的任何内容（包括说明、Markdown、代码块围栏）。

# 若工具列表包含 SearchImage（联网配图）：
- 你必须为每个页面调用 SearchImage 工具获取配图，并把结果写入 JSON 顶层 images 字段。
- 你必须自己生成英文检索 query（不要用纯中文），并调用 SearchImage(query, count=6) 返回 6 张候选图。
- images 字段必须放在 JSON 顶层（与 type 同级），不要放在 data 内。
- query 必须“贴主题”，建议结构：`本页主题关键词(英文) + 本页内容锚点词(英文) + 风格关键词(如 minimal/diagram/illustration/background)`。
- 禁止只用 technology/business/abstract 等泛词 + minimal/background 这类风格词组合，否则很容易命中无关图片。
- 若 SearchImage 返回结果 alt 大量出现 laptop/keyboard/office/desk 等“通用电脑办公图”，说明 query 过泛：请追加更具体的锚点词后重试 1 次 SearchImage（最多重试 1 次），并使用更相关那次的结果写入 images。
- 图片质量要求：优先选择“简洁、干净、适合作为演示背景/插图”的图片（尽量避免强人物特写、明显水印/大段文字）。
"""

# input_slide_data代表slide的json的模版
COVER_PAGE_PROMPT="""
封面页（type: "cover"）
你是PPT封面文案优化器,使用的语言是{language}。保持 title 原样，不改；重写 data.text 为 18～32 字的副标题，强调主题价值与适用场景，避免标点堆叠与口号化。
{input_slide_data}
"""

CONTENTS_PAGE_PROMPT = """
目录页（type: "contents"）
你是PPT目录优化器,使用的语言是{language}。仅在需要时对 data.items[*] 的短语做轻微润色（可名词化或动宾化，使其更像目录条目），不得改变顺序与数量；每项不超过14个字；不添加或删除项目。
{input_slide_data}
"""

TRANSITION_PAGE_PROMPT = """
过渡页（type: "transition"）
你是章节过渡文案撰写者,使用的语言是{language}。保持 data.title 原样不改；重写 data.text 为2～3句过渡语，每句12～24字，说明本章为何重要、将回答什么问题、读者可获得的收获。避免夸张或口号化表达。
{input_slide_data}
"""

# 不带图表的prompt，如果对于智力比较差的模型，可以不要带图表，助手下面的CONTENT_PAGE_PROMPT，然后启用这个
def _truthy_env(name: str) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


# USE_CHART 允许设置为 false/0 来禁用图表生成
if _truthy_env("USE_CHART"):
    # 带图表的prompt
    CONTENT_PAGE_PROMPT = """
    内容页（type: "content"）
    你是技术与产业结合的内容扩写器，使用的语言是{language}。保持 data.title 与各 items[*].title 原样不改；对 items[*].text 逐项扩写为 2～3 句、合计 60～120 字，采用“是什么→为何重要→如何落地/示例”的逻辑；不得删除已有 items；避免编造精确数据或过度承诺。

# 图表（严格防止编造）：
仅当本页主题涉及趋势/对比/占比/量化指标，且通过检索获得“可引用的权威来源数据”时，才允许在 data.items **末尾**新增 1 个 `{{"kind":"chart", ...}}` 项；否则**不要**新增图表。
- **来源要求**：使用的数据**必须来自工具返回的原文内容**。
- **数据要求**：所有数值必须与来源一致；不得估算/外推/上色演示。
- **类型选择**：时间趋势用 line，类目对比用 bar，占比用 pie。
- **找不到即拒绝**：若未找到可引用数据，保持原结构不变，并在本页末尾追加一句固定话术：“未检索到可引用的数据，故不新增图表。”
- **字段限制**：不得新增chart 以外的其他字段。

# 输出结构（不得变更）：
- 原始结构（type、data）保持不变；
- 你可以在 data.items 中**最多新增 1 个**图表 item（不替换已存在文本 item）；
- 图表 item 的 JSON 结构**扩展为**（以下附加字段为必填）：
{{
  "kind": "chart",                                    # 必填，固定字符串 "chart"
  "title": "图表标题",                                # 建议 ≤ 16 字，不要添加来源信息
  "text": "图表的描述信息",                             # 建议 ≤ 40 字，不要添加来源信息
  "chartType": "line" | "bar" | "pie" | "column" | "ring" | "area" | "radar",
  "labels": ["类目或时间刻度", ...],                    # 4~8 个，均为字符串
  "series": [                                           # 1~2 组数据
    {{ "name": "系列名", "data": [数值, ...] }}         # data 长度与 labels 一致，均为数字
  ],
  "options": {{
      "xAxis": {{ "name": "xxx" }},
      "yAxis": {{ "name": "xxx" }} 
  }},
}}

# 检索与证据：
- 先检索再写作。
- 图表以外的内容若涉及定量描述，需加“区间/范围/定性词”，避免精确值。

# 何时应当新增图表：
- 仅当存在可视化价值且**找到了**可引用数据；否则不要新增图表。

    # 原始结构
    {input_slide_data}
    """
else:
    CONTENT_PAGE_PROMPT = """
    内容页（type: "content"）
    你是技术与产业结合的内容扩写器。保持 data.title 与各 items[*].title 原样不改；对 items[*].text 逐项扩写为 2～3 句、合计 60～120 字，采用“是什么→为何重要→如何落地/示例”的逻辑；不得删除已有 items；避免编造精确数据或过度承诺。
    
    # 原始结构
    {input_slide_data}
    """


END_PAGE_PROMPT = """
结束页（type: "end"）
你是PPT结束页生成器,使用的语言是{language}。若无 data 字段则原样返回；若存在 data.text，则改写为10～16字的感谢语，语气真诚克制，可包含“感谢观看/欢迎交流”等，不添加多余字段。
{input_slide_data}
"""
# 不同的类型的页面对应的prompt
prompt_mapper = {
    "cover": COVER_PAGE_PROMPT,
    "contents": CONTENTS_PAGE_PROMPT,
    "transition": TRANSITION_PAGE_PROMPT,
    "content": CONTENT_PAGE_PROMPT,
    "end": END_PAGE_PROMPT,
}
