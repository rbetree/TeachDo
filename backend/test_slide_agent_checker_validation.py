from __future__ import annotations

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
