"""Сервис задач: примеры, тесты, импорт/экспорт usloviya.json."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.task import Task, TaskExample, TaskTest


# ---------- примеры ----------

def replace_examples(db: Session, task: Task, examples: list[dict]) -> None:
    """Перезаписать список примеров у задачи (с сохранением порядка)."""
    for ex in list(task.examples):
        db.delete(ex)
    db.flush()
    for i, ex in enumerate(examples):
        inp = (ex.get("input") or "").rstrip("\n")
        out = (ex.get("output") or "").rstrip("\n")
        if not inp and not out:
            continue
        db.add(TaskExample(task_id=task.id, order=i, input=inp, output=out))
    db.commit()


# ---------- тесты ----------

def replace_tests(db: Session, task: Task, tests: list[dict],
                  *, file_content: str | None = None) -> None:
    """Перезаписать список тестов. file_content — если задача с open()."""
    for t in list(task.tests):
        db.delete(t)
    db.flush()
    for i, t in enumerate(tests):
        inp = ((t.get("input") or "").replace("\r\n", "\n")
               .replace("\r", "\n").rstrip("\n"))
        out = ((t.get("output") or t.get("expected_output") or "")
               .replace("\r\n", "\n").replace("\r", "\n").rstrip("\n"))
        fc = (t.get("file_content") or file_content or "")
        fc = fc.replace("\r\n", "\n").replace("\r", "\n")
        db.add(TaskTest(task_id=task.id, order=i,
                        input=inp, expected_output=out, file_content=fc))
    db.commit()


def append_tests(db: Session, task: Task, tests: list[dict]) -> int:
    """Добавить тесты к существующим (вернёт новое количество)."""
    start = len(task.tests)
    for i, t in enumerate(tests, start=start):
        inp = (t.get("input") or "").rstrip("\n")
        out = (t.get("output") or t.get("expected_output") or "").rstrip("\n")
        db.add(TaskTest(task_id=task.id, order=i, input=inp,
                        expected_output=out, file_content=t.get("file_content")))
    db.commit()
    return len(task.tests)


def delete_test(db: Session, test_id: int, task_id: int) -> None:
    t = db.get(TaskTest, test_id)
    if t and t.task_id == task_id:
        db.delete(t)
        # переупакуем order
        db.flush()
        for i, t in enumerate(db.query(TaskTest).filter_by(task_id=task_id)
                              .order_by(TaskTest.order).all()):
            t.order = i
        db.commit()


def parse_tests_json(raw: str) -> list[dict]:
    """Принимает: [{input,output}, ...] либо {"tests":[...]}.

    Если у теста поле output, а не expected_output — нормализуем.
    Бросает ValueError с понятным текстом.
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("Пустой JSON")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка JSON: {e.msg} (строка {e.lineno}, колонка {e.colno})") from e

    if isinstance(data, dict):
        data = data.get("tests") or data.get("cases") or []
    if not isinstance(data, list):
        raise ValueError("Ожидался массив тестов: [{\"input\": ..., \"output\": ...}, ...]")

    result = []
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Тест #{i}: ожидался объект")
        if "input" not in item:
            raise ValueError(f"Тест #{i}: нет поля 'input'")
        if "output" not in item and "expected_output" not in item:
            raise ValueError(f"Тест #{i}: нет поля 'output' или 'expected_output'")
        def _norm(x):
            if x is None:
                return None
            return str(x).replace("\r\n", "\n").replace("\r", "\n")
        result.append({
            "input": _norm(item["input"]) or "",
            "output": _norm(item.get("output", item.get("expected_output"))) or "",
            "file_content": _norm(item.get("file_content")),
        })
    return result


# ---------- импорт usloviya.json ----------

_RE_EXTRA_BRACE_22 = re.compile(r'},\s*\{\s*("22"\s*:)')
_RE_FIX_TAIL = re.compile(r'}\s*}\s*$')


def fix_broken_usloviya(raw: str) -> str:
    """Чинит типовые поломки usloviya.json:
      * лишняя `{` перед `"22":` (было `{` вместо ключа);
      * лишняя `}` в конце (если после фикса получается валидный JSON — возвращаем).
    Если не получилось — возвращаем исходник, пусть json.loads ругнётся сам.
    """
    # 1) убираем `{` перед "22":
    fixed = _RE_EXTRA_BRACE_22.sub(r'},\n  \1', raw)
    # 2) проверим, валидно ли; если нет — попробуем срезать одну лишнюю } в конце
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass
    trimmed = _RE_FIX_TAIL.sub("}", fixed)
    try:
        json.loads(trimmed)
        return trimmed
    except json.JSONDecodeError:
        return fixed

