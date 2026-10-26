from time import perf_counter

from pydantic import ValidationError

from app.prompts.misconception_labels import PROMPT_VERSION, build_misconception_labels_prompt
from app.providers.llm import LLMProviderError, LLMService
from app.schemas.analysis import AnalysisResponse
from app.schemas.interpretation import GroupLabelBatch
from app.telemetry import log_error, log_stage


class InterpretationOutputError(ValueError):
    pass


async def interpret_misconception_groups(
    result: AnalysisResponse,
    llm_service: LLMService,
) -> AnalysisResponse:
    if not result.groups:
        return result.model_copy(deep=True)

    started = perf_counter()
    try:
        raw_batch = await llm_service.generate_group_labels(build_misconception_labels_prompt(result))
        batch = GroupLabelBatch.model_validate(raw_batch.model_dump())
        labels_by_group = _validate_batch(result, batch)
    except (LLMProviderError, ValidationError, InterpretationOutputError) as error:
        code = error.code if isinstance(error, LLMProviderError) else "label_output_invalid"
        log_error(
            "misconception_interpretation",
            code,
            model=llm_service.model_id,
            prompt_version=PROMPT_VERSION,
            group_count=len(result.groups),
        )
        fallback = result.model_copy(deep=True)
        for group in fallback.groups:
            group.interpretation_status = "fallback"
        log_stage(
            "misconception_interpretation",
            (perf_counter() - started) * 1000,
            model=llm_service.model_id,
            prompt_version=PROMPT_VERSION,
            group_count=len(result.groups),
            status="fallback",
        )
        return fallback

    interpreted = result.model_copy(deep=True)
    for group in interpreted.groups:
        group.provisional_label = labels_by_group[group.group_id]
        group.interpretation_status = "completed"
    log_stage(
        "misconception_interpretation",
        (perf_counter() - started) * 1000,
        model=llm_service.model_id,
        prompt_version=PROMPT_VERSION,
        group_count=len(result.groups),
        status="completed",
    )
    return interpreted


def _validate_batch(result: AnalysisResponse, batch: GroupLabelBatch) -> dict[str, str]:
    expected = {group.group_id: group for group in result.groups}
    received_ids = [label.group_id for label in batch.labels]
    if len(received_ids) != len(set(received_ids)) or set(received_ids) != set(expected):
        raise InterpretationOutputError("The label batch must cover every supplied group exactly once.")

    labels: dict[str, str] = {}
    for label in batch.labels:
        representative_ids = {
            item.student_id for item in expected[label.group_id].representative_responses
        }
        if not set(label.evidence_student_ids).issubset(representative_ids):
            raise InterpretationOutputError("A label referenced evidence outside its supplied group.")
        labels[label.group_id] = label.label
    return labels
