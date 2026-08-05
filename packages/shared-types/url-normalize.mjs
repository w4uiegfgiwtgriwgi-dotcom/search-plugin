export function normalizeUrl(value) {
  const url = new URL(value);
  url.hash = "";
  url.protocol = url.protocol.toLowerCase();
  url.hostname = url.hostname.toLowerCase();
  if ((url.protocol === "https:" && url.port === "443") || (url.protocol === "http:" && url.port === "80")) {
    url.port = "";
  }
  const removable = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];
  for (const key of removable) url.searchParams.delete(key);
  url.searchParams.sort();
  return url.toString();
}
