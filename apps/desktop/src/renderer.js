const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const projectSelect = document.querySelector("#project-select");
const apiPill = document.querySelector("#api-pill");
const stage2Output = document.querySelector("#stage2-output");
const librarySummary = document.querySelector("#library-summary");
const libraryList = document.querySelector("#library-list");
const libraryKeyword = document.querySelector("#library-keyword");
const libraryFilter = document.querySelector("#library-filter");
const libraryReviewFilter = document.querySelector("#library-review-filter");
const libraryRightsFilter = document.querySelector("#library-rights-filter");
const librarySort = document.querySelector("#library-sort");
const screenshotDropzone = document.querySelector("#screenshot-dropzone");
let currentTaskId = null;
let currentResults = [];
let currentAssetId = null;
let currentAssetIds = [];
let currentMatch = null;
let currentBulkMatches = [];

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
    throw new Error(await errorMessageFromResponse(response));
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

async function errorMessageFromResponse(response) {
  const text = await response.text();
  if (!text) return response.statusText;
  try {
    const payload = JSON.parse(text);
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) return payload.detail.map((item) => item.msg || JSON.stringify(item)).join("；");
  } catch {
    return text;
  }
  return text;
}

function friendlyError(error) {
  const message = error?.message || String(error);
  if (message === "Failed to fetch") return "本地 API 暂时不可用，请确认桌面端 API 已启动";
  return message;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[char]));
}

