const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const projectSelect = document.querySelector("#project-select");
const apiPill = document.querySelector("#api-pill");
const stage2Output = document.querySelector("#stage2-output");
const librarySummary = document.querySelector("#library-summary");
const libraryList = document.querySelector("#library-list");
const libraryFilter = document.querySelector("#library-filter");
const librarySort = document.querySelector("#library-sort");
let currentTaskId = null;
let currentResults = [];
let currentAssetId = null;
let currentMatch = null;

function renderApiStatus(status) {
  if (!apiPill) return;
  const labels = {
    starting: "API 启动中",
    ready: status.owned ? "API 已自动启动" : "API 已连接",
    failed: "API 启动失败",
  };
  apiPill.textContent = labels[status.status] || "API 状态未知";
  apiPill.dataset.status = status.status || "unknown";
  if (status.error) {
    apiPill.title = status.error;
  }
}

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

async function uploadImage(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiBase}/api/assets/upload-image`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

function renderAsset(asset) {
  currentAssetId = asset.id;
  currentMatch = null;
  stage2Output.textContent = JSON.stringify({
    asset_id: asset.id,
    source_path: asset.source_path,
    size: `${asset.width || "?"}x${asset.height || "?"}`,
    ocr_text: asset.ocr_text,
    phash: asset.perceptual_hash,
    thumbnail_path: asset.thumbnail_path
  }, null, 2);
}

function readMatchOptions() {
  const threshold = Number(document.querySelector("#match-threshold").value || 0.75);
  const fps = Number(document.querySelector("#match-fps").value || 1);
  const refineFps = Number(document.querySelector("#refine-fps").value || 4);
  const refineWindowMs = Number(document.querySelector("#refine-window-ms").value || 1000);
  return {
    threshold: Math.min(Math.max(threshold, 0), 1),
    fps: Math.max(fps, 0.1),
    refine_fps: Math.max(refineFps, 0.1),
    refine_window_ms: Math.max(Math.round(refineWindowMs), 250)
  };
}

function renderMatch(match) {
  currentMatch = match;
  stage2Output.textContent = JSON.stringify({
    match_id: match.id,
    match_type: match.match_type,
    timestamp_ms: match.timestamp_ms,
    end_timestamp_ms: match.end_timestamp_ms,
    combined_score: match.combined_score,
    phash_score: match.phash_score,
    local_frame_path: match.local_frame_path,
    evidence: match.evidence_json
  }, null, 2);
}

function renderBatchMatches(batch) {
  currentMatch = batch.matches[0] || null;
  stage2Output.textContent = JSON.stringify({
    candidate_count: batch.candidate_count,
    match_count: batch.match_count,
    error_count: batch.error_count,
    matches: batch.matches.map((match) => ({
      match_id: match.id,
      candidate_video_path: match.candidate_video_path,
      match_type: match.match_type,
      timestamp_ms: match.timestamp_ms,
      combined_score: match.combined_score,
      local_frame_path: match.local_frame_path
    })),
    errors: batch.errors
  }, null, 2);
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

function renderLibrary(library) {
  if (!libraryList || !librarySummary) return;
  librarySummary.textContent = `共 ${library.total_count} 条：搜索收藏 ${library.search_result_count} 条，截图反查 ${library.frame_match_count} 条`;
  if (library.items.length === 0) {
    libraryList.innerHTML = `<p class="meta">当前项目还没有收藏素材</p>`;
    return;
  }
  libraryList.innerHTML = library.items.map((item) => {
    const kind = item.source_type === "frame_match" ? "截图反查" : "搜索收藏";
    const score = item.combined_score == null ? "" : `<p>匹配分：${item.combined_score}</p>`;
    const timestamp = item.selected_timestamp_ms == null ? "" : `<p>时间点：${item.selected_timestamp_ms}ms</p>`;
    const href = item.source_type === "frame_match" ? item.source_url : item.source_url;
    return `
      <article class="library-item">
        <div class="library-kind">${kind}</div>
        <h3>${item.title || "未命名素材"}</h3>
        <p>${item.note || "暂无备注"}</p>
        ${timestamp}
        ${score}
        <p>${(item.tags || []).join(" / ") || "未打标签"}</p>
        <a href="${href}" target="_blank" rel="noreferrer">打开素材来源</a>
      </article>
    `;
  }).join("");
}

async function refreshLibrary() {
  if (!projectSelect.value) {
    if (librarySummary) librarySummary.textContent = "等待选择项目";
    if (libraryList) libraryList.innerHTML = "";
    return null;
  }
  const params = new URLSearchParams({
    source_type: libraryFilter?.value || "all",
    review_status: "all",
    sort_by: librarySort?.value || "created_desc"
  });
  const library = await api(`/api/projects/${projectSelect.value}/library?${params.toString()}`);
  renderLibrary(library);
  return library;
}

function exportLibrary(fmt) {
  if (!projectSelect.value) {
    statusEl.textContent = "请先选择项目再导出素材";
    return;
  }
  const params = new URLSearchParams({
    source_type: libraryFilter?.value || "all",
    review_status: "all",
    sort_by: librarySort?.value || "created_desc"
  });
  window.open(`${apiBase}/api/projects/${projectSelect.value}/library.${fmt}?${params.toString()}`, "_blank");
}

async function refreshProjects() {
  const projects = await api("/api/projects");
  projectSelect.innerHTML = projects.map((project) => `<option value="${project.id}">${project.name}</option>`).join("");
  await refreshLibrary().catch(() => {});
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
  await refreshLibrary().catch(() => {});
  statusEl.textContent = `已收藏结果 ${resultId} 到项目 ${projectId}`;
}

async function saveCurrentMatch() {
  if (!currentMatch) {
    stage2Output.textContent = "请先完成一次匹配";
    return;
  }
  const projectId = projectSelect.value || (await ensureProject()).id;
  const material = await api(`/api/projects/${projectId}/frame-matches`, {
    method: "POST",
    body: JSON.stringify({
      match_id: currentMatch.id,
      tags: ["阶段2", "截图反查"],
      note: `截图反查匹配帧，时间点 ${currentMatch.timestamp_ms}ms`,
      review_status: "confirmed"
    })
  });
  stage2Output.textContent = JSON.stringify({
    saved: true,
    project_id: projectId,
    material_id: material.id,
    match_id: material.match_id,
    timestamp_ms: material.timestamp_ms,
    candidate_video_path: material.candidate_video_path,
    local_frame_path: material.local_frame_path
  }, null, 2);
  await refreshLibrary().catch(() => {});
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
    await refreshLibrary();
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

projectSelect.addEventListener("change", () => {
  refreshLibrary().catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${error.message}`;
  });
});

