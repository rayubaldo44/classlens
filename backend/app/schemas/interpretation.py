from pydantic import BaseModel, ConfigDict, Field, field_validator


class GroupLabelDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str = Field(min_length=1)
    label: str = Field(min_length=5, max_length=120)
    evidence_student_ids: list[str] = Field(min_length=1, max_length=3)

    @field_validator("group_id", "label")
    @classmethod
    def require_trimmed_single_line_text(cls, value: str) -> str:
        if value != value.strip() or "\n" in value or "\r" in value:
            raise ValueError("Text must be trimmed and single-line.")
        return value

    @field_validator("evidence_student_ids")
    @classmethod
    def require_unique_trimmed_evidence_ids(cls, values: list[str]) -> list[str]:
        if any(not value or value != value.strip() for value in values):
            raise ValueError("Evidence student IDs must be non-empty and trimmed.")
        if len(set(values)) != len(values):
            raise ValueError("Evidence student IDs must be unique.")
        return values


class GroupLabelBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labels: list[GroupLabelDraft]
