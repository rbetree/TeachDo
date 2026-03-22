from __future__ import annotations

"""
课程产出全文注入（gen:/full:）相关的 marker 与处理函数。

背景：
- main_api 的 /tools/ppt 会把“已生成产物”的全文（不经检索）注入到 Markdown 大纲中，
  以便下游 slide_agent 在生成 PPT 内容时能够获得参考上下文。
- 但 slide_agent 的 Markdown 解析器非常简单，会把注入区块里的 `##/###/-` 当作大纲结构，
  导致 PPT 结构被“引用产物”污染（出现照搬教案/照搬 PPT 目录结构的问题）。

解决思路：
- 统一用 start/end marker 包裹注入区块；
- 下游解析大纲前先剥离该区块，把其内容作为“参考资料”单独传递给写作 prompt。
"""


COURSE_OUTPUTS_START_MARKER = "<!-- teachdo:course-outputs-fulltext -->"
COURSE_OUTPUTS_END_MARKER = "<!-- teachdo:course-outputs-fulltext:end -->"


def build_course_outputs_injection_markdown(full_context: str, *, language: str) -> str:
    """
    构建可注入到 Markdown（大纲）中的“课程产出全文”区块。

    注意：该区块会被 slide_agent 在解析大纲前剥离，仅作为参考上下文使用。
    """
    if not (full_context or "").strip():
        return ""

    lang = (language or "zh").strip().lower()
    want_english = lang in {"en", "english"}

    title = "## Course outputs (full text, not retrieved)" if want_english else "## 课程产出（全文，不经检索）"
    note = (
        "> Note: This block is **reference-only** for consistency. Do NOT copy verbatim and do NOT treat it as outline.\n"
        if want_english
        else "> 说明：该区块仅用于“一致性对齐”的参考，不要原文照抄，也不要把它当作大纲结构。\n"
    )

    return (
        f"{COURSE_OUTPUTS_START_MARKER}\n"
        f"{title}\n\n"
        f"{note}\n"
        f"{full_context.strip()}\n"
        f"{COURSE_OUTPUTS_END_MARKER}"
    ).strip()


def split_course_outputs_injection(markdown: str) -> tuple[str, str]:
    """
    将注入的“课程产出全文”区块从 markdown 中剥离：
    - 返回 (clean_markdown, course_outputs_block)

    course_outputs_block 为去掉 marker 的区块文本（仍可能包含标题行/说明行），可作为参考上下文。
    若不存在完整区块（缺少 marker），则返回 (markdown, "")。
    """
    src = str(markdown or "")
    if COURSE_OUTPUTS_START_MARKER not in src:
        return src, ""
    if COURSE_OUTPUTS_END_MARKER not in src:
        # 旧格式或异常情况：避免误删用户大纲，选择不剥离
        return src, ""

    lines = src.splitlines()
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if start_idx is None and line.strip() == COURSE_OUTPUTS_START_MARKER:
            start_idx = i
            continue
        if start_idx is not None and line.strip() == COURSE_OUTPUTS_END_MARKER:
            end_idx = i
            break

    if start_idx is None or end_idx is None or end_idx <= start_idx:
        return src, ""

    block = "\n".join(lines[start_idx + 1 : end_idx]).strip()
    clean_lines = lines[:start_idx] + lines[end_idx + 1 :]
    clean = "\n".join(clean_lines)
    return clean, block

