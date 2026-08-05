const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
function selectedPlatforms() {
  return Array.from(document.querySelectorAll("input[type='checkbox']:checked")).map((item) => item.value);
}
function renderResults(results) {
  resultsEl.innerHTML = results.map((item) => `
    <article class="result-card"><div class="source">${item.platform}</div><h2>${item.title}</h2><p>${item.description || "暂无描述"}</p><a href="${item.source_url}" target="_blank" rel="noreferrer">打开原链接</a></article>
  `).join("");
}
document.querySelector("#search").addEventListener("click", async () => {
  const query = document.querySelector("#query").value.trim();
  statusEl.textContent = "搜索中";
  resultsEl.innerHTML = "";
  try {
    const taskResponse = await fetch(`${apiBase}/api/search/tasks`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ query, platforms: selectedPlatforms() }) });
    const task = await taskResponse.json();
    const resultsResponse = await fetch(`${apiBase}/api/search/tasks/${task.id}/results`);
    const results = await resultsResponse.json();
    statusEl.textContent = `任务 ${task.id}：${task.status}，找到 ${results.length} 条`;
    renderResults(results);
  } catch (error) {
    statusEl.textContent = `本地 API 不可用：${error.message}`;
  }
});
