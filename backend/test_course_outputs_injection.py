from backend.common.course_outputs_injection import (
    COURSE_OUTPUTS_END_MARKER,
    COURSE_OUTPUTS_START_MARKER,
    build_course_outputs_injection_markdown,
    split_course_outputs_injection,
)


def test_course_outputs_injection_markdown_has_start_and_end_markers():
    injection = build_course_outputs_injection_markdown("FULL TEXT", language="zh")
    assert COURSE_OUTPUTS_START_MARKER in injection
    assert COURSE_OUTPUTS_END_MARKER in injection
    assert "课程产出（全文，不经检索）" in injection


def test_split_course_outputs_injection_strips_block_without_polluting_outline_parser():
    """
    目标：确保“课程产出全文注入”不会被当作 Markdown 大纲结构解析成 PPT 目录/章节。
    """
    from backend.slide_agent.slide_agent.utils import parse_markdown_to_slides

    outline = "# 三角形的基本性质\n\n## 内角和\n### 定理\n- 结论\n"
    full_context = "# 教案\n## 教学目标\n- 目标1\n## 教学流程\n- 导入\n"
    injection = build_course_outputs_injection_markdown(full_context, language="zh")

    merged = "# 三角形的基本性质\n\n" + injection + "\n\n" + "\n".join(outline.splitlines()[2:]) + "\n"

    clean, block = split_course_outputs_injection(merged)

    assert COURSE_OUTPUTS_START_MARKER not in clean
    assert COURSE_OUTPUTS_END_MARKER not in clean
    assert "教学目标" not in clean  # 注入块不应残留在大纲中
    assert "教学目标" in block      # 但注入内容应能被取出作为参考

    slides = parse_markdown_to_slides(clean)
    contents_items = []
    for slide in slides:
        if slide.get("type") == "contents":
            contents_items = (slide.get("data") or {}).get("items") or []

    assert "内角和" in contents_items
    assert all("课程产出" not in str(x) for x in contents_items)

