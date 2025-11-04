from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

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


SQL_CALL_PATTERNS: Sequence[CallPattern] = (
    # Fully-qualified ccw.Statement(...)
    CallPattern(path=("ccw", "Statement"), arg_index=0, arg_name="statement"),
    # Direct Statement(...) calls (e.g., from ccw import Statement)
    CallPattern(path=("Statement",), arg_index=0, arg_name="statement"),
)