async function uploadImage(file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiBase}/api/assets/upload-image`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json();
}

async function uploadImages(files) {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  const response = await fetch(`${apiBase}/api/assets/upload-images`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json();
}

function isSupportedImageFile(file) {
  const suffix = (file.name || "").toLowerCase().split(".").pop();
  return file.type.startsWith("image/") || ["png", "jpg", "jpeg", "webp"].includes(suffix);
}

function renderBatchAssets(batch) {
  currentAssetIds = batch.assets.map((asset) => asset.id);
  currentAssetId = currentAssetIds[0] || null;
  currentMatch = null;
  currentBulkMatches = [];
  stage2Output.textContent = JSON.stringify({
    upload_count: batch.upload_count,
    asset_count: batch.asset_count,
    error_count: batch.error_count,
    current_asset_id: currentAssetId,
    assets: batch.assets.map((asset) => ({
      asset_id: asset.id,
      source_path: asset.source_path,
      size: `${asset.width || "?"}x${asset.height || "?"}`,
      ocr_text: asset.ocr_text,
      thumbnail_path: asset.thumbnail_path
    })),
    errors: batch.errors
  }, null, 2);
}

async function analyzeUploadedFiles(files, label = "截图") {
  const images = Array.from(files || []).filter(isSupportedImageFile);
  if (images.length === 0) {
    stage2Output.textContent = "请先选择一张 PNG/JPG/WebP 截图";
    return;
  }
  stage2Output.textContent = `${label}上传分析中，共 ${images.length} 张`;
  if (images.length === 1) {
    const asset = await uploadImage(images[0]);
    renderAsset(asset);
  } else {
    const batch = await uploadImages(images);
    renderBatchAssets(batch);
  }
}

function renderAsset(asset) {
  currentAssetId = asset.id;
  currentAssetIds = [asset.id];
  currentMatch = null;
  currentBulkMatches = [];
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
  currentBulkMatches = [match];
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
  currentBulkMatches = batch.matches;
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

function renderMultiAssetMatches(result) {
  currentMatch = result.best_matches[0] || null;
  currentBulkMatches = result.best_matches;
  stage2Output.textContent = JSON.stringify({
    asset_count: result.asset_count,
    batch_count: result.batch_count,
    error_count: result.error_count,
    best_matches: result.best_matches.map((match) => ({
      query_asset_id: match.query_asset_id,
      match_id: match.id,
      candidate_video_path: match.candidate_video_path,
      match_type: match.match_type,
      timestamp_ms: match.timestamp_ms,
      combined_score: match.combined_score,
      local_frame_path: match.local_frame_path
    })),
    batches: result.batches.map((batch) => ({
      query_asset_id: batch.query_asset_id,
      match_count: batch.match_count,
      error_count: batch.error_count,
      top_match: batch.matches[0] ? {
        match_id: batch.matches[0].id,
        candidate_video_path: batch.matches[0].candidate_video_path,
        timestamp_ms: batch.matches[0].timestamp_ms,
        combined_score: batch.matches[0].combined_score
      } : null
    })),
    errors: result.errors
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

function reviewStatusLabel(status) {
  return {
    pending: "待复核",
    confirmed: "已确认",
    rejected: "已拒绝"
  }[status] || "未知状态";
}

function rightsStatusLabel(status) {
  return {
    unknown: "未知",
    cleared: "可用",
    needs_permission: "需授权",
    blocked: "不可用"
  }[status] || "未知";
}

function renderLibrarySummary(library) {
  const summary = library.summary || {};
  const review = summary.by_review_status || {};
  const rights = summary.by_rights_status || {};
  librarySummary.innerHTML = `
    <div class="summary-grid">
      <span class="summary-chip">当前 ${library.total_count} / 全部 ${summary.all_count ?? library.total_count}</span>
      <span class="summary-chip">搜索 ${library.search_result_count}</span>
      <span class="summary-chip">截图 ${library.frame_match_count}</span>
      <span class="summary-chip">待复核 ${review.pending ?? 0}</span>
      <span class="summary-chip">已确认 ${review.confirmed ?? 0}</span>
      <span class="summary-chip">已拒绝 ${review.rejected ?? 0}</span>
      <span class="summary-chip">可用 ${rights.cleared ?? 0}</span>
      <span class="summary-chip">需授权 ${rights.needs_permission ?? 0}</span>
      <span class="summary-chip">不可用 ${rights.blocked ?? 0}</span>
    </div>
  `;
}

function renderLibrary(library) {
  if (!libraryList || !librarySummary) return;
  renderLibrarySummary(library);
  if (library.items.length === 0) {
    libraryList.innerHTML = `<p class="meta">当前项目还没有收藏素材</p>`;
    return;
  }
  libraryList.innerHTML = library.items.map((item) => {
    const kind = item.source_type === "frame_match" ? "截图反查" : "搜索收藏";
    const score = item.combined_score == null ? "" : `<p>匹配分：${item.combined_score}</p>`;
    const timeLabel = item.timecode || item.selected_timecode;
    const timestamp = item.selected_timestamp_ms == null ? "" : `<p>时间点：${timeLabel || ""} (${item.selected_timestamp_ms}ms)</p>`;
    const href = item.source_type === "frame_match" ? item.source_url : item.source_url;
    const note = item.note || "";
    const tags = item.tags || [];
    const reviewButtons = ["pending", "confirmed", "rejected"].map((status) => `
      <button
        class="review-button ${item.review_status === status ? "is-active" : ""}"
        data-review-source="${item.source_type}"
        data-review-material="${item.material_id}"
        data-review-status="${status}"
      >${reviewStatusLabel(status)}</button>
    `).join("");
    const rightsButtons = ["unknown", "cleared", "needs_permission", "blocked"].map((status) => `
      <button
        class="review-button ${item.rights_status === status ? "is-active" : ""}"
        data-rights-source="${item.source_type}"
        data-rights-material="${item.material_id}"
        data-rights-status="${status}"
      >${rightsStatusLabel(status)}</button>
    `).join("");
    return `
      <article class="library-item">
        <div class="library-kind">${kind}</div>
        <h3>${escapeHtml(item.title || "未命名素材")}</h3>
        <p>${escapeHtml(note || "暂无备注")}</p>
        ${timestamp}
        ${score}
        <p>状态：${reviewStatusLabel(item.review_status)}</p>
        <p>版权：${rightsStatusLabel(item.rights_status)}</p>
        <p>${escapeHtml(tags.join(" / ") || "未打标签")}</p>
        <div class="review-actions">${reviewButtons}</div>
        <div class="review-actions">${rightsButtons}</div>
        <div class="metadata-editor">
          <label>
            标签
            <input data-metadata-tags value="${escapeHtml(tags.join("，"))}" placeholder="多个标签用逗号分隔" />
          </label>
          <label>
            备注
            <textarea data-metadata-note placeholder="补充可用理由、版权风险或剪辑建议">${escapeHtml(note)}</textarea>
          </label>
          <button
            data-save-metadata
            data-metadata-source="${item.source_type}"
            data-metadata-material="${item.material_id}"
          >保存标签备注</button>
        </div>
        <a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">打开素材来源</a>
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
    keyword: libraryKeyword?.value.trim() || "",
    source_type: libraryFilter?.value || "all",
    review_status: libraryReviewFilter?.value || "all",
    rights_status: libraryRightsFilter?.value || "all",
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
    keyword: libraryKeyword?.value.trim() || "",
    source_type: libraryFilter?.value || "all",
    review_status: libraryReviewFilter?.value || "all",
    rights_status: libraryRightsFilter?.value || "all",
    sort_by: librarySort?.value || "created_desc"
  });
  window.open(`${apiBase}/api/projects/${projectSelect.value}/library.${fmt}?${params.toString()}`, "_blank");
}

