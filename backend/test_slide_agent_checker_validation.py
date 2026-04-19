from __future__ import annotations

import json

from backend.slide_agent.slide_agent.utils import parse_markdown_to_slides

from backend.slide_agent.slide_agent.sub_agents.ppt_writer.utils import (
    FAILURE_STAGE_PARSE,
    FAILURE_STAGE_QUALITY,
    FAILURE_STAGE_STRUCTURE,
    advance_or_retry_after_validation,
    apply_checker_outcome_to_state,
    ensure_loop_state_initialized,
    evaluate_checker_result,
    validate_slide,
    validate_slide_quality,
)


CONTENT_SCHEMA = {
    "type": "content",
    "data": {
        "title": "AI 与商业应用",
        "items": [
            {"title": "自动化办公", "text": "Detailed content about 自动化办公"},
            {"title": "智能客服", "text": "Detailed content about 智能客服"},
        ],
    },
}

COVER_SCHEMA = {
    "type": "cover",
    "data": {
        "title": "AI 备课助手",
        "text": "聚焦课堂设计与内容组织，帮助教师高效完成备课演示。",
    },
}

TRANSITION_SCHEMA = {
    "type": "transition",
    "data": {
        "title": "课堂目标",
        "text": "本章先明确学习目标，再梳理教学重点与课堂推进方式。",
    },
}

END_SCHEMA = {"type": "end"}


def _valid_slide() -> dict:
    return {
        "type": "content",
        "data": {
            "title": "AI 与商业应用",
            "items": [
                {
                    "title": "自动化办公",
                    "text": "AI 可以自动整理会议纪要、流转审批与归档资料，显著减少重复性行政工作。",
                },
                {
                    "title": "智能客服",
                    "text": "企业通过智能客服处理标准化问答，并把人工客服聚焦到复杂问题与高价值客户。",
                },
            ],
        },
        "images": [{"src": "https://example.com/cover-image.jpg"}],
    }


def test_validate_slide_rejects_missing_required_fields():
    passed, issues = validate_slide({"type": "content", "data": {"title": "x"}}, CONTENT_SCHEMA)

    assert passed is False
    assert "data.items" in issues


def test_validate_slide_quality_rejects_placeholder_content():
    data = {
        "type": "content",
        "data": {
            "title": "AI 与商业应用",
            "items": [
                {"title": "自动化办公", "text": "Detailed content about 自动化办公"},
                {"title": "智能客服", "text": "Detailed content about 智能客服"},
            ],
        },
    }

    passed, issues = validate_slide_quality(data, CONTENT_SCHEMA)

    assert passed is False
    assert any("占位" in issue for issue in issues)


def test_validate_cover_like_quality_requires_cover_text():
    passed, issues = validate_slide_quality({"type": "cover", "data": {"title": "AI 备课助手", "text": ""}}, COVER_SCHEMA)

    assert passed is False
    assert "data.text 为空或过短" in issues


def test_validate_cover_like_quality_rejects_transition_placeholder_text():
    passed, issues = validate_slide_quality(
        {
            "type": "transition",
            "data": {"title": "课堂目标", "text": "Exploring the topic of 课堂目标"},
        },
        TRANSITION_SCHEMA,
    )

    assert passed is False
    assert "data.text 含占位或模板化表述" in issues


def test_validate_cover_like_quality_allows_end_without_data():
    passed, issues = validate_slide_quality({"type": "end"}, END_SCHEMA)

    assert passed is True
    assert issues == []


def test_validate_slide_allows_end_without_data_when_schema_has_no_data():
    passed, issues = validate_slide({"type": "end"}, END_SCHEMA)

    assert passed is True
    assert issues == []


def test_parse_markdown_to_slides_keeps_cover_transition_end_contract_consistent():
    slides = parse_markdown_to_slides(
        "# AI 备课助手\n\n## 课堂目标\n### 核心能力\n- 教学设计\n- 课堂互动\n"
    )

    assert slides[0] == {"type": "cover", "data": {"title": "AI 备课助手", "text": ""}}
    assert any(
        slide == {"type": "transition", "data": {"title": "课堂目标", "text": ""}}
        for slide in slides
    )
    assert slides[-1] == {"type": "end"}


def test_checker_accepts_end_without_data():
    outcome = evaluate_checker_result(json.dumps({"type": "end"}, ensure_ascii=False), END_SCHEMA)

    assert outcome.passed is True
    assert outcome.failure_stage is None
    assert outcome.parsed_data == {"type": "end"}


