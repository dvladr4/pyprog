"""Импорт старых данных: usloviya.json + tests/*.json -> БД.

    python -m scripts.import_legacy path/to/usloviya.json path/to/tests_dir
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models.task import Task, TaskExample, TaskTest


def main(usloviya_path: str, tests_dir: str) -> None:
    usloviya = json.loads(Path(usloviya_path).read_text(encoding="utf-8"))
    tests_root = Path(tests_dir)

    db = SessionLocal()
    try:
        for ext_num_str, cond in usloviya.items():
            try:
                ext_num = int(ext_num_str)
            except ValueError:
                continue
            task = db.query(Task).filter_by(external_number=ext_num).first()
            if not task:
                task = Task(
                    external_number=ext_num,
                    title=cond.get("title", f"Задача {ext_num}"),
                    description=cond.get("description", ""),
                    compare_mode="exact",
                    is_published=True,
                )
                db.add(task)
                db.flush()
            for i, ex in enumerate(cond.get("examples", [])):
                db.add(TaskExample(
                    task_id=task.id, order=i,
                    input=ex["input"], output=ex["output"],
                ))

            test_file = tests_root / f"{ext_num}.json"
            if test_file.exists():
                for i, t in enumerate(json.loads(test_file.read_text(encoding="utf-8"))):
                    db.add(TaskTest(
                        task_id=task.id, order=i,
                        input=t["input"], expected_output=t["output"],
                    ))
        db.commit()
        print("[import_legacy] импорт завершён")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m scripts.import_legacy <usloviya.json> <tests_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
