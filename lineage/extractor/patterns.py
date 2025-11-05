from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import ast


@dataclass(frozen=True)
class CallPattern:
    """Describes how to identify a SQL-carrying call and extract its SQL argument."""

    path: Tuple[str, ...]
    arg_index: Optional[int] = 0
    arg_name: Optional[str] = None

    def matches(self, call_path: Optional[Tuple[str, ...]]) -> bool:
        return call_path is not None and call_path == self.path

    def extract_argument(self, node: ast.Call) -> Optional[ast.AST]:
        if self.arg_name:
            for kw in node.keywords:
                if kw.arg == self.arg_name:
                    return kw.value
        if self.arg_index is not None and len(node.args) > self.arg_index:
            return node.args[self.arg_index]
        return None


DEFAULT_PATTERNS: Sequence[CallPattern] = (
    CallPattern(path=("ccw", "Statement"), arg_index=0, arg_name="statement"),
    CallPattern(path=("Statement",), arg_index=0, arg_name="statement"),
)


def load_patterns_from_specs(specs: Optional[Iterable[dict]]) -> Sequence[CallPattern]:
    patterns: List[CallPattern] = list(DEFAULT_PATTERNS)
    if not specs:
        return patterns

    for spec in specs:
        if not isinstance(spec, dict):
            continue
        path_value = spec.get("path")
        if not path_value:
            continue
        if isinstance(path_value, str):
            path = tuple(path_value.split("."))
        elif isinstance(path_value, (list, tuple)):
            path = tuple(str(part) for part in path_value)
        else:
            continue

        arg_index = spec.get("arg_index")
        arg_name = spec.get("arg_name")

        normalized_index: Optional[int]
        if arg_index is None:
            normalized_index = None
        elif isinstance(arg_index, int):
            normalized_index = arg_index
        elif isinstance(arg_index, str) and arg_index.isdigit():
            normalized_index = int(arg_index)
        else:
            normalized_index = 0

        normalized_name = str(arg_name) if arg_name is not None else None

        patterns.append(
            CallPattern(
                path=path,
                arg_index=normalized_index,
                arg_name=normalized_name,
            )
        )
    return patterns

