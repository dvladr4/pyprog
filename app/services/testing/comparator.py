"""Сравнение вывода ученика с ожидаемым."""
from __future__ import annotations


def compare(actual: str, expected: str, mode: str = "exact") -> bool:
    if mode == "exact":
        return actual.rstrip("\r\n") == expected.rstrip("\r\n")
    if mode == "ignore_whitespace":
        return "".join(actual.split()) == "".join(expected.split())
    if mode == "tokens":
        return actual.split() == expected.split()
    if mode == "float":
        try:
            a = [float(x.replace(",", ".")) for x in actual.split()]
            b = [float(x.replace(",", ".")) for x in expected.split()]
            if len(a) != len(b):
                return False
            return all(abs(x - y) <= 1e-9 for x, y in zip(a, b))
        except ValueError:
            return False
    return actual.rstrip("\r\n") == expected.rstrip("\r\n")
