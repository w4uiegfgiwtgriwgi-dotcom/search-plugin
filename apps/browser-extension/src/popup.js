const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");
const projectSelect = document.querySelector("#project-select");
const collectButton = document.querySelector("#collect");
const refreshProjectsButton = document.querySelector("#refresh-projects");

function readVisiblePageInfo() {
  const meta = (name) => (
    document.querySelector(`meta[name="${name}"]`)?.getAttribute("content") ||
    document.querySelector(`meta[property="${name}"]`)?.getAttribute("content") ||
    ""
  );
  const author = meta("author") || meta("article:author") || "";
  const description = meta("description") || meta("og:description") || "";
  const cover = meta("og:image") || meta("twitter:image") || "";
  const published = meta("article:published_time") || meta("pubdate") || meta("date") || "";
  const siteName = meta("og:site_name") || meta("application-name") || location.hostname;
  return {
    title: document.title || meta("og:title") || "未命名页面",
    url: location.href,
    author_name: author,
    description,
    cover_url: cover,
    published_at: published,
    site_name: siteName
  };
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { "content-type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

async function loadProjects() {
  const previousProjectId = projectSelect.value;
  refreshProjectsButton.disabled = true;
  const projects = await fetchJson("/api/projects");
  projectSelect.innerHTML = [
    `<option value="">自动创建浏览器采集素材</option>`,
    ...projects.map((project) => `<option value="${project.id}">${project.name}</option>`)
  ].join("");
  if (previousProjectId && projects.some((project) => String(project.id) === previousProjectId)) {
    projectSelect.value = previousProjectId;
  }
  statusEl.textContent = projects.length ? "请选择项目后保存当前页面" : "没有项目时会自动创建浏览器采集素材";
  refreshProjectsButton.disabled = false;
}

async function savePageToLocalApi(pageInfo) {
  const projectId = Number(projectSelect.value || 0);
  const response = await fetch(`${apiBase}/api/browser/collect-page`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ ...pageInfo, project_id: projectId || null })
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

collectButton.addEventListener("click", async () => {
  collectButton.disabled = true;
  statusEl.textContent = "正在读取并保存当前页面";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readVisiblePageInfo
    });
    const saved = await savePageToLocalApi(result);
    statusEl.textContent = `已保存到项目：${saved.project.name}，素材 ${saved.material.id}`;
  } catch (error) {
    statusEl.textContent = `保存失败：${error.message || error}`;
  } finally {
    collectButton.disabled = false;
  }
});

refreshProjectsButton.addEventListener("click", () => {
  statusEl.textContent = "正在刷新项目列表";
  loadProjects().catch((error) => {
    refreshProjectsButton.disabled = false;
    statusEl.textContent = `本地 API 不可用：${error.message || error}`;
  });
});

loadProjects().catch((error) => {
  refreshProjectsButton.disabled = false;
  statusEl.textContent = `本地 API 不可用：${error.message || error}`;
});