def import_usloviya(db: Session, raw: str, *, tests_dir: str | None = None,
                    overwrite: bool = False) -> dict[str, Any]:
    """Импортирует usloviya.json в БД.

    overwrite=False — существующие задачи пропускаются (по external_number).
    tests_dir — если задан и там есть {N}.json, тесты подхватятся.
    Возвращает {'created': [...], 'skipped': [...], 'tests_loaded': N, 'errors': [...]}.
    """
    fixed = fix_broken_usloviya(raw)
    try:
        data = json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ValueError(f"Не удалось разобрать JSON: {e.msg} (строка {e.lineno})") from e

    if not isinstance(data, dict):
        raise ValueError("usloviya.json должен быть объектом {номер: {...}}")

    created: list[int] = []
    skipped: list[int] = []
    errors: list[str] = []
    tests_loaded = 0
    tests_root = Path(tests_dir) if tests_dir else None

    for key, cond in data.items():
        try:
            ext = int(key)
        except (TypeError, ValueError):
            errors.append(f"Пропущен нечисловой ключ: {key!r}")
            continue
        if not isinstance(cond, dict):
            errors.append(f"Задача {ext}: ожидался объект, получено {type(cond).__name__}")
            continue

        task = db.query(Task).filter_by(external_number=ext).first()
        if task and not overwrite:
            skipped.append(ext)
            continue

        # Собираем поля ДО создания/флаша, чтобы INSERT шёл с готовыми значениями
        title = (cond.get("title") or f"Задача {ext}").strip() or f"Задача {ext}"
        description = cond.get("description") or ""

        if not task:
            task = Task(
                external_number=ext,
                title=title,
                description=description,
                is_published=True,
            )
            db.add(task)
        else:
            task.title = title
            task.description = description
            task.is_published = True
        db.flush()

        # примеры
        for ex in list(task.examples):
            db.delete(ex)
        db.flush()
        for i, ex in enumerate(cond.get("examples") or []):
            if not isinstance(ex, dict):
                continue
            db.add(TaskExample(task_id=task.id, order=i,
                               input=str(ex.get("input", ""))
                                    .replace("\r\n", "\n")
                                    .replace("\r", "\n").rstrip("\n"),
                               output=str(ex.get("output", ""))
                                    .replace("\r\n", "\n")
                                    .replace("\r", "\n").rstrip("\n")))

        # тесты из tests/{ext}.json
        if tests_root:
            test_file = tests_root / f"{ext}.json"
            if test_file.exists():
                try:
                    tests = parse_tests_json(test_file.read_text(encoding="utf-8"))
                except ValueError as e:
                    errors.append(f"Задача {ext}: {e}")
                else:
                    for t in list(task.tests):
                        db.delete(t)
                    db.flush()
                    for i, t in enumerate(tests):
                        def _n(x):
                            return str(x or "").replace("\r\n", "\n").replace("\r", "\n")
                        db.add(TaskTest(task_id=task.id, order=i,
                                        input=_n(t["input"]),
                                        expected_output=_n(t["output"]),
                                        file_content=_n(t.get("file_content")) or None))
                    tests_loaded += len(tests)

        created.append(ext)
        db.commit()

    return {
        "created": created,
        "skipped": skipped,
        "tests_loaded": tests_loaded,
        "errors": errors,
    }


# ---------- задачи с open(): тесты с файлом ----------

def add_test_with_file(db, task, file_content: str, expected_output: str) -> int:
    """Добавить тест для задачи с open(): файл + ожидаемый вывод."""
    order = len(task.tests)
    db.add(TaskTest(
        task_id=task.id,
        order=order,
        input="",  # с клавиатуры ничего не читается
        expected_output=(expected_output or "").replace("\r\n", "\n").replace("\r", "\n").rstrip("\n"),
        file_content=(file_content or "").replace("\r\n", "\n").replace("\r", "\n"),
    ))
    db.commit()
    return order


def update_test_with_file(db, task, test_id: int,
                          file_content: str | None,
                          expected_output: str) -> bool:
    """Обновить тест для задачи с open(). Если file_content is None — файл не трогаем."""
    t = db.get(TaskTest, test_id)
    if not t or t.task_id != task.id:
        return False
    t.expected_output = ((expected_output or "").replace("\r\n", "\n").replace("\r", "\n").rstrip("\n"))
    if file_content is not None:
        t.file_content = (file_content.replace("\r\n", "\n").replace("\r", "\n"))
    db.commit()
    return True


def clear_test_file(db, task, test_id: int) -> bool:
    t = db.get(TaskTest, test_id)
    if not t or t.task_id != task.id:
        return False
    t.file_content = ""
    db.commit()
    return True
