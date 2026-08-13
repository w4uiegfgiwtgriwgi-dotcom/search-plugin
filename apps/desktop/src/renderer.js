const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const projectSelect = document.querySelector("#project-select");
const apiPill = document.querySelector("#api-pill");
const sourceStatusEl = document.querySelector("#source-status");
const stage2Output = document.querySelector("#stage2-output");
const librarySummary = document.querySelector("#library-summary");
const libraryList = document.querySelector("#library-list");
const libraryKeyword = document.querySelector("#library-keyword");
const libraryFilter = document.querySelector("#library-filter");
const libraryReviewFilter = document.querySelector("#library-review-filter");
const libraryRightsFilter = document.querySelector("#library-rights-filter");
const libraryConfidenceFilter = document.querySelector("#library-confidence-filter");
const librarySort = document.querySelector("#library-sort");
const showBrowserMaterialsButton = document.querySelector("#show-browser-materials");
const refreshBrowserMaterialsButton = document.querySelector("#refresh-browser-materials");
const screenshotDropzone = document.querySelector("#screenshot-dropzone");
const wechatQuery = document.querySelector("#wechat-query");
const wechatKeywords = document.querySelector("#wechat-keywords");
const wechatPlanOutput = document.querySelector("#wechat-plan-output");
const wechatManualUrl = document.querySelector("#wechat-manual-url");
const wechatManualTitle = document.querySelector("#wechat-manual-title");
let currentTaskId = null;
let currentResults = [];
let currentAssetId = null;
let currentAssetIds = [];
let currentMatch = null;
let currentBulkMatches = [];
let libraryActionFilter = "all";
let currentWechatPlan = null;
let platformStatus = new Map();

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

function selectedUnavailablePlatforms() {
  return selectedPlatforms().filter((platform) => {
    if (!["xiaohongshu", "douyin"].includes(platform)) return false;
    const session = platformStatus.get(platform)?.session || {};
    return session.status !== "available";
  });
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
  resultsEl.innerHTML = results.map((item) => {
    const metadata = item.raw_metadata_json || {};
    const percent = metadata.semantic_match_percent;
    const reasons = metadata.semantic_match_reasons || [];
    const warning = metadata.semantic_match_warning || "";
    const scoreHtml = percent == null ? "" : `
      <div class="match-score">
        <strong>匹配度 ${escapeHtml(percent)}%</strong>
        <span>${escapeHtml(reasons.join("；") || "等待人工复核")}</span>
      </div>
    `;
    return `
      <article class="result-card">
        <div class="source">${escapeHtml(item.platform)}</div>
        <h2>${escapeHtml(item.title)}</h2>
        <p>${escapeHtml(item.description || "暂无描述")}</p>
        ${scoreHtml}
        ${warning ? `<p class="match-warning">${escapeHtml(warning)}</p>` : ""}
        <div class="meta">${escapeHtml(item.author_name || "未知作者")} · ${escapeHtml(item.published_at || "未知时间")}</div>
        <div class="card-actions">
          <a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">打开原链接</a>
          <button data-save-result="${item.id}">收藏到项目</button>
        </div>
      </article>
    `;
  }).join("");
}

function renderSourceStatus(platforms) {
  platformStatus = new Map(platforms.map((item) => [item.platform, item]));
  if (!sourceStatusEl) return;
  const labels = {
    xiaohongshu: "小红书",
    douyin: "抖音",
  };
  const parts = ["xiaohongshu", "douyin"].map((platform) => {
    const session = platformStatus.get(platform)?.session || {};
    const available = session.status === "available";
    const text = `${labels[platform]}：${available ? "已配置" : "未配置"}`;
    const title = session.hint || session.command || "";
    return `<span class="source-chip ${available ? "is-ready" : "is-missing"}" title="${escapeHtml(title)}">${escapeHtml(text)}</span>`;
  });
  sourceStatusEl.innerHTML = `
    <span>真实候选源</span>
    ${parts.join("")}
    <span class="source-help">未配置时可先用公开网页/B站样本；真实搜索需安装对应 CLI。</span>
  `;
}

async function refreshPlatformStatus() {
  const platforms = await api("/api/platforms");
  renderSourceStatus(platforms);
  return platforms;
}