def test_checker_marks_parse_failure_when_writer_output_is_not_json():
    outcome = evaluate_checker_result("not json at all", CONTENT_SCHEMA)

    assert outcome.passed is False
    assert outcome.failure_stage == FAILURE_STAGE_PARSE
    assert outcome.is_valid_json is False
    assert outcome.feedback is not None
    assert "JSON" in outcome.feedback


def test_checker_marks_structure_failure_with_missing_fields():
    raw = '{"type":"content","data":{"title":"AI 与商业应用"}}'

    outcome = evaluate_checker_result(raw, CONTENT_SCHEMA)

    assert outcome.passed is False
    assert outcome.failure_stage == FAILURE_STAGE_STRUCTURE
    assert outcome.parsed_data is None
    assert "data.items" in outcome.issues


def test_checker_marks_quality_failure_with_feedback():
    raw = (
        '{"type":"content","data":{"title":"AI 与商业应用","items":['
        '{"title":"自动化办公","text":"Detailed content about 自动化办公"},'
        '{"title":"智能客服","text":"Detailed content about 智能客服"}]}}'
    )

    outcome = evaluate_checker_result(raw, CONTENT_SCHEMA)

    assert outcome.passed is False
    assert outcome.failure_stage == FAILURE_STAGE_QUALITY
    assert outcome.parsed_data is not None
    assert outcome.is_valid_json is True
    assert outcome.structure_passed is True
    assert outcome.quality_passed is False
    assert outcome.feedback is not None
    assert "内容质量" in outcome.feedback


def test_checker_passes_valid_slide_and_sets_clean_state():
    raw = str(_valid_slide()).replace("'", '"')

    outcome = evaluate_checker_result(raw, CONTENT_SCHEMA)
    state = {}
    apply_checker_outcome_to_state(state, outcome)

    assert outcome.passed is True
    assert state["last_validation_passed"] is True
    assert state["last_structure_validation_passed"] is True
    assert state["last_quality_validation_passed"] is True
    assert state["last_validation_failure_stage"] is None
    assert state["last_validation_issues"] == []
    assert state["last_slide_json"]["type"] == "content"


def test_controller_retries_without_advancing_on_quality_failure():
    state = ensure_loop_state_initialized(
        {
            "slides_plan_num": 2,
            "current_slide_index": 0,
            "last_written_raw": "bad output",
            "last_validation_passed": False,
            "last_validation_failure_stage": FAILURE_STAGE_QUALITY,
            "last_validation_feedback": "请重写",
        }
    )

    decision = advance_or_retry_after_validation(state, max_retries=3)

    assert decision.action == "retry"
    assert decision.next_slide_index == 0
    assert decision.retry_count == 1
    assert state["current_slide_index"] == 0
    assert state["writer_should_clear_history"] is False
    assert state["retry_count_map"][0] == 1


def test_controller_advances_and_resets_retry_after_success():
    slide = _valid_slide()
    state = ensure_loop_state_initialized(
        {
            "slides_plan_num": 2,
            "current_slide_index": 0,
            "last_written_raw": "raw-json",
            "last_slide_json": slide,
            "last_validation_passed": True,
            "last_structure_validation_passed": True,
            "last_quality_validation_passed": True,
            "retry_count_map": {0: 2},
        }
    )

    decision = advance_or_retry_after_validation(state, max_retries=3)

    assert decision.action == "advance"
    assert decision.next_slide_index == 1
    assert decision.retry_count == 0
    assert state["current_slide_index"] == 1
    assert state["generated_slides_content"] == [slide]
    assert state["retry_count_map"][0] == 0
    assert state["last_written_raw"] is None
    assert state["last_slide_json"] is None


def test_controller_degrades_after_retry_limit_and_preserves_failure_stage():
    state = ensure_loop_state_initialized(
        {
            "slides_plan_num": 1,
            "current_slide_index": 0,
            "last_written_raw": "still bad",
            "last_slide_json": None,
            "last_validation_passed": False,
            "last_validation_failure_stage": FAILURE_STAGE_STRUCTURE,
            "last_validation_feedback": "缺字段",
            "retry_count_map": {0: 3},
        }
    )

    decision = advance_or_retry_after_validation(state, max_retries=3)

    assert decision.action == "degrade"
    assert decision.degraded is True
    assert decision.failure_stage == FAILURE_STAGE_STRUCTURE
    assert decision.should_escalate is True
    assert state["current_slide_index"] == 1
    assert state["last_degraded_failure_stage"] == FAILURE_STAGE_STRUCTURE
    assert state["last_degraded_feedback"] == "缺字段"
    assert state["retry_count_map"][0] == 0
