from __future__ import annotations

import json
from typing import Any, Dict

from .models import SideCommand, SideProject, SideSuite, SideTest


def _build_command(raw: Dict[str, Any]) -> SideCommand:
    return SideCommand(
        id=raw.get("id", ""),
        command=raw.get("command", ""),
        target=raw.get("target", "") or "",
        value=raw.get("value", "") or "",
        comment=raw.get("comment"),
    )


def _build_test(raw: Dict[str, Any]) -> SideTest:
    commands = [_build_command(command) for command in raw.get("commands", [])]
    return SideTest(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        commands=commands,
    )


def _build_suite(raw: Dict[str, Any]) -> SideSuite:
    return SideSuite(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        tests=list(raw.get("tests", [])),
        persist_session=bool(raw.get("persistSession", False)),
        parallel=bool(raw.get("parallel", False)),
        timeout=raw.get("timeout"),
    )


def load_side_project(json_payload: str, *, default_name: str | None = None) -> SideProject:
    """Selenium IDE .side JSON 문자열을 SideProject 객체로 변환."""
    if not isinstance(json_payload, str):
        raise TypeError("json_payload 는 문자열이어야 합니다.")
    raw_project = json.loads(json_payload)
    project_name = raw_project.get("name") or default_name or "Unnamed Project"

    tests = [_build_test(test) for test in raw_project.get("tests", [])]
    test_map = {test.id: test for test in tests}

    suites = [_build_suite(suite) for suite in raw_project.get("suites", [])]

    return SideProject(
        id=raw_project.get("id", ""),
        name=project_name,
        url=raw_project.get("url"),
        tests=test_map,
        suites=suites,
    )