async function updateLibraryReviewStatus(sourceType, materialId, reviewStatus) {
  if (!projectSelect.value) {
    statusEl.textContent = "请先选择项目再修改素材状态";
    return;
  }
  await api(`/api/projects/${projectSelect.value}/library/${sourceType}/${materialId}/review-status`, {
    method: "POST",
    body: JSON.stringify({ review_status: reviewStatus })
  });
  await refreshLibrary();
  statusEl.textContent = `已更新素材 ${materialId} 为${reviewStatusLabel(reviewStatus)}`;
}

async function updateLibraryRightsStatus(sourceType, materialId, rightsStatus) {
  if (!projectSelect.value) {
    statusEl.textContent = "请先选择项目再修改版权状态";
    return;
  }
  await api(`/api/projects/${projectSelect.value}/library/${sourceType}/${materialId}/rights-status`, {
    method: "POST",
    body: JSON.stringify({ rights_status: rightsStatus })
  });
  await refreshLibrary();
  statusEl.textContent = `已更新素材 ${materialId} 的版权状态为${rightsStatusLabel(rightsStatus)}`;
}

function parseTagInput(value) {
  return String(value || "")
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function updateLibraryMetadata(sourceType, materialId, tags, note) {
  if (!projectSelect.value) {
    statusEl.textContent = "请先选择项目再修改素材信息";
    return;
  }
  await api(`/api/projects/${projectSelect.value}/library/${sourceType}/${materialId}/metadata`, {
    method: "POST",
    body: JSON.stringify({ tags, note })
  });
  await refreshLibrary();
  statusEl.textContent = `已保存素材 ${materialId} 的标签和备注`;
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

async function saveHighScoreMatches() {
  const threshold = readMatchOptions().threshold;
  const matchIds = currentBulkMatches.filter((match) => Number(match.combined_score) >= threshold).map((match) => match.id);
  if (matchIds.length === 0) {
    stage2Output.textContent = `当前没有达到阈值 ${threshold} 的匹配结果`;
    return;
  }
  const projectId = projectSelect.value || (await ensureProject()).id;
  const result = await api(`/api/projects/${projectId}/frame-matches/batch`, {
    method: "POST",
    body: JSON.stringify({
      match_ids: matchIds,
      min_score: threshold,
      tags: ["阶段2", "高分匹配"],
      note: `批量高分匹配收藏，阈值 ${threshold}`,
      review_status: "confirmed"
    })
  });
  stage2Output.textContent = JSON.stringify({
    saved: true,
    project_id: projectId,
    requested_count: result.requested_count,
    saved_count: result.saved_count,
    skipped_count: result.skipped_count,
    error_count: result.error_count,
    skipped: result.skipped,
    errors: result.errors
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
    statusEl.textContent = `本地 API 不可用：${friendlyError(error)}`;
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
    statusEl.textContent = `创建项目失败：${friendlyError(error)}`;
  }
});

resultsEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-save-result]");
  if (!button) return;
  try {
    await saveResult(button.dataset.saveResult);
  } catch (error) {
    statusEl.textContent = `收藏失败：${friendlyError(error)}`;
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
    librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
  });
});

document.querySelector("#refresh-library").addEventListener("click", () => {
  refreshLibrary().catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
  });
});

[libraryFilter, libraryReviewFilter, libraryRightsFilter, librarySort].forEach((control) => {
  control?.addEventListener("change", () => {
    refreshLibrary().catch((error) => {
      librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
    });
  });
});

libraryKeyword?.addEventListener("input", () => {
  refreshLibrary().catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
  });
});

document.querySelectorAll("button[data-library-export]").forEach((button) => {
  button.addEventListener("click", () => exportLibrary(button.dataset.libraryExport));
});