function renderWechatPlan(plan) {
  currentWechatPlan = plan;
  const searchTerms = plan.search_terms || [];
  const manualSteps = plan.manual_steps || [];
  const collectionSteps = plan.collection_steps || [];
  const boundaries = plan.safety_boundaries || [];
  wechatPlanOutput.innerHTML = `
    <div class="stage4-copy-grid">
      <div class="copy-box">
        <div class="copy-title">
          <strong>微信内搜索</strong>
          <button data-copy-block="wechat_search">复制</button>
        </div>
        <textarea readonly>${escapeHtml(plan.copy_blocks?.wechat_search || "")}</textarea>
      </div>
      <div class="copy-box">
        <div class="copy-title">
          <strong>网页辅助搜索</strong>
          <button data-copy-block="web_assist_search">复制</button>
        </div>
        <textarea readonly>${escapeHtml(plan.copy_blocks?.web_assist_search || "")}</textarea>
      </div>
    </div>
    <div class="stage4-list">
      <h3>候选搜索词</h3>
      ${searchTerms.map((term) => `<button class="term-button" data-copy-term="${escapeHtml(term)}">${escapeHtml(term)}</button>`).join("")}
    </div>
    <div class="stage4-columns">
      <div>
        <h3>人工搜索</h3>
        <ol>${manualSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
      </div>
      <div>
        <h3>采集回素材库</h3>
        <ol>${collectionSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
      </div>
    </div>
    <div class="safety-box">
      <h3>安全边界</h3>
      <ul>${boundaries.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      <p>${escapeHtml(plan.matching_hint || "")}</p>
    </div>
  `;
}