document.querySelector("#refresh-library").addEventListener("click", () => {
  refreshLibrary().catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${error.message}`;
  });
});

[libraryFilter, librarySort].forEach((control) => {
  control?.addEventListener("change", () => {
    refreshLibrary().catch((error) => {
      librarySummary.textContent = `项目素材刷新失败：${error.message}`;
    });
  });
});

document.querySelectorAll("button[data-library-export]").forEach((button) => {
  button.addEventListener("click", () => exportLibrary(button.dataset.libraryExport));
});

document.querySelector("#analyze-image").addEventListener("click", async () => {
  const imagePath = document.querySelector("#image-path").value.trim();
  if (!imagePath) {
    stage2Output.textContent = "请先填写截图路径";
    return;
  }
  try {
    const asset = await api("/api/assets/analyze-image", {
      method: "POST",
      body: JSON.stringify({ image_path: imagePath })
    });
    renderAsset(asset);
  } catch (error) {
    stage2Output.textContent = `截图分析失败：${error.message}`;
  }
});

document.querySelector("#upload-image").addEventListener("click", async () => {
  const file = document.querySelector("#image-file").files[0];
  if (!file) {
    stage2Output.textContent = "请先选择一张截图";
    return;
  }
  try {
    const asset = await uploadImage(file);
    renderAsset(asset);
  } catch (error) {
    stage2Output.textContent = `截图上传失败：${error.message}`;
  }
});

document.querySelector("#find-match").addEventListener("click", async () => {
  const videoPath = document.querySelector("#video-path").value.trim();
  if (!currentAssetId) {
    stage2Output.textContent = "请先分析截图";
    return;
  }
  if (!videoPath) {
    stage2Output.textContent = "请先填写候选视频路径";
    return;
  }
  try {
    const options = readMatchOptions();
    const match = await api("/api/matches/find", {
      method: "POST",
      body: JSON.stringify({ query_asset_id: currentAssetId, candidate_video_path: videoPath, ...options })
    });
    renderMatch(match);
  } catch (error) {
    stage2Output.textContent = `候选视频匹配失败：${error.message}`;
  }
});

document.querySelector("#find-batch-match").addEventListener("click", async () => {
  const paths = document.querySelector("#video-paths").value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  if (!currentAssetId) {
    stage2Output.textContent = "请先分析截图";
    return;
  }
  if (paths.length === 0) {
    stage2Output.textContent = "请先填写批量候选视频路径";
    return;
  }
  try {
    const options = readMatchOptions();
    const batch = await api("/api/matches/batch", {
      method: "POST",
      body: JSON.stringify({ query_asset_id: currentAssetId, candidate_video_paths: paths, ...options, top_k: 10 })
    });
    renderBatchMatches(batch);
  } catch (error) {
    stage2Output.textContent = `批量候选视频匹配失败：${error.message}`;
  }
});

document.querySelector("#save-current-match").addEventListener("click", async () => {
  try {
    await saveCurrentMatch();
  } catch (error) {
    stage2Output.textContent = `收藏匹配帧失败：${error.message}`;
  }
});

refreshProjects().catch(() => {
  statusEl.textContent = "本地 API 未启动，项目列表暂不可用";
});

if (window.vmf) {
  window.vmf.getApiStatus().then(renderApiStatus).catch(() => renderApiStatus({ status: "failed" }));
  window.vmf.onApiStatus(renderApiStatus);
}
