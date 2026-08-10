const apiBase = "http://127.0.0.1:17860";
const statusEl = document.querySelector("#status");

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

async function savePageToLocalApi(pageInfo) {
  const response = await fetch(`${apiBase}/api/browser/collect-page`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(pageInfo)
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

document.querySelector("#collect").addEventListener("click", async () => {
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
  }
});
