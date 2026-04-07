"""Slack command handler for triggering Jenkins test-pipeline builds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

PIPELINE_NAME = "test-pipeline"
ALLOWED_JOBS = {"deploy-api", "deploy-web", "smoke-tests"}
ALLOWED_PARAMS = {"branch", "env", "version"}
CONTROL_PARAMS = {"confirm"}
EXPECTED_FORMAT = (
    "Expected format: `build <job> [branch=<value>] [env=<value>] [version=<value>]` "
    "where job is one of `deploy-api`, `deploy-web`, `smoke-tests`."
)


@dataclass(frozen=True)
class BuildRequest:
    job: str
    params: dict[str, str]


def parse_build_command(text: str) -> tuple[BuildRequest | None, str | None]:
    """Parse and validate a Slack build command."""
    stripped = (text or "").strip()
    if not stripped.startswith("build"):
        return None, None

    parts = stripped.split()
    if len(parts) < 2 or parts[0] != "build":
        return None, EXPECTED_FORMAT

    job = parts[1]
    if job not in ALLOWED_JOBS:
        return None, EXPECTED_FORMAT

    parsed: dict[str, str] = {}
    for token in parts[2:]:
        if "=" not in token:
            return None, EXPECTED_FORMAT
        key, value = token.split("=", 1)
        if not key or not value:
            return None, EXPECTED_FORMAT
        if key not in ALLOWED_PARAMS and key not in CONTROL_PARAMS:
            return None, EXPECTED_FORMAT
        if key in parsed:
            return None, EXPECTED_FORMAT
        parsed[key] = value

    env = parsed.get("env", "").strip().lower()
    if env == "prod" and parsed.get("confirm", "").strip().lower() != "yes":
        return None, EXPECTED_FORMAT

    forwarded = {k: v for k, v in parsed.items() if k in ALLOWED_PARAMS}
    return BuildRequest(job=job, params=forwarded), None


def handle_slack_command(
    text: str,
    jenkins_trigger: Callable[[str, str, dict[str, str]], object],
) -> str | None:
    """
    Handle one Slack message text.

    Returns:
      - None when message does not start with "build"
      - a user-facing error message for invalid command
      - a queued confirmation for valid commands
    """
    request, error = parse_build_command(text)
    if request is None:
        return error

    jenkins_trigger(PIPELINE_NAME, request.job, request.params)
    if request.params:
        params_text = ", ".join(
            f"{k}={v}" for k, v in sorted(request.params.items(), key=lambda item: item[0])
        )
    else:
        params_text = "(none)"

    return (
        f"Queued `{PIPELINE_NAME}` build.\n"
        f"Job: `{request.job}`\n"
        f"Parameters: `{params_text}`"
    )
