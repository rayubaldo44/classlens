import logging

logger = logging.getLogger("classlens.telemetry")


def log_stage(stage: str, elapsed_ms: float, **fields: str | int | float | None) -> None:
    details = " ".join(f"{key}={value}" for key, value in sorted(fields.items()) if value is not None)
    logger.info("stage_timing stage=%s elapsed_ms=%.1f%s", stage, elapsed_ms, f" {details}" if details else "")


def log_error(stage: str, code: str, **fields: str | int | float | None) -> None:
    details = " ".join(f"{key}={value}" for key, value in sorted(fields.items()) if value is not None)
    logger.warning("stage_error stage=%s error_code=%s%s", stage, code, f" {details}" if details else "")
