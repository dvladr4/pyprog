"use strict";

let REPORT = { tasksById: {}, results: {}, commentsByTask: {}, isTeacher: false };

document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("report-data");
  if (el) {
    try {
      REPORT = Object.assign(
        { tasksById: {}, results: {}, commentsByTask: {}, isTeacher: false },
        JSON.parse(el.textContent || "{}")
      );
    } catch (e) {
      console.error("Не удалось разобрать report-data:", e);
    }
  }
});

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function openTab(evt, tabName) {
  const tabcontent = document.getElementsByClassName("tabcontent");
  for (let i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  const tablinks = document.getElementsByClassName("tablinks");
  for (let i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(tabName).style.display = "block";
  if (evt && evt.currentTarget) evt.currentTarget.className += " active";
}

function showCondition(taskNum) {
  const cond = REPORT.tasksById[String(taskNum)];
  if (!cond) return;

  let html = `<h3>Задача ${taskNum}: ${escapeHtml(cond.title)}</h3>
              <p><strong>Описание:</strong> ${escapeHtml(cond.description || "—")}</p>`;

  if (cond.examples && cond.examples.length) {
    html += `<h4>Примеры:</h4>`;
    cond.examples.forEach((ex, idx) => {
      html += `
        <div style="margin-bottom:15px;">
          <strong>Пример ${idx + 1}:</strong>
          <div style="display:flex;gap:10px;">
            <div style="flex:1;">
              <strong>Ввод:</strong>
              <div class="preformatted test-input">${escapeHtml(ex.input)}</div>
            </div>
            <div style="flex:1;">
              <strong>Вывод:</strong>
              <div class="preformatted expected-output">${escapeHtml(ex.output)}</div>
            </div>
          </div>
        </div>`;
    });
  }

  document.getElementById("conditionModalContent").innerHTML = html;
  document.getElementById("conditionModal").style.display = "block";
}

function renderCommentsForTest(taskNum) {
  const list = (REPORT.commentsByTask || {})[String(taskNum)] || [];
  if (!list.length) {
    return '<p class="muted">Комментариев пока нет.</p>';
  }
  let html = '<ul class="comments-list">';
  list.forEach(c => {
    html += `<li>
      <div class="comment-text">${escapeHtml(c.text)}</div>
      <div class="comment-meta">${escapeHtml(c.created_at || "")}</div>
    </li>`;
  });
  html += '</ul>';
  return html;
}

function renderCommentForm(submissionId) {
  // Показываем форму только учителю и только если есть submission_id.
  if (!REPORT.isTeacher || !submissionId) return "";
  const token = REPORT.csrfToken || "";
  return `
    <form method="post" action="/admin/comments" class="comment-form"
          style="margin-top:10px;">
      <input type="hidden" name="csrf_token" value="${token}">
      <input type="hidden" name="submission_id" value="${submissionId}">
      <textarea name="text" rows="3" required
                placeholder="Комментарий к решению…"></textarea>
      <button type="submit">Сохранить</button>
    </form>`;
}

function showTestDetails(taskNum, testIndex, submissionId) {
  const result = REPORT.results[String(taskNum)];
  if (!result) return;
  const test = result.tests[testIndex];
  if (!test) return;
  const cond = REPORT.tasksById[String(taskNum)] || {};

  const code = result.code || "# Код решения не найден.";

  let html = `
    <h3>Детали теста: Задача ${taskNum} — ${escapeHtml(cond.title || "")}, тест ${testIndex + 1}</h3>

    <div class="test-details">
      <details>
        <summary>📄 Показать код решения ученика</summary>
        <div class="solution-code" style="margin-top:10px;">${escapeHtml(code)}</div>
      </details>
    </div>

    <div class="test-details">
      <h4>Условие задачи:</h4>
      <p>${escapeHtml(cond.description || "—")}</p>
    </div>

    <div class="test-details">
      <h4>Входные данные:</h4>
      <div class="preformatted test-input">${escapeHtml(test.input)}</div>
    </div>

    <div class="output-comparison">
      <div class="output-box">
        <h4>Ожидаемый вывод:</h4>
        <div class="preformatted expected-output">${escapeHtml(test.expected_output)}</div>
      </div>
      <div class="output-box">
        <h4>Фактический вывод:</h4>
        ${test.error
          ? `<div class="preformatted error-output">${escapeHtml(test.error)}</div>`
          : `<div class="preformatted student-output">${escapeHtml(test.actual_output)}</div>`}
      </div>
    </div>

    <div class="test-details">
      <h4>Результат:
        ${test.passed
          ? '<span style="color:green;">✓ Тест пройден</span>'
          : '<span style="color:red;">✗ Тест не пройден</span>'}
        <span class="muted" style="font-weight:normal;margin-left:8px;">
          (${test.execution_ms || 0} мс)
        </span>
      </h4>
    </div>

    <div class="test-details">
      <h4>Комментарии учителя</h4>
      ${renderCommentsForTest(taskNum)}
      ${renderCommentForm(submissionId)}
    </div>`;

  document.getElementById("testModalContent").innerHTML = html;
  document.getElementById("testModal").style.display = "block";
}

function closeTestModal() {
  document.getElementById("testModal").style.display = "none";
}
function closeConditionModal() {
  document.getElementById("conditionModal").style.display = "none";
}

window.addEventListener("click", (event) => {
  const testModal = document.getElementById("testModal");
  const conditionModal = document.getElementById("conditionModal");
  if (event.target === testModal) testModal.style.display = "none";
  if (event.target === conditionModal) conditionModal.style.display = "none";
});