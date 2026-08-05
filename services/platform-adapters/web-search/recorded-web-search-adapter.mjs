import fs from "node:fs/promises";

function pick(pattern, html) {
  const match = html.match(pattern);
  return match ? match[1].trim() : "";
}

export function parseRecordedWebSearch(html) {
  const articlePattern = /<article class="result" data-platform="([^"]+)">([\s\S]*?)<\/article>/g;
  const results = [];
  for (const match of html.matchAll(articlePattern)) {
    const platform = match[1];
    const body = match[2];
    results.push({
      platform,
      content_type: "web_page",
      title: pick(/<a class="title" href="[^"]+">([\s\S]*?)<\/a>/, body),
      source_url: pick(/<a class="title" href="([^"]+)">/, body),
      author_name: pick(/<span class="author">([\s\S]*?)<\/span>/, body),
      cover_url: pick(/<img class="cover" src="([^"]+)"\s*\/>/, body),
      published_at: pick(/<time datetime="([^"]+)">/, body),
      raw_metadata_json: { recorded_fixture: true }
    });
  }
  return results;
}

export async function loadRecordedWebSearch(filePath) {
  const html = await fs.readFile(filePath, "utf8");
  return parseRecordedWebSearch(html);
}
