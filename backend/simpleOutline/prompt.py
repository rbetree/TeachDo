#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/26 13:24
# @File  : prompt.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

# 当用户上传或者输入的内容长度超过一定长度时，使用不同的prompt
# 设计的原因是，当用户上传一个PDF或者文章时，肯定是希望根据该文章生成大纲，进而使用该文章生成PPT，而不是网络搜索
# 如果用户输入的内容或者上传的内容很短，那么大概率需要通过网络搜索去搜索和扩充大纲，例如只输入1个topic，简单的话，那么
# 根据搜索去生成大纲更合理，所以当用户输入的长度大于USER_INPUT_NUMBER时，提示词变成只使用用户输入的内容生成大纲。
# 否则使用用户输入内容+网络搜索生成大纲
USER_INPUT_NUMBER = 1000

OUTLINE_LENGTH_PRESETS: dict[str, dict[str, object]] = {
    "short": {
        "sections": 3,
        "subsections_range": "2–3",
        "bullets_range": "2–3",
    },
    "standard": {
        "sections": 5,
        "subsections_range": "3–4",
        "bullets_range": "3–5",
    },
    "long": {
        "sections": 6,
        "subsections_range": "4–5",
        "bullets_range": "4–6",
    },
}


def build_outline_instruction(
    *,
    language: str,
    outline_length: str = "standard",
    use_web_search: bool = True,
) -> str:
    """
    动态构建大纲生成提示词。

    - outline_length: short | standard | long
    - use_web_search:
        - True: 允许模型调用 DocumentSearch 扩写细节
        - False: 明确禁止调用 DocumentSearch（工具层也会拦截）
    """
    length_key = (outline_length or "").strip().lower() or "standard"
    preset = OUTLINE_LENGTH_PRESETS.get(length_key) or OUTLINE_LENGTH_PRESETS["standard"]
    sections = int(preset["sections"])
    subsections_range = str(preset["subsections_range"])
    bullets_range = str(preset["bullets_range"])

    if use_web_search:
        intro = "根据用户的描述或者参考内容生成大纲。按下面的格式生成大纲，仅生成大纲即可，无需多余说明, 可以使用DocumentSearch进行大纲的细节补充。"
    else:
        intro = "根据用户的描述或者参考内容生成大纲。按下面的格式生成大纲，仅生成大纲即可，无需多余说明, 尽量根据用户提供的信息生成高质量的符合格式要求的大纲。禁止调用DocumentSearch。"

    return f"""
{intro}
输出格式与规则（严格遵守）：
- 使用Markdown标题层级：# 标题 → ## 一级部分 → ### 二级小节 → 列表要点
- 一级部分数量：{sections}个；每个一级部分下含{subsections_range}个二级小节
- 每个二级小节列出{bullets_range}个要点；要点使用短句，动词开头，不超过18字，不要句号
- 全文不写引言/结语/目录，不写解释性段落，不加任何额外说明
- 术语统一、风格一致，必要时加入可量化指标或示例
- 语言：{language}

输出示例格式如下：
# 标题

## 一级部分
### 二级小节
- 要点1
- 要点2
- 要点3

### 二级小节
- 要点1
- 要点2
- 要点3
- 要点4
- 要点5
""".strip()


# 兼容旧引用（默认标准长度）
OUTLINE_INSTRUCTION_WITH_SEARCH = build_outline_instruction(language="{language}", outline_length="standard", use_web_search=True)
OUTLINE_INSTRUCTION_NO_SEARCH = build_outline_instruction(language="{language}", outline_length="standard", use_web_search=False)