libraryList?.addEventListener("click", async (event) => {
  const reviewButton = event.target.closest("button[data-review-status]");
  const rightsButton = event.target.closest("button[data-rights-status]");
  const metadataButton = event.target.closest("button[data-save-metadata]");
  if (!reviewButton && !rightsButton && !metadataButton) return;
  try {
    if (reviewButton) {
      await updateLibraryReviewStatus(
        reviewButton.dataset.reviewSource,
        reviewButton.dataset.reviewMaterial,
        reviewButton.dataset.reviewStatus
      );
      return;
    }
    if (rightsButton) {
      await updateLibraryRightsStatus(
        rightsButton.dataset.rightsSource,
        rightsButton.dataset.rightsMaterial,
        rightsButton.dataset.rightsStatus
      );
      return;
    }
    const item = metadataButton.closest(".library-item");
    await updateLibraryMetadata(
      metadataButton.dataset.metadataSource,
      metadataButton.dataset.metadataMaterial,
      parseTagInput(item.querySelector("[data-metadata-tags]")?.value),
      item.querySelector("[data-metadata-note]")?.value || ""
    );
  } catch (error) {
    librarySummary.textContent = `素材更新失败：${friendlyError(error)}`;
  }
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
    stage2Output.textContent = `截图分析失败：${friendlyError(error)}`;
  }
});

document.querySelector("#upload-image").addEventListener("click", async () => {
  const files = document.querySelector("#image-file").files;
  try {
    await analyzeUploadedFiles(files, "选择的截图");
  } catch (error) {
    stage2Output.textContent = `截图上传失败：${friendlyError(error)}`;
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
    stage2Output.textContent = `候选视频匹配失败：${friendlyError(error)}`;
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
    stage2Output.textContent = `批量候选视频匹配失败：${friendlyError(error)}`;
  }
});

document.querySelector("#find-multi-asset-match").addEventListener("click", async () => {
  const paths = document.querySelector("#video-paths").value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
  if (currentAssetIds.length === 0) {
    stage2Output.textContent = "请先上传或分析至少一张截图";
    return;
  }
  if (paths.length === 0) {
    stage2Output.textContent = "请先填写批量候选视频路径";
    return;
  }
  try {
    const options = readMatchOptions();
    const result = await api("/api/matches/batch-assets", {
      method: "POST",
      body: JSON.stringify({ query_asset_ids: currentAssetIds, candidate_video_paths: paths, ...options, top_k: 10 })
    });
    renderMultiAssetMatches(result);
  } catch (error) {
    stage2Output.textContent = `批量截图匹配失败：${friendlyError(error)}`;
  }
});

document.querySelector("#save-current-match").addEventListener("click", async () => {
  try {
    await saveCurrentMatch();
  } catch (error) {
    stage2Output.textContent = `收藏匹配帧失败：${friendlyError(error)}`;
  }
});

document.querySelector("#save-high-score-matches").addEventListener("click", async () => {
  try {
    await saveHighScoreMatches();
  } catch (error) {
    stage2Output.textContent = `收藏高分匹配失败：${friendlyError(error)}`;
  }
});

if (screenshotDropzone) {
  ["dragenter", "dragover"].forEach((eventName) => {
    screenshotDropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      screenshotDropzone.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    screenshotDropzone.addEventListener(eventName, () => {
      screenshotDropzone.classList.remove("is-dragover");
    });
  });
  screenshotDropzone.addEventListener("drop", async (event) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer?.files || []);
    try {
      await analyzeUploadedFiles(files, "拖入的截图");
    } catch (error) {
      stage2Output.textContent = `截图上传失败：${friendlyError(error)}`;
    }
  });
}

document.addEventListener("paste", async (event) => {
  const files = Array.from(event.clipboardData?.files || []).filter(isSupportedImageFile);
  if (files.length === 0) return;
  try {
    await analyzeUploadedFiles(files, "粘贴的截图");
  } catch (error) {
    stage2Output.textContent = `截图上传失败：${friendlyError(error)}`;
  }
});

refreshProjects().catch(() => {
  statusEl.textContent = "本地 API 未启动，项目列表暂不可用";
});

if (window.vmf) {
  window.vmf.getApiStatus().then(renderApiStatus).catch(() => renderApiStatus({ status: "failed" }));
  window.vmf.onApiStatus(renderApiStatus);
}
