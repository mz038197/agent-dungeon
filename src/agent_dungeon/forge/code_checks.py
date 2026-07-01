from __future__ import annotations

import ast


def has_input_call(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "input":
                return True
    return False


def has_brain_constructor(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "Brain":
            return True
    return False


def _is_main_name_guard(test: ast.Compare) -> bool:
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    left = test.left
    if not isinstance(left, ast.Name) or left.id != "__name__":
        return False
    if len(test.comparators) != 1:
        return False
    comp = test.comparators[0]
    return isinstance(comp, ast.Constant) and comp.value == "__main__"


def _guard_body_has_main_call(body: list[ast.stmt]) -> bool:
    for node in body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if isinstance(func, ast.Name) and func.id == "main":
            return True
    return False


def has_main_call_in_main_guard(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        if not isinstance(node.test, ast.Compare):
            continue
        if not _is_main_name_guard(node.test):
            continue
        if _guard_body_has_main_call(node.body):
            return True
    return False
