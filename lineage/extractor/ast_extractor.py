from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExtractedStatement:
    """A ccw.Statement invocation discovered in a Python module."""

    sql: str
    file: Path
    function: Optional[str]
    lineno: int
    end_lineno: Optional[int]


class StatementExtractor(ast.NodeVisitor):
    """AST visitor that locates ccw.Statement calls and reconstructs SQL text."""

    def __init__(self, file_path: Path, common_config: Optional[Dict[str, object]] = None) -> None:
        self.file_path = file_path
        self.common_config: Dict[str, str] = {
            key: str(value) for key, value in (common_config or {}).items()
        }
        self.statements: List[ExtractedStatement] = []
        self._function_stack: List[str] = []
        self._function_defs: Dict[str, ast.FunctionDef] = {}
        self._function_call_stack: List[str] = []

    # ------------------------------------------------------------------
    # Visitor methods
    # ------------------------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802 (AST API)
        self._function_defs[node.name] = node
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function_defs[node.name] = node  # type: ignore[assignment]
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if self._is_ccw_statement(node):
            sql_text = self._extract_sql_argument(node)
            if sql_text:
                self.statements.append(
                    ExtractedStatement(
                        sql=sql_text,
                        file=self.file_path,
                        function=self._function_stack[-1] if self._function_stack else None,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", node.lineno),
                    )
                )
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_ccw_statement(node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr == "Statement"
        if isinstance(func, ast.Name):
            return func.id == "Statement"
        return False

    def _extract_sql_argument(self, node: ast.Call) -> Optional[str]:
        target_node: Optional[ast.AST] = None
        for kw in node.keywords:
            if kw.arg == "statement":
                target_node = kw.value
                break
        if target_node is None and node.args:
            target_node = node.args[0]
        if target_node is None:
            return None
        return self._resolve_node(target_node)

    # pylint: disable=too-many-return-statements
    def _resolve_node(self, node: ast.AST, *, local_env: Optional[Dict[str, str]] = None) -> str:
        if isinstance(node, ast.Constant):
            return self._resolve_constant(node)
        if isinstance(node, ast.JoinedStr):
            return self._resolve_joined_str(node, local_env=local_env)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._resolve_node(node.left, local_env=local_env)
            right = self._resolve_node(node.right, local_env=local_env)
            return left + right
        if isinstance(node, ast.Subscript):
            return self._resolve_subscript(node)
        if isinstance(node, ast.FormattedValue):
            return self._resolve_node(node.value, local_env=local_env)
        if isinstance(node, ast.Call):
            return self._resolve_call(node, local_env=local_env)
        if isinstance(node, ast.Name):
            if local_env and node.id in local_env:
                return local_env[node.id]
            return self._placeholder(node.id)
        if isinstance(node, ast.Attribute):
            return self._placeholder(self._attribute_name(node))
        # Fallback: use AST unparse for a readable placeholder
        return self._placeholder(ast.unparse(node))

    def _resolve_constant(self, node: ast.Constant) -> str:
        value = node.value
        if isinstance(value, (str, bytes)):
            return value.decode() if isinstance(value, bytes) else value
        return str(value)

    def _resolve_joined_str(self, node: ast.JoinedStr, *, local_env: Optional[Dict[str, str]] = None) -> str:
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(self._resolve_constant(value))
            elif isinstance(value, ast.FormattedValue):
                parts.append(self._resolve_node(value.value, local_env=local_env))
            else:
                parts.append(self._placeholder(ast.unparse(value)))
        return "".join(parts)

    def _resolve_call(self, node: ast.Call, *, local_env: Optional[Dict[str, str]] = None) -> str:
        # Handle simple wrappers such as str(common_config['key'])
        if isinstance(node.func, ast.Name) and node.args:
            func_name = node.func.id
            if func_name in {"str", "int", "float"}:
                return self._resolve_node(node.args[0], local_env=local_env)
            if func_name in self._function_defs:
                result = self._resolve_user_function_call(func_name, node, local_env=local_env)
                if result is not None:
                    return result
        return self._placeholder(ast.unparse(node))

    def _resolve_subscript(self, node: ast.Subscript) -> str:
        target = node.value
        if isinstance(target, ast.Name) and target.id == "common_config":
            key = self._resolve_slice_key(node.slice)
            if key is not None:
                if key in self.common_config:
                    return self.common_config[key]
                return f"{{{{common_config.{key}}}}}"
            return f"{{{{{ast.unparse(node)}}}}}"
        return self._placeholder(ast.unparse(node))

    @staticmethod
    def _resolve_slice_key(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value
            return str(node.value)
        if isinstance(node, ast.Index):  # Python <3.9 compatibility within AST
            return StatementExtractor._resolve_slice_key(node.value)
        return None

    @staticmethod
    def _attribute_name(node: ast.Attribute) -> str:
        parts: List[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        else:
            parts.append(ast.unparse(current))
        return ".".join(reversed(parts))

    @staticmethod
    def _placeholder(name: str) -> str:
        return f"{{{{{name}}}}}"

    def _resolve_user_function_call(
        self,
        name: str,
        call: ast.Call,
        *,
        local_env: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        func_def = self._function_defs.get(name)
        if func_def is None:
            return None
        if name in self._function_call_stack:
            return None

        params = [arg.arg for arg in func_def.args.args]
        if len(call.args) != len(params):
            return None

        env: Dict[str, str] = {}
        if local_env:
            env.update(local_env)

        self._function_call_stack.append(name)
        try:
            for stmt in func_def.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    value = self._resolve_node(stmt.value, local_env=env)
                    env[stmt.targets[0].id] = value
                elif isinstance(stmt, ast.Return):
                    return self._resolve_node(stmt.value, local_env=env)
        finally:
            self._function_call_stack.pop()
        return None


def extract_statements_from_file(
    file_path: Path, common_config: Optional[Dict[str, object]] = None
) -> List[ExtractedStatement]:
    """Parse *file_path* and return discovered SQL statements."""

    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    extractor = StatementExtractor(file_path=file_path, common_config=common_config)
    extractor.visit(tree)
    return extractor.statements
