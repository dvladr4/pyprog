# Регистрация моделей для Base.metadata.create_all
from app.models.user import User            # noqa: F401
from app.models.task import Task, TaskExample, TaskTest  # noqa: F401
from app.models.submission import Submission, TestResult  # noqa: F401
from app.models.comment import TeacherComment  # noqa: F401
