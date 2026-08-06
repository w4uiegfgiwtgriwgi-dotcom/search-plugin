const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const projectSelect = document.querySelector("#project-select");
let currentTaskId = null;
let currentResults = [];

function selectedPlatforms() {
  return Array.from(document.querySelectorAll("input[type='checkbox']:checked")).map((item) => item.value);
}

async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { "content-type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

function renderResults(results) {
  currentResults = results;
  resultsEl.innerHTML = results.map((item) => `
    <article class="result-card">
      <div class="source">${item.platform}</div>
      <h2>${item.title}</h2>
      <p>${item.description || "暂无描述"}</p>
      <div class="meta">${item.author_name || "未知作者"} · ${item.published_at || "未知时间"}</div>
      <div class="card-actions">
        <a href="${item.source_url}" target="_blank" rel="noreferrer">打开原链接</a>
        <button data-save-result="${item.id}">收藏到项目</button>
      </div>
    </article>
  `).join("");
}

async function refreshProjects() {
  const projects = await api("/api/projects");
  projectSelect.innerHTML = projects.map((project) => `<option value="${project.id}">${project.name}</option>`).join("");
  return projects;
}

async function ensureProject() {
  let projects = await refreshProjects();
  if (projects.length === 0) {
    await api("/api/projects", { method: "POST", body: JSON.stringify({ name: "默认素材项目" }) });
    projects = await refreshProjects();
  }
  return projects[0];
}

async function saveResult(resultId) {
  const projectId = projectSelect.value || (await ensureProject()).id;
  await api(`/api/projects/${projectId}/materials`, {
    method: "POST",
    body: JSON.stringify({ result_id: Number(resultId), tags: ["阶段1"], note: "从搜索结果收藏" })
  });
  statusEl.textContent = `已收藏结果 ${resultId} 到项目 ${projectId}`;
}

document.querySelector("#search").addEventListener("click", async () => {
  const query = document.querySelector("#query").value.trim();
  statusEl.textContent = "搜索中";
  resultsEl.innerHTML = "";
  try {
    await ensureProject();
    const task = await api("/api/search/tasks", {
      method: "POST",
      body: JSON.stringify({ query, platforms: selectedPlatforms() })
    });
    currentTaskId = task.id;
    const results = await api(`/api/search/tasks/${task.id}/results`);
    statusEl.textContent = `任务 ${task.id}：${task.status}，找到 ${results.length} 条`;
    renderResults(results);
  } catch (error) {
    statusEl.textContent = `本地 API 不可用：${error.message}`;
  }
});

document.querySelector("#create-project").addEventListener("click", async () => {
  const name = document.querySelector("#project-name").value.trim() || "未命名项目";
  try {
    const project = await api("/api/projects", { method: "POST", body: JSON.stringify({ name }) });
    await refreshProjects();
    projectSelect.value = String(project.id);
    statusEl.textContent = `已创建项目：${project.name}`;
  } catch (error) {
    statusEl.textContent = `创建项目失败：${error.message}`;
  }
});

resultsEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-save-result]");
  if (!button) return;
  try {
    await saveResult(button.dataset.saveResult);
  } catch (error) {
    statusEl.textContent = `收藏失败：${error.message}`;
  }
});

document.querySelectorAll("button[data-export]").forEach((button) => {
  button.addEventListener("click", () => {
    if (!currentTaskId) {
      statusEl.textContent = "请先完成一次搜索再导出";
      return;
    }
    const fmt = button.dataset.export;
    window.open(`${apiBase}/api/exports/${currentTaskId}.${fmt}`, "_blank");
  });
});

refreshProjects().catch(() => {
  statusEl.textContent = "本地 API 未启动，项目列表暂不可用";
});