async function copyText(text) {
  const value = String(text || "");
  if (!value) return;
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

async function saveWechatManualLink() {
  const url = wechatManualUrl.value.trim();
  const title = wechatManualTitle.value.trim() || "视频号手动采集";
  if (!url) {
    wechatPlanOutput.textContent = "请先粘贴一个公开链接";
    return;
  }
  const projectId = projectSelect.value || (await ensureProject()).id;
  const collected = await api("/api/browser/collect-page", {
    method: "POST",
    body: JSON.stringify({
      url,
      title,
      project_id: Number(projectId),
      project_name: "视频号半自动素材",
      site_name: "微信视频号",
      description: "用户手动复制公开链接后保存",
    })
  });
  await refreshLibrary().catch(() => {});
  wechatPlanOutput.innerHTML = `
    <div class="safety-box">
      <h3>已保存</h3>
      <p>${escapeHtml(collected.result.title)} 已进入当前项目素材库。</p>
      <p>来源仍标记为用户主动采集，版权状态默认未知，使用前请人工复核。</p>
    </div>
  `;
  statusEl.textContent = "已保存视频号手动链接到当前项目";
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
  const confidence = summary.by_match_confidence || {};
  const usage = summary.by_usage_status || {};
  const timeline = library.timeline || [];
  const activeActionFilter = library.filters?.action_filter || "all";
  const actions = library.action_items || { counts: {} };
  const actionCounts = actions.counts || {};
  const actionTotal = (actionCounts.pending_review || 0) + (actionCounts.rights_attention || 0) + (actionCounts.low_confidence || 0);
  const actionFilterLabel = {
    pending_review: "待复核",
    rights_attention: "版权需处理",
    low_confidence: "低可信"
  }[activeActionFilter] || "";
  const actionHtml = actionTotal === 0 ? "" : `
    <div class="library-actions">
      <strong>待处理</strong>
      <button class="action-filter-button ${activeActionFilter === "pending_review" ? "is-active" : ""}" data-action-filter="pending_review">待复核 ${actionCounts.pending_review || 0}</button>
      <button class="action-filter-button ${activeActionFilter === "rights_attention" ? "is-active" : ""}" data-action-filter="rights_attention">版权需处理 ${actionCounts.rights_attention || 0}</button>
      <button class="action-filter-button ${activeActionFilter === "low_confidence" ? "is-active" : ""}" data-action-filter="low_confidence">低可信 ${actionCounts.low_confidence || 0}</button>
      ${activeActionFilter === "all" ? "" : `<button class="action-filter-button" data-action-filter="all">清除：${actionFilterLabel}</button>`}
      ${["pending_review", "rights_attention", "low_confidence"].flatMap((group) => actions[group] || []).slice(0, 6).map((item) => `
        <div class="action-item">
          <span>${escapeHtml(item.source_type_label || "")}</span>
          <span>${escapeHtml(item.timecode || item.review_status_label || item.rights_status_label || item.match_confidence_label || "")}</span>
          <span>${escapeHtml(item.title || "未命名素材")}</span>
          <span>${escapeHtml(item.suggested_next_step || item.action_reason || "")}</span>
        </div>
      `).join("")}
    </div>
  `;
  const timelineHtml = timeline.length === 0 ? "" : `
    <div class="library-timeline">
      ${timeline.slice(0, 8).map((item) => `
        <div class="timeline-item">
          <strong>${escapeHtml(item.timecode || "未知时间")}</strong>
          <span>${escapeHtml(item.duration_timecode || "未知时长")} · ${escapeHtml(item.match_confidence_label || "未知可信度")}</span>
          <span>${escapeHtml(item.title || "未命名素材")}</span>
        </div>
      `).join("")}
    </div>
  `;
  librarySummary.innerHTML = `
    <div class="summary-grid">
      <span class="summary-chip">当前 ${library.total_count} / 全部 ${summary.all_count ?? library.total_count}</span>
      <span class="summary-chip">搜索 ${library.search_result_count}</span>
      <span class="summary-chip">截图 ${library.frame_match_count}</span>
      <span class="summary-chip">高可信 ${confidence.high ?? 0}</span>
      <span class="summary-chip">中可信 ${confidence.medium ?? 0}</span>
      <span class="summary-chip">低可信 ${confidence.low ?? 0}</span>
      <span class="summary-chip">可交付 ${usage.ready ?? 0}</span>
      <span class="summary-chip">待确认 ${((usage.needs_review || 0) + (usage.rights_unknown || 0) + (usage.low_confidence || 0))}</span>
      <span class="summary-chip">待复核 ${review.pending ?? 0}</span>
      <span class="summary-chip">已确认 ${review.confirmed ?? 0}</span>
      <span class="summary-chip">已拒绝 ${review.rejected ?? 0}</span>
      <span class="summary-chip">可用 ${rights.cleared ?? 0}</span>
      <span class="summary-chip">需授权 ${rights.needs_permission ?? 0}</span>
      <span class="summary-chip">不可用 ${rights.blocked ?? 0}</span>
    </div>
    ${actionHtml}
    ${timelineHtml}
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
    const kind = item.source_type === "frame_match" ? "截图反查" : (item.collection_source_label || "搜索收藏");
    const score = item.combined_score == null ? "" : `<p>匹配分：${item.combined_score}</p>`;
    const confidence = item.match_confidence_label ? `<p>可信度：${escapeHtml(item.match_confidence_label)}</p>` : "";
    const browserMeta = item.platform === "browser-extension" ? `
      <p>站点：${escapeHtml(item.site_name || item.hostname || "未知站点")}</p>
      <p>作者：${escapeHtml(item.author_name || "未知作者")}</p>
      <p>发布时间：${escapeHtml(item.published_at || "未知时间")}</p>
    ` : "";
    const scoreDetails = item.phash_score == null ? "" : `
      <p>分数明细：pHash ${item.phash_score} / 视觉 ${item.visual_score} / 文字 ${item.text_score}</p>
    `;
    const evidence = item.evidence_summary ? `<p>证据：${escapeHtml(item.evidence_summary)}</p>` : "";
    const usageStatus = item.usage_status_label ? `<p>可用状态：${escapeHtml(item.usage_status_label)} · ${escapeHtml(item.usage_status_reason || "")}</p>` : "";
    const timeLabel = item.timecode || item.selected_timecode;
    const timestamp = item.selected_timestamp_ms == null ? "" : `<p>时间点：${timeLabel || ""} (${item.selected_timestamp_ms}ms)</p>`;
    const duration = item.duration_timecode ? `<p>时长：${item.duration_timecode} (${item.duration_ms}ms)</p>` : "";
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
        ${duration}
        ${score}
        ${confidence}
        ${browserMeta}
        ${usageStatus}
        ${scoreDetails}
        ${evidence}
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
    match_confidence: libraryConfidenceFilter?.value || "all",
    action_filter: libraryActionFilter,
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
    match_confidence: libraryConfidenceFilter?.value || "all",
    action_filter: libraryActionFilter,
    sort_by: librarySort?.value || "created_desc"
  });
  window.open(`${apiBase}/api/projects/${projectSelect.value}/library.${fmt}?${params.toString()}`, "_blank");
}

async function applyLibraryActionFilter(actionFilter) {
  libraryActionFilter = actionFilter || "all";
  await refreshLibrary();
  statusEl.textContent = libraryActionFilter === "all" ? "已清除待处理筛选" : "已切换到待处理素材";
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
    if (platformStatus.size === 0) {
      await refreshPlatformStatus().catch(() => {});
    }
    const unavailable = selectedUnavailablePlatforms();
    if (unavailable.length > 0) {
      statusEl.textContent = `已勾选 ${unavailable.join(" / ")}，但候选源未配置；请先运行 npm run stage6:check-sources`;
      return;
    }
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

document.querySelector("#build-wechat-plan")?.addEventListener("click", async () => {
  const fallbackQuery = document.querySelector("#query").value.trim();
  const query = wechatQuery.value.trim() || fallbackQuery;
  if (!query) {
    wechatPlanOutput.textContent = "请先输入画面描述、关键词、台词或视频线索";
    return;
  }
  wechatPlanOutput.textContent = "正在生成视频号人工搜索计划";
  try {
    const plan = await api("/api/wechat-channel/search-plan", {
      method: "POST",
      body: JSON.stringify({ query, keywords: parseTagInput(wechatKeywords.value) })
    });
    renderWechatPlan(plan);
    statusEl.textContent = "已生成视频号半自动搜索计划";
  } catch (error) {
    wechatPlanOutput.textContent = `视频号搜索计划生成失败：${friendlyError(error)}`;
  }
});

wechatPlanOutput?.addEventListener("click", async (event) => {
  const blockButton = event.target.closest("button[data-copy-block]");
  const termButton = event.target.closest("button[data-copy-term]");
  if (!blockButton && !termButton) return;
  try {
    const text = blockButton
      ? currentWechatPlan?.copy_blocks?.[blockButton.dataset.copyBlock]
      : termButton.dataset.copyTerm;
    await copyText(text);
    statusEl.textContent = "已复制视频号搜索词";
  } catch (error) {
    statusEl.textContent = `复制失败：${friendlyError(error)}`;
  }
});

document.querySelector("#save-wechat-manual-link")?.addEventListener("click", async () => {
  try {
    await saveWechatManualLink();
  } catch (error) {
    wechatPlanOutput.textContent = `视频号公开链接保存失败：${friendlyError(error)}`;
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
  libraryActionFilter = "all";
  refreshLibrary().catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
  });
});

document.querySelector("#refresh-library").addEventListener("click", () => {
  refreshLibrary().catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
  });
});

showBrowserMaterialsButton?.addEventListener("click", () => {
  if (libraryKeyword) libraryKeyword.value = "浏览器采集";
  if (libraryFilter) libraryFilter.value = "all";
  if (librarySort) librarySort.value = "created_desc";
  libraryActionFilter = "all";
  refreshLibrary().then((library) => {
    statusEl.textContent = `正在查看浏览器采集素材，共 ${library?.total_count ?? 0} 条`;
  }).catch((error) => {
    librarySummary.textContent = `浏览器采集素材刷新失败：${friendlyError(error)}`;
  });
});

refreshBrowserMaterialsButton?.addEventListener("click", () => {
  refreshLibrary().then((library) => {
    statusEl.textContent = `已刷新项目素材，当前 ${library?.total_count ?? 0} 条`;
  }).catch((error) => {
    librarySummary.textContent = `项目素材刷新失败：${friendlyError(error)}`;
  });
});

[libraryFilter, libraryReviewFilter, libraryRightsFilter, libraryConfidenceFilter, librarySort].forEach((control) => {
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

librarySummary?.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action-filter]");
  if (!button) return;
  applyLibraryActionFilter(button.dataset.actionFilter).catch((error) => {
    librarySummary.textContent = `待处理筛选失败：${friendlyError(error)}`;
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

refreshPlatformStatus().catch(() => {
  if (sourceStatusEl) sourceStatusEl.textContent = "候选源状态暂不可用";
});

refreshProjects().catch(() => {
  statusEl.textContent = "本地 API 未启动，项目列表暂不可用";
});

if (window.vmf) {
  window.vmf.getApiStatus().then(renderApiStatus).catch(() => renderApiStatus({ status: "failed" }));
  window.vmf.onApiStatus(renderApiStatus);
}
