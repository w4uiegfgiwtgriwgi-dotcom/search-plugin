document.querySelector("#collect").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const [{ result }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => ({ title: document.title, url: location.href }) });
  document.querySelector("#status").textContent = `${result.title} 已读取`;
});
