import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import { execFile, spawn } from "node:child_process";
import { Buffer } from "node:buffer";
import { URL } from "node:url";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import mysql from "mysql2/promise";

const execFileAsync = promisify(execFile);
const require = createRequire(import.meta.url);
const TorrentSearchApi = require("torrent-search-api");
const cheerio = require("cheerio");
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const config = {
  host: process.env.TORRENT_CLOUD_HOST || "0.0.0.0",
  port: Number(process.env.TORRENT_CLOUD_PORT || 9100),
  downloadsDir: process.env.DOWNLOADS_DIR || "/root/cloud-stack/downloads/torrent-cloud",
  aria2DownloadsDir: process.env.ARIA2_DOWNLOADS_DIR || "/downloads/torrent-cloud",
  aria2Rpc: process.env.ARIA2_RPC || "http://127.0.0.1:6800/jsonrpc",
  piHost: process.env.PI_HOST || "100.106.250.6",
  piStorage1: process.env.PI_STORAGE1 || "/mnt/storage1",
  piStorage2: process.env.PI_STORAGE2 || "/mnt/storage2",
  piMount1: process.env.PI_MOUNT1 || "/mnt/pi-storage1",
  piMount2: process.env.PI_MOUNT2 || "/mnt/pi-storage2",
  piDownloadsDir: process.env.PI_DOWNLOADS_DIR || "/mnt/pi-storage1/downloads/torrent-cloud",
  posterCacheDir: process.env.POSTER_CACHE_DIR || "/home/arduino/cloud-stack/downloads/.poster-cache",
  dbHost: process.env.DB_HOST || "127.0.0.1",
  dbPort: Number(process.env.DB_PORT || 3307),
  dbUser: process.env.DB_USER || "torrentcloud",
  dbPass: process.env.DB_PASS || "TorrentCloud@2026!",
  dbName: process.env.DB_NAME || "torrentcloud",
  searchProviders: process.env.TORRENT_SEARCH_PROVIDERS || "Nyaa,VPS",
  vpsSearchUrl: process.env.VPS_SEARCH_URL || "",
  vpsSearchToken: process.env.VPS_SEARCH_TOKEN || "",
  publicMode: process.env.TORRENT_CLOUD_PUBLIC === "1",
  cookieName: "tc_session"
};

let pool;
const memoryCache = new Map();

async function cachedValue(key, ttlMs, producer) {
  const now = Date.now();
  const hit = memoryCache.get(key);
  if (hit && hit.expires > now) return hit.value;
  if (hit?.promise) return hit.promise;
  const promise = Promise.resolve()
    .then(producer)
    .then((value) => {
      memoryCache.set(key, { value, expires: Date.now() + ttlMs });
      return value;
    })
    .catch((error) => {
      memoryCache.delete(key);
      throw error;
    });
  memoryCache.set(key, { promise, expires: now + ttlMs });
  return promise;
}

function clearCachePrefix(prefix) {
  for (const key of memoryCache.keys()) {
    if (key.startsWith(prefix)) memoryCache.delete(key);
  }
}

function htmlEscape(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function bytes(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), units.length - 1);
  return `${(n / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
}

function percentFree(free, total) {
  if (!total) return "";
  return `${Math.round((free / total) * 100)}% free`;
}

async function runCommand(command, args, timeout = 1800) {
  const { stdout } = await execFileAsync(command, args, {
    timeout,
    maxBuffer: 256 * 1024
  });
  return stdout.trim();
}

// ── Settings: LLM keys, custom providers, app settings ──────────────
const TANK_TERMINAL_BIN = "/home/arduino/tank-project/.venv/bin/python3";
const TANK_TERMINAL_SCRIPT = "/usr/local/bin/tankos-terminal";
const TANK_ENV_FILE = "/home/arduino/tank-project/.env";
const CUSTOM_PROVIDERS_FILE = "/home/arduino/tank-project/custom_providers.json";
const APP_SETTINGS_FILE = "/home/arduino/cloud-stack/app-settings.json";
const TANK_RESTART_UNITS = ["tankos-web", "tankos-web-embed"];

const APP_SETTINGS_DEFAULTS = {
  brandName: "TORRENT CLOUD",
  defaultProvider: "rotation",
  temperature: 0.7,
  maxTokens: 512,
  searchProviders: config.searchProviders,
  aria2Rpc: config.aria2Rpc,
  vpsSearchUrl: config.vpsSearchUrl
};

function readJsonFile(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

function appSettings() {
  return { ...APP_SETTINGS_DEFAULTS, ...readJsonFile(APP_SETTINGS_FILE, {}) };
}

function saveAppSettings(patch) {
  const next = { ...readJsonFile(APP_SETTINGS_FILE, {}), ...patch };
  fs.writeFileSync(APP_SETTINGS_FILE, JSON.stringify(next, null, 2), { mode: 0o600 });
  return next;
}

function updateEnvFile(updates) {
  // updates: { KEY: value } - empty string removes the key
  const text = fs.existsSync(TANK_ENV_FILE) ? fs.readFileSync(TANK_ENV_FILE, "utf8") : "";
  const NL = String.fromCharCode(10);
  const lines = text.split(NL);
  for (const key of Object.keys(updates)) {
    const idx = lines.findIndex((l) => new RegExp("^" + key + "=").test(l));
    if (updates[key]) {
      const line = key + "=" + updates[key];
      if (idx >= 0) lines[idx] = line; else lines.push(line);
    } else if (idx >= 0) {
      lines.splice(idx, 1);
    }
  }
  fs.writeFileSync(TANK_ENV_FILE, lines.join(NL), { mode: 0o600 });
}

async function runTankOs(args, timeout = 90000) {
  try {
    const out = await runCommand(TANK_TERMINAL_BIN, [TANK_TERMINAL_SCRIPT, ...args], timeout);
    return JSON.parse(out || "{}");
  } catch (error) {
    try { return JSON.parse(error.stdout || "{}"); } catch { return { ok: false, error: String(error.message || error) }; }
  }
}

async function restartTankTerminals() {
  const results = {};
  for (const unit of TANK_RESTART_UNITS) {
    try {
      await runCommand("sudo", ["-n", "systemctl", "restart", unit], 20000);
      results[unit] = "restarted";
    } catch (error) {
      results[unit] = "failed";
    }
  }
  return results;
}

async function localDiskSummary() {
  try {
    const { free, total } = await diskStats(config.downloadsDir);
    return `VPS ${bytes(free)} ${percentFree(free, total)}`;
  } catch {
    return "VPS unknown";
  }
}

async function diskStats(target) {
  const stat = await fs.promises.statfs(target);
  return {
    free: Number(stat.bavail) * Number(stat.bsize),
    total: Number(stat.blocks) * Number(stat.bsize)
  };
}

function parseDf(output) {
  const rows = output.split(/\r?\n/).slice(1).map((line) => line.trim().split(/\s+/)).filter((parts) => parts.length >= 6);
  return rows.map((parts) => {
    const total = Number(parts[1]) * 1024;
    const free = Number(parts[3]) * 1024;
    const mount = parts.slice(5).join(" ");
    return `${path.posix.basename(mount)} ${bytes(free)} ${percentFree(free, total)}`;
  }).join(" | ");
}

async function piStorageSummary() {
  try {
    const [one, two] = await Promise.all([
      diskStats(config.piMount1),
      diskStats(config.piMount2)
    ]);
    return `Pi mounted ${path.basename(config.piMount1)} ${bytes(one.free)} ${percentFree(one.free, one.total)} | ${path.basename(config.piMount2)} ${bytes(two.free)} ${percentFree(two.free, two.total)}`;
  } catch {
    // Fall through to direct Tailscale SSH if the SSHFS mount is not available.
  }
  try {
    const output = await runCommand("ssh", [
      "-o", "BatchMode=yes",
      "-o", "ConnectTimeout=5",
      "-o", "StrictHostKeyChecking=accept-new",
      `root@${config.piHost}`,
      `df -Pk ${config.piStorage1} ${config.piStorage2}`
    ], 7000);
    return `Pi ${parseDf(output) || "online"}`;
  } catch {
    return "Pi offline";
  }
}

async function syncSummary() {
  try {
    const state = await runCommand("systemctl", ["show", "-p", "ActiveState", "--value", "edulabs-sync-to-pi.service"], 1500);
    if (state === "active" || state === "activating") return "Sync running";
    if (state === "inactive") return "Sync idle";
    return `Sync ${state}`;
  } catch {
    return "Sync unknown";
  }
}

async function systemStatusHtml() {
  return cachedValue("system-status-html", 10000, async () => {
    const [local, pi, sync] = await Promise.all([
      localDiskSummary(),
      piStorageSummary(),
      syncSummary()
    ]);
    return `<div class="top-stats">
      <span>${htmlEscape(local)}</span>
      <span>${htmlEscape(pi)}</span>
      <span>${htmlEscape(sync)}</span>
    </div>`;
  });
}

const mediaTypes = new Map([
  [".mp4", "video/mp4"],
  [".m4v", "video/mp4"],
  [".webm", "video/webm"],
  [".mkv", "video/x-matroska"],
  [".mov", "video/quicktime"],
  [".avi", "video/x-msvideo"],
  [".mp3", "audio/mpeg"],
  [".m4a", "audio/mp4"],
  [".aac", "audio/aac"],
  [".ogg", "audio/ogg"],
  [".oga", "audio/ogg"],
  [".opus", "audio/ogg"],
  [".wav", "audio/wav"],
  [".flac", "audio/flac"]
]);

function mediaTypeFor(filePath) {
  return mediaTypes.get(path.extname(filePath).toLowerCase()) || "";
}

function isPlayableMedia(filePath) {
  return Boolean(mediaTypeFor(filePath));
}

function isSubtitleFile(filePath) {
  return [".srt", ".vtt"].includes(path.extname(filePath).toLowerCase());
}

function cleanMediaTitle(name) {
  return path.basename(name, path.extname(name))
    .replace(/\bS\d{1,4}E\d{1,4}\b|\bEP\d+\b|\bS\d{1,4}\b/ig, " ")
    .replace(/\b\d{2,4}p\b/ig, " ")
    .replace(/\s-\s\d{3,4}\b/ig, " ")
    .replace(/\b(x264|x265|h264|h265|hevc|web[-_. ]?dl|webrip|bluray|brrip|hdrip|dvdrip|aac|ddp\d?\.?\d?|atmos|proper|repack)\b/ig, " ")
    .replace(/\[[^\]]+\]|\([^)]+\)/g, " ")
    .replace(/[._-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function episodeLabel(fileName) {
  const base = path.basename(fileName, path.extname(fileName));
  const match = /\bS(\d{1,2})E(\d{1,2})\b/i.exec(base) || /\b(\d{1,2})x(\d{1,2})\b/i.exec(base);
  if (!match) return cleanMediaTitle(fileName) || base;
  return `S${match[1].padStart(2, "0")} E${match[2].padStart(2, "0")}`;
}

function posterSlug(title) {
  return crypto.createHash("sha1").update(title.toLowerCase()).digest("hex");
}

function subtitleLabel(fileName) {
  return path.basename(fileName, path.extname(fileName)).replace(/[._-]+/g, " ").trim() || fileName;
}

function streamLabel(stream, fallback) {
  return [stream.title, stream.language, stream.codec, stream.channels ? `${stream.channels}ch` : ""]
    .filter(Boolean)
    .join(" / ") || fallback;
}

async function subtitleTracksFor(user, mediaRelativePath) {
  const folder = parentRelative(mediaRelativePath);
  const mediaBase = path.basename(mediaRelativePath, path.extname(mediaRelativePath)).toLowerCase();
  const folderFull = absoluteFor(user, folder);
  const entries = await fs.promises.readdir(folderFull, { withFileTypes: true });
  const external = entries
    .filter((entry) => entry.isFile() && isSubtitleFile(entry.name))
    .map((entry) => {
      const rel = folder ? `${folder}/${entry.name}` : entry.name;
      const base = path.basename(entry.name, path.extname(entry.name)).toLowerCase();
      return {
        rel,
        external: true,
        label: subtitleLabel(entry.name),
        preferred: base === mediaBase || base.startsWith(`${mediaBase}.`) || base.startsWith(`${mediaBase}-`)
      };
    })
    .sort((a, b) => Number(b.preferred) - Number(a.preferred) || a.label.localeCompare(b.label));
  let embedded = [];
  try {
    const full = absoluteFor(user, mediaRelativePath);
    const probe = await probeMedia(full);
    embedded = probe.subtitles.map((stream) => ({
      stream: stream.globalIndex,
      external: false,
      label: streamLabel(stream, `Embedded subtitle ${stream.index + 1}`),
      preferred: Boolean(stream.default)
    }));
  } catch {
    embedded = [];
  }
  return [...external, ...embedded];
}

function srtToVtt(input) {
  return `WEBVTT\n\n${String(input)
    .replace(/^\uFEFF/, "")
    .replace(/\r+/g, "")
    .replace(/(\d{2}:\d{2}:\d{2}),(\d{3})/g, "$1.$2")
    .split("\n")
    .filter((line) => !/^\d+$/.test(line.trim()))
    .join("\n")}`;
}

function userSlug(username) {
  return username.toLowerCase().replace(/[^a-z0-9._-]/g, "_").slice(0, 48);
}

function cleanUsername(input) {
  const username = String(input || "").trim().toLowerCase();
  if (!/^[a-z0-9][a-z0-9._-]{1,47}$/.test(username)) {
    throw new Error("Use 2-48 characters: lowercase letters, numbers, dot, dash, underscore.");
  }
  return username;
}

function safeRelative(input) {
  const decoded = String(input || "").replaceAll("\\", "/");
  const normalized = path.posix.normalize(`/${decoded}`).slice(1);
  if (!normalized || normalized === ".") return "";
  if (normalized.startsWith("../") || normalized.includes("/../")) return "";
  return normalized;
}

function parentRelative(relativePath) {
  const parent = path.posix.dirname(relativePath);
  return parent === "." ? "" : parent;
}

function userRoot(user) {
  return path.resolve(config.downloadsDir, user.slug);
}

function userPiRoot(user) {
  return path.resolve(config.piDownloadsDir, user.slug);
}

function userReadRoots(user) {
  return [userRoot(user), userPiRoot(user)];
}

function aria2UserRoot(user) {
  return path.posix.join(config.aria2DownloadsDir, user.slug);
}

async function ensureUserDir(user) {
  const dir = userRoot(user);
  await fs.promises.mkdir(dir, { recursive: true, mode: 0o777 });
  await fs.promises.chmod(dir, 0o777);
  return dir;
}

function absoluteFor(user, relativePath) {
  const roots = userReadRoots(user);
  let fallback = "";
  for (const root of roots) {
    const full = path.resolve(root, relativePath);
    if (full !== root && !full.startsWith(root + path.sep)) {
      throw new Error("Invalid path");
    }
    fallback ||= full;
    if (fs.existsSync(full)) return full;
  }
  return fallback;
}

async function mergedEntries(user, relativePath) {
  const seen = new Map();
  for (const root of userReadRoots(user)) {
    const full = path.resolve(root, relativePath);
    if (full !== root && !full.startsWith(root + path.sep)) throw new Error("Invalid path");
    try {
      const entries = await fs.promises.readdir(full, { withFileTypes: true });
      for (const entry of entries) {
        if (!seen.has(entry.name)) seen.set(entry.name, entry);
      }
    } catch {
      // Missing/offline roots are allowed; local storage remains usable.
    }
  }
  return [...seen.values()].sort((a, b) => Number(b.isDirectory()) - Number(a.isDirectory()) || a.name.localeCompare(b.name));
}

function parseCookies(req) {
  const out = {};
  for (const part of String(req.headers.cookie || "").split(";")) {
    const index = part.indexOf("=");
    if (index > 0) out[part.slice(0, index).trim()] = decodeURIComponent(part.slice(index + 1).trim());
  }
  return out;
}

function send(res, status, body, headers = {}) {
  res.writeHead(status, {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    ...headers
  });
  res.end(body);
}

function redirect(res, location) {
  res.writeHead(303, { Location: location, "Cache-Control": "no-store" });
  res.end();
}

function collectBody(req, limit = 100 * 1024 * 1024) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error("Request too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

async function aria2(method, params = []) {
  const payload = { jsonrpc: "2.0", id: crypto.randomUUID(), method, params };
  const response = await fetch(config.aria2Rpc, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(`aria2 HTTP ${response.status}`);
  const data = await response.json();
  if (data.error) throw new Error(data.error.message || "aria2 error");
  return data.result;
}

const searchSecret = crypto.createHash("sha256").update(`${config.dbPass}:${config.cookieName}`).digest("hex");

function cleanQuery(input) {
  return String(input || "").replace(/\s+/g, " ").trim().slice(0, 120);
}

function configuredSearchProviders() {
  const available = new Map(TorrentSearchApi.getProviders().filter((provider) => provider.public).map((provider) => [provider.name.toLowerCase(), provider]));
  return config.searchProviders
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name) => {
      const lower = name.toLowerCase();
      if (lower === "nyaa") return { name: "Nyaa", public: true };
      if (lower === "vps") return { name: "VPS", public: true };
      return available.get(lower);
    })
    .filter(Boolean);
}

function activeSearchProviderNames() {
  return configuredSearchProviders().map((provider) => provider.name);
}

function searchProviderMap() {
  return new Map([["all", "All"], ...activeSearchProviderNames().map((name) => [name, name])]);
}

function setupTorrentSearchProviders() {
  TorrentSearchApi.disableAllProviders();
  for (const provider of activeSearchProviderNames()) {
    try {
      TorrentSearchApi.enableProvider(provider);
    } catch {
      // Broken provider modules are skipped at search time.
    }
  }
}

function encodeSearchPayload(torrent) {
  const payload = Buffer.from(JSON.stringify(torrent)).toString("base64url");
  const sig = crypto.createHmac("sha256", searchSecret).update(payload).digest("hex");
  return { payload, sig };
}

function decodeSearchPayload(payload, sig) {
  const expected = crypto.createHmac("sha256", searchSecret).update(payload).digest("hex");
  const given = Buffer.from(String(sig || ""));
  const wanted = Buffer.from(expected);
  if (given.length !== wanted.length || !crypto.timingSafeEqual(wanted, given)) {
    throw new Error("Invalid search result token");
  }
  return JSON.parse(Buffer.from(String(payload), "base64url").toString("utf8"));
}

function normalizeSearchResult(torrent) {
  return {
    ...torrent,
    title: torrent.title || torrent.name || "Untitled",
    size: torrent.size || "",
    seeds: torrent.seeds ?? "",
    peers: torrent.peers ?? "",
    pageUrl: torrent.desc || torrent.link || "",
    poster: torrent.poster || torrent.image || "",
    screenshots: torrent.screenshots || []
  };
}

function cleanProviderError(error) {
  const text = String(error?.stderr || error?.message || error || "").replace(/\s+/g, " ").trim();
  if (/cloudflare|Just a moment|challenge-platform|Enable JavaScript/i.test(text)) return "Provider is blocking the VPS with Cloudflare.";
  if (/ENOTFOUND|getaddrinfo/i.test(text)) return "Provider DNS failed from this VPS.";
  if (/timed out|timeout|ETIMEDOUT/i.test(text)) return "Provider timed out.";
  if (/ECONNREFUSED|ECONNRESET|EHOSTUNREACH|ENETUNREACH/i.test(text)) return "Provider network connection failed.";
  return text.slice(0, 180) || "Provider failed.";
}

async function searchProviderWithTimeout(provider, query, category) {
  const { stdout } = await execFileAsync(process.execPath, [
    path.join(__dirname, "torrent-search-worker.cjs"),
    "search",
    provider,
    query,
    category || "All",
    "12"
  ], {
    timeout: 12000,
    maxBuffer: 4 * 1024 * 1024,
    windowsHide: true
  });
  return JSON.parse(stdout || "[]").map(normalizeSearchResult);
}

async function probeMedia(fullPath) {
  return cachedValue(`probe:${fullPath}:${(await fs.promises.stat(fullPath)).mtimeMs}`, 5 * 60 * 1000, async () => {
    const { stdout } = await execFileAsync("ffprobe", [
      "-v", "error",
      "-print_format", "json",
      "-show_entries", "stream=index,codec_type,codec_name,channels,disposition:stream_tags=language,title",
      fullPath
    ], { maxBuffer: 4 * 1024 * 1024, timeout: 12000 });
    const data = JSON.parse(stdout || "{}");
    const streams = Array.isArray(data.streams) ? data.streams : [];
    const video = streams.find((stream) => stream.codec_type === "video") || null;
    const audio = streams.filter((stream) => stream.codec_type === "audio").map((stream, index) => ({
      index,
      globalIndex: stream.index,
      codec: stream.codec_name || "",
      channels: stream.channels || "",
      language: stream.tags?.language || "",
      title: stream.tags?.title || "",
      default: Boolean(stream.disposition?.default)
    }));
    const subtitles = streams.filter((stream) => stream.codec_type === "subtitle").map((stream, index) => ({
      index,
      globalIndex: stream.index,
      codec: stream.codec_name || "",
      language: stream.tags?.language || "",
      title: stream.tags?.title || "",
      default: Boolean(stream.disposition?.default)
    }));
    return { video, audio, subtitles };
  });
}

async function searchNyaa(query, category = "All") {
  const url = `https://nyaa.si/?f=0&c=0_0&q=${encodeURIComponent(query)}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  let html = "";
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
      }
    });
    html = await response.text();
  } finally {
    clearTimeout(timer);
  }
  const $ = cheerio.load(html);
  const results = [];
  $("tr.default").each((_, row) => {
    const $row = $(row);
    const title = $row.find("td:nth-child(2) a").last().text().trim();
    if (!title) return;
    const view = $row.find("a[href^='/view/']").attr("href") || "";
    const magnet = $row.find("a[href^='magnet:']").attr("href") || "";
    const thumb = $row.find("td:nth-child(1) img").attr("src") || "";
    results.push({
      title,
      size: $row.find("td:nth-child(4)").text().trim(),
      seeds: $row.find("td:nth-child(6)").text().trim(),
      peers: $row.find("td:nth-child(7)").text().trim(),
      magnet,
      poster: thumb && !/\/static\//.test(thumb) ? thumb : "",
      link: view ? `https://nyaa.si${view}` : "",
      provider: "Nyaa"
    });
  });
  return results.slice(0, 24);
}

async function searchVps(query, category = "All") {
  if (!config.vpsSearchUrl) return [];
  const token = config.vpsSearchToken ? `&token=${encodeURIComponent(config.vpsSearchToken)}` : "";
  const url = `${config.vpsSearchUrl}/api/search?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}${token}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`VPS search HTTP ${response.status}`);
    const data = await response.json();
    const results = [];
    for (const group of Array.isArray(data.groups) ? data.groups : []) {
      for (const item of Array.isArray(group.results) ? group.results : []) {
        results.push({ ...item, provider: item.provider || group.provider || "VPS" });
      }
    }
    return results.slice(0, 24);
  } catch (error) {
    throw new Error(`VPS search failed: ${error.message}`);
  } finally {
    clearTimeout(timer);
  }
}

async function fetchTrending() {
  if (!config.vpsSearchUrl) return { movies: [], tv: [] };
  const token = config.vpsSearchToken ? `?token=${encodeURIComponent(config.vpsSearchToken)}` : "";
  const url = `${config.vpsSearchUrl}/api/trending${token}`;
  return cachedValue("trending", 30 * 60 * 1000, async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`trending HTTP ${response.status}`);
      const data = await response.json();
      return {
        movies: Array.isArray(data.movies) ? data.movies : [],
        tv: Array.isArray(data.tv) ? data.tv : []
      };
    } finally {
      clearTimeout(timer);
    }
  }).catch(() => ({ movies: [], tv: [] }));
}

async function fetchTrailers() {
  if (!config.vpsSearchUrl) return [];
  const token = config.vpsSearchToken ? "?token=" + encodeURIComponent(config.vpsSearchToken) : "";
  const url = config.vpsSearchUrl + "/api/trailers" + token;
  return cachedValue("trailers", 30 * 60 * 1000, async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error("trailers HTTP " + response.status);
      const data = await response.json();
      return Array.isArray(data.trailers) ? data.trailers : [];
    } finally {
      clearTimeout(timer);
    }
  }).catch(() => []);
}

function normKey(s) {
  return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function findTrailer(trailers, title) {
  if (!trailers || !title) return null;
  const key = normKey(title);
  const keyTokens = key.split(" ").filter(Boolean);
  if (!keyTokens.length) return null;
  // exact normalized match first
  for (const t of trailers) {
    if (normKey(t.title) === key) return t;
  }
  // token-overlap fuzzy: >=60% of query tokens appear in a trailer title
  let best = null, bestScore = 0;
  for (const t of trailers) {
    const tTokens = normKey(t.title).split(" ").filter(Boolean);
    if (!tTokens.length) continue;
    const overlap = keyTokens.filter((tok) => tTokens.includes(tok)).length;
    const score = overlap / keyTokens.length;
    if (score >= 0.6 && score > bestScore) {
      bestScore = score;
      best = t;
    }
  }
  return best;
}

function trailerMap(trailers) {
  const map = new Map();
  for (const t of trailers || []) {
    const key = normKey(t.title);
    if (key && !map.has(key)) map.set(key, t);
  }
  return map;
}

function trailerButton(tr) {
  if (!tr || !tr.youtube_id) return "";
  const href = "https://www.youtube.com/watch?v=" + encodeURIComponent(tr.youtube_id);
  return '<a class="button trailer-btn" href="' + href + '" target="_blank" rel="noopener noreferrer" title="' + htmlEscape(tr.video_title || "Trailer") + '">▶ Trailer</a>';
}

function renderTrendingRail(trending, trailers = []) {
  const tmap = trailerMap(trailers);
  const shelf = (label, items, accent) => {
    if (!items.length) return "";
    const cards = items.map((it) => {
      const title = it.title || "Untitled";
      const letter = htmlEscape((title.replace(/^[^a-z0-9]+/i, "").charAt(0) || "?").toUpperCase());
      const size = it.size ? `<span class="muted">${htmlEscape(it.size)}</span>` : "";
      const seeds = it.seeds !== undefined && it.seeds !== "" ? `<span class="pill success">${htmlEscape(it.seeds)} seeds</span>` : "";
      const tr = findTrailer(trailers, title);
      return `<a class="media-card trend-card" href="/?q=${encodeURIComponent(title)}&provider=all&category=${encodeURIComponent(it.category || label)}" style="--accent:${accent}">
        <span class="poster">
          <img src="/poster?title=${encodeURIComponent(title)}" alt="" loading="lazy" onerror="this.remove()">
          <span>${letter}</span>
        </span>
        <span class="media-info">
          <span class="media-title">${htmlEscape(title)}</span>
          <span class="trend-meta">${size}${seeds}</span>
          <span class="row">${trailerButton(tr)}</span>
        </span>
      </a>`;
    }).join("");
    return `<section class="trending-shelf">
      <h2>${label}</h2>
      <div class="media-shelf horizontal">${cards}</div>
    </section>`;
  };
  return shelf("Trending Movies", trending.movies, "#8b5cf6")
       + shelf("Latest TV Shows", trending.tv, "#06b6d4");
}

async function readCpuTimes() {
  try {
    const raw = await fs.promises.readFile("/proc/stat", "utf8");
    const m = /^cpu\s+([\d\s]+)$/m.exec(raw);
    if (!m) return null;
    const parts = m[1].trim().split(/\s+/).map(Number);
    const idle = parts[3] + (parts[4] || 0);
    const total = parts.reduce((a, b) => a + b, 0);
    return { idle, total };
  } catch {
    return null;
  }
}

let _lastCpu = null;

async function systemInfo() {
  const cpu = await readCpuTimes();
  let cpuPct = 0;
  if (cpu && _lastCpu) {
    const dIdle = cpu.idle - _lastCpu.idle;
    const dTotal = cpu.total - _lastCpu.total;
    cpuPct = dTotal > 0 ? Math.round(((dTotal - dIdle) / dTotal) * 100) : 0;
  }
  _lastCpu = cpu;
  const memRaw = await fs.promises.readFile("/proc/meminfo", "utf8").catch(() => "");
  const mTotal = Number(/MemTotal:\s+(\d+)/.exec(memRaw)?.[1] || 0) * 1024;
  const mAvail = Number(/MemAvailable:\s+(\d+)/.exec(memRaw)?.[1] || 0) * 1024;
  const disk = await diskStats(config.downloadsDir).catch(() => ({ free: 0, total: 0 }));
  const tempRaw = await fs.promises.readFile("/sys/class/thermal/thermal_zone0/temp", "utf8").catch(() => "");
  const temp = tempRaw ? Math.round(Number(tempRaw) / 1000) : null;
  const uptimeRaw = await fs.promises.readFile("/proc/uptime", "utf8").catch(() => "");
  const uptime = uptimeRaw ? Math.round(Number(uptimeRaw.split(/\s+/)[0])) : 0;
  return {
    cpu: cpuPct,
    memTotal: mTotal,
    memAvail: mAvail,
    diskFree: disk.free,
    diskTotal: disk.total,
    temp,
    uptime,
    hostname: os.hostname()
  };
}

async function serviceState(name) {
  try {
    const out = await runCommand("systemctl", ["is-active", name], 3000);
    return (out || "").trim() || "inactive";
  } catch {
    return "inactive";
  }
}

async function dockerState(name) {
  try {
    const out = await runCommand("docker", ["inspect", "-f", "{{.State.Running}}", name], 3000);
    return (out || "").trim() === "true" ? "active" : "inactive";
  } catch {
    return "inactive";
  }
}

async function systemSnapshot() {
  const [info, cloud, aria2, vpn, tailscale, tankos, mariadb, tankosWeb] = await Promise.all([
    systemInfo(),
    serviceState("edulabs-torrent-cloud"),
    serviceState("docker"),
    serviceState("unoq-vpn"),
    serviceState("tailscaled"),
    serviceState("tankos-terminal.socket"),
    dockerState("torrent_cloud_db"),
    serviceState("tankos-web")
  ]);
  let tailscaleIp = "";
  let tailscaleName = "";
  try {
    const out = await runCommand("tailscale", ["status"], 3000).catch(() => "");
    const linesArr = String(out || "").split(String.fromCharCode(10));
    const line = linesArr.find((l) => /^100[.]/ .test(l) && l.indexOf("Logged out") === -1);
    if (line) {
      const parts = String(line).split(String.fromCharCode(32));
      if (parts.length >= 2) { tailscaleIp = parts[0]; tailscaleName = parts[1]; }
    }
  } catch {}
  let vpnIp = "";
  try {
    const out = await runCommand("ip", ["-4", "addr", "show", "dev", "tun0"], 3000).catch(() => "");
    const m = /inet\s+([\d.]+)/.exec(out || "");
    if (m) vpnIp = m[1];
  } catch {}
  return {
    ...info,
    services: {
      cloud, aria2, vpn, tailscale, tankos, mariadb, tankosWeb
    },
    tailscale: { ip: tailscaleIp, name: tailscaleName },
    vpnIp
  };
}

async function handleApiSystem(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (!config.vpsSearchToken || url.searchParams.get("token") !== config.vpsSearchToken) {
    send(res, 401, "Unauthorized", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }
  try {
    const data = await systemSnapshot();
    send(res, 200, JSON.stringify({ ok: true, ...data }), {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store"
    });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), {
      "Content-Type": "application/json; charset=utf-8"
    });
  }
}

async function handleApiService(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (!config.vpsSearchToken || url.searchParams.get("token") !== config.vpsSearchToken) {
    send(res, 401, "Unauthorized", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }
  const action = url.searchParams.get("action") || "";
  const target = url.searchParams.get("target") || "";
  const allowed = { vpn: "unoq-vpn", tailscale: "tailscaled" };
  const unit = allowed[target];
  if (!unit || !["start", "stop", "restart"].includes(action)) {
    send(res, 400, JSON.stringify({ ok: false, error: "bad action/target" }), {
      "Content-Type": "application/json; charset=utf-8"
    });
    return;
  }
  try {
    await runCommand("sudo", ["-n", "systemctl", action, unit], 15000);
    const state = await serviceState(unit);
    send(res, 200, JSON.stringify({ ok: true, action, target, state }), {
      "Content-Type": "application/json; charset=utf-8"
    });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), {
      "Content-Type": "application/json; charset=utf-8"
    });
  }
}

// ── TV Remote: ADB / WoL / network control ─────────────────────────
const TV_SETTINGS_FILE = "/home/arduino/cloud-stack/tv-settings.json";
const TV_SETTINGS_DEFAULTS = { tvIp: "", tvPort: "5555", tvMac: "", castApp: "youtube" };
function tvSettings() {
  try { return { ...TV_SETTINGS_DEFAULTS, ...JSON.parse(fs.readFileSync(TV_SETTINGS_FILE, "utf8")) }; }
  catch (e) { return { ...TV_SETTINGS_DEFAULTS }; }
}
function saveTvSettings(patch) {
  const next = { ...tvSettings(), ...patch };
  try {
    fs.mkdirSync("/home/arduino/cloud-stack", { recursive: true });
    fs.writeFileSync(TV_SETTINGS_FILE, JSON.stringify(next, null, 2), { mode: 0o600 });
    return next;
  } catch (error) { throw error; }
}
function adbTarget() {
  const s = tvSettings();
  return s.tvIp ? s.tvIp + ":" + (s.tvPort || "5555") : "";
}
async function adbShell(args) {
  if (!adbTarget()) throw new Error("No TV configured. Set IP in Remote settings.");
  await runCommand("adb", ["connect", adbTarget()], 8000);
  return runCommand("adb", ["-s", adbTarget(), "shell"].concat(args), 10000);
}
const TV_KEYS = {
  power: "26", poweroff: "223", home: "3", back: "4", menu: "82", search: "84",
  up: "19", down: "20", left: "21", right: "22", ok: "23", enter: "66",
  volup: "24", voldown: "25", mute: "164", chup: "166", chdown: "167",
  play: "85", pause: "127", ff: "90", rew: "89", stop: "86", next: "87", prev: "88",
  guide: "281", tvinput: "178", settings: "176", exit: "284"
};
function sendWol(mac) {
  const clean = String(mac || "").replace(/[^0-9a-fA-F]/g, "");
  if (clean.length !== 12) throw new Error("Invalid MAC address");
  const macBytes = clean.match(/.{2}/g).map(function (h) { return parseInt(h, 16); });
  const payload = [];
  for (let i = 0; i < 6; i++) payload.push(0xff);
  for (let i = 0; i < 16; i++) payload.push.apply(payload, macBytes);
  const packet = Buffer.from(payload);
  const dgram = require("dgram");
  const sock = dgram.createSocket("udp4");
  return new Promise(function (resolve, reject) {
    sock.send(packet, 0, packet.length, 9, "255.255.255.255", function (err) {
      sock.close();
      if (err) reject(err); else resolve({ sent: true, mac: mac });
    });
  });
}
async function discoverNetwork() {
  const out = await runCommand("/bin/sh", ["-c", "ip -4 route get 1 | awk '{print $7; exit}'"], 5000);
  const lanIp = out.trim();
  const parts = lanIp.split(".");
  if (parts.length !== 4) return [];
  const prefix = parts.slice(0, 3).join(".");
  const found = [];
  const tasks = [];
  for (let i = 1; i <= 254; i++) {
    const ip = prefix + "." + i;
    tasks.push(runCommand("ping", ["-c", "1", "-W", "1", ip], 2500).then(function () { found.push(ip); }).catch(function () {}));
    if (tasks.length >= 16) await Promise.all(tasks.splice(0));
  }
  await Promise.all(tasks);
  return found.sort();
}
async function speedTest() {
  const pingOut = await runCommand("ping", ["-c", "3", "-W", "2", "8.8.8.8"], 10000).catch(function () { return ""; });
  const ms = [];
  const re = /time=([\d.]+) ms/g;
  let m;
  while ((m = re.exec(pingOut)) !== null) ms.push(parseFloat(m[1]));
  const jitter = ms.length > 1 ? (Math.max.apply(null, ms) - Math.min.apply(null, ms)).toFixed(1) : "0";
  const bytes = 8 * 1024 * 1024;
  try {
    const t1 = Date.now();
    await runCommand("curl", ["-s", "-o", "/dev/null", "--max-time", "8", "-r", "0-" + (bytes - 1), "http://speedtest.tele2.net/8MB.zip"], 12000);
    const secs = (Date.now() - t1) / 1000;
    const avg = ms.length ? (ms.reduce(function (a, b) { return a + b; }, 0) / ms.length).toFixed(1) : null;
    return { ms: avg, jitter: jitter, downMbps: secs > 0 ? ((bytes * 8) / secs / 1e6).toFixed(1) : null };
  } catch (e) {
    const avg = ms.length ? (ms.reduce(function (a, b) { return a + b; }, 0) / ms.length).toFixed(1) : null;
    return { ms: avg, jitter: jitter, downMbps: null, note: "speedtest host unreachable" };
  }
}
async function handleApiTv(req, res) {
  const url = new URL(req.url, "http://" + req.headers.host);
  const action = url.pathname.split("/").pop();
  try {
    if (action === "settings" && req.method === "GET") {
      send(res, 200, JSON.stringify(Object.assign({ ok: true }, tvSettings())), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "settings" && req.method === "POST") {
      const body = await readBody(req);
      const patch = JSON.parse(body || "{}");
      const saved = saveTvSettings(patch);
      send(res, 200, JSON.stringify(Object.assign({ ok: true }, saved)), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "connect") {
      const body = await readBody(req);
      const data = JSON.parse(body || "{}");
      const target = (data.ip || tvSettings().tvIp) + ":" + (data.port || tvSettings().tvPort || "5555");
      const out = await runCommand("adb", ["connect", target], 10000);
      const online = /connected|already/.test(out);
      if (data.ip) saveTvSettings({ tvIp: String(data.ip), tvPort: String(data.port || tvSettings().tvPort || "5555") });
      send(res, 200, JSON.stringify({ ok: true, online: online, target: target, out: out }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "disconnect") {
      const target = adbTarget();
      const out = target ? await runCommand("adb", ["disconnect", target], 6000).catch(function () { return ""; }) : "no target";
      send(res, 200, JSON.stringify({ ok: true, out: out }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "key") {
      const body = await readBody(req);
      const data = JSON.parse(body || "{}");
      const code = TV_KEYS[data.key] || data.key;
      if (!code) throw new Error("Unknown key");
      const out = await adbShell(["input", "keyevent", String(code)]);
      send(res, 200, JSON.stringify({ ok: true, key: data.key, code: code, out: out }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "text") {
      const body = await readBody(req);
      const data = JSON.parse(body || "{}");
      const safe = String(data.text || "").replace(/[^A-Za-z0-9 .,!?@#%&*()_+=-]/g, "").replace(/ /g, "%s");
      const out = await adbShell(["input", "text", safe]);
      send(res, 200, JSON.stringify({ ok: true, out: out }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "wol") {
      const body = await readBody(req);
      const data = JSON.parse(body || "{}");
      const result = await sendWol(data.mac || tvSettings().tvMac);
      if (data.mac) saveTvSettings({ tvMac: String(data.mac) });
      send(res, 200, JSON.stringify(Object.assign({ ok: true }, result)), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "cast") {
      const body = await readBody(req);
      const data = JSON.parse(body || "{}");
      if (!data.url) throw new Error("Missing url");
      const pkg = data.app || tvSettings().castApp || "youtube";
      const safeUrl = String(data.url).replace(/[^A-Za-z0-9:/.?=&_%-]/g, "");
      const target = pkg === "youtube" ? "com.google.android.youtube.tv" : "org.chromium.chrome";
      const out = await adbShell(["am", "start", "-a", "android.intent.action.VIEW", "-d", safeUrl, target]);
      send(res, 200, JSON.stringify({ ok: true, url: safeUrl, out: out }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "discover") {
      const devices = await discoverNetwork();
      send(res, 200, JSON.stringify({ ok: true, devices: devices }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "ping") {
      const body = await readBody(req);
      const data = JSON.parse(body || "{}");
      const target = data.ip || tvSettings().tvIp;
      if (!target) throw new Error("No IP to ping");
      const out = await runCommand("ping", ["-c", "3", "-W", "2", String(target)], 10000).catch(function (e) { return "FAIL " + e.message; });
      const ms = [];
      const re = /time=([\d.]+) ms/g;
      let m;
      while ((m = re.exec(out)) !== null) ms.push(parseFloat(m[1]));
      const avg = ms.length ? (ms.reduce(function (a, b) { return a + b; }, 0) / ms.length).toFixed(1) : null;
      send(res, 200, JSON.stringify({ ok: true, target: target, out: String(out), avgMs: avg }), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "speed") {
      const result = await speedTest();
      send(res, 200, JSON.stringify(Object.assign({ ok: true }, result)), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    if (action === "status") {
      const s = tvSettings();
      let connected = false, model = "", androidVer = "";
      const target = adbTarget();
      if (target) {
        try {
          const list = await runCommand("adb", ["devices"], 5000);
          connected = list.indexOf(target.split(":")[0]) >= 0;
          if (connected) {
            model = await adbShell(["getprop", "ro.product.model"]).catch(function () { return ""; });
            androidVer = await adbShell(["getprop", "ro.build.version.release"]).catch(function () { return ""; });
          }
        } catch (e) { connected = false; }
      }
      send(res, 200, JSON.stringify(Object.assign({ ok: true }, s, { connected: connected, model: model, androidVer: androidVer })), { "Content-Type": "application/json; charset=utf-8" });
      return;
    }
    send(res, 404, JSON.stringify({ ok: false, error: "unknown tv action" }), { "Content-Type": "application/json; charset=utf-8" });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), { "Content-Type": "application/json; charset=utf-8" });
  }
}


async function searchTorrents(query, provider, category) {
  const cacheKey = `search:${provider}:${category}:${query.toLowerCase()}`;
  return cachedValue(cacheKey, 15 * 60 * 1000, async () => {
    setupTorrentSearchProviders();
    const providers = searchProviderMap();
    const selected = providers.has(provider) ? provider : "all";
    const categoryName = category || "All";
    const names = selected === "all" ? activeSearchProviderNames() : [selected];
    const searches = names.map(async (name) => {
      try {
        const results = name === "Nyaa" ? await searchNyaa(query, categoryName) : name === "VPS" ? await searchVps(query, categoryName) : await searchProviderWithTimeout(name, query, categoryName);
        return { provider: name, results };
      } catch (error) {
        return { provider: name, results: [], error: cleanProviderError(error) };
      }
    });
    return Promise.all(searches);
  });
}

function parseMultipart(buffer, contentType) {
  const match = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType || "");
  if (!match) return {};
  const boundary = Buffer.from(`--${match[1] || match[2]}`);
  const fields = {};
  let start = buffer.indexOf(boundary);
  while (start >= 0) {
    start += boundary.length;
    if (buffer[start] === 45 && buffer[start + 1] === 45) break;
    if (buffer[start] === 13 && buffer[start + 1] === 10) start += 2;
    const headerEnd = buffer.indexOf(Buffer.from("\r\n\r\n"), start);
    if (headerEnd < 0) break;
    const headers = buffer.slice(start, headerEnd).toString("utf8");
    const next = buffer.indexOf(boundary, headerEnd + 4);
    if (next < 0) break;
    let content = buffer.slice(headerEnd + 4, next);
    if (content.length >= 2 && content[content.length - 2] === 13 && content[content.length - 1] === 10) {
      content = content.slice(0, -2);
    }
    const name = /name="([^"]+)"/.exec(headers)?.[1];
    const filename = /filename="([^"]*)"/.exec(headers)?.[1] || "";
    if (name) fields[name] = { filename, content, text: content.toString("utf8") };
    start = next;
  }
  return fields;
}

async function initDb() {
  pool = mysql.createPool({
    host: config.dbHost,
    port: config.dbPort,
    user: config.dbUser,
    password: config.dbPass,
    database: config.dbName,
    waitForConnections: true,
    connectionLimit: 10
  });
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(64) NOT NULL UNIQUE,
      slug VARCHAR(64) NOT NULL UNIQUE,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS sessions (
      token CHAR(64) NOT NULL PRIMARY KEY,
      user_id BIGINT UNSIGNED NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      expires_at TIMESTAMP NOT NULL,
      KEY idx_sessions_user (user_id),
      CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS torrents (
      id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
      user_id BIGINT UNSIGNED NOT NULL,
      gid VARCHAR(32) NOT NULL,
      label VARCHAR(512) NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY uniq_gid (gid),
      KEY idx_torrents_user (user_id),
      CONSTRAINT fk_torrents_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  `);
}

async function getSessionUser(req) {
  const token = parseCookies(req)[config.cookieName];
  if (!token || !/^[a-f0-9]{64}$/.test(token)) return null;
  const [rows] = await pool.query(
    `SELECT u.id, u.username, u.slug
       FROM sessions s
       JOIN users u ON u.id = s.user_id
      WHERE s.token = ? AND s.expires_at > NOW()
      LIMIT 1`,
    [token]
  );
  return rows[0] || null;
}

async function createSession(username) {
  const clean = cleanUsername(username);
  const slug = userSlug(clean);
  await pool.query(
    "INSERT INTO users (username, slug) VALUES (?, ?) ON DUPLICATE KEY UPDATE username = VALUES(username)",
    [clean, slug]
  );
  const [[user]] = await pool.query("SELECT id, username, slug FROM users WHERE username = ? LIMIT 1", [clean]);
  await ensureUserDir(user);
  const token = crypto.randomBytes(32).toString("hex");
  await pool.query("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, DATE_ADD(NOW(), INTERVAL 30 DAY))", [token, user.id]);
  return token;
}

async function destroySession(req) {
  const token = parseCookies(req)[config.cookieName];
  if (token) await pool.query("DELETE FROM sessions WHERE token = ?", [token]);
}

function layout(user, content, statusHtml = "") {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>${htmlEscape(appSettings().brandName)}</title>
  <style>
    :root { color-scheme: dark; }
    * { box-sizing: border-box; }
    html { background: #05070f; }
    body { margin: 0; min-height: 100vh; font-family: 'Segoe UI', system-ui, -apple-system, Roboto, 'Helvetica Neue', Arial, sans-serif; background: #05070f; color: #e8ecf4; -webkit-font-smoothing: antialiased; animation: tvFade .45s ease; }
    @keyframes tvFade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    body::before { content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none; background:
      radial-gradient(900px 520px at 12% -8%, rgba(99,102,241,.17), transparent 60%),
      radial-gradient(820px 520px at 92% -4%, rgba(6,182,212,.13), transparent 55%),
      radial-gradient(1100px 700px at 50% 115%, rgba(168,85,247,.10), transparent 60%),
      #05070f; }
    .shell { display: flex; min-height: 100vh; }
    .rail { position: fixed; top: 0; bottom: 0; left: 0; width: 236px; display: flex; flex-direction: column; gap: 6px; padding: 22px 14px 16px; background: rgba(8,12,24,.88); border-right: 1px solid rgba(255,255,255,.06); backdrop-filter: blur(16px); z-index: 20; }
    .brand { display: flex; align-items: center; gap: 10px; padding: 4px 10px 18px; font-size: 17px; font-weight: 900; letter-spacing: .05em; color: #fff; }
    .brand::before { content: ""; width: 24px; height: 24px; flex: none; border-radius: 8px; background: linear-gradient(135deg, #6366f1, #06b6d4); box-shadow: 0 0 20px rgba(99,102,241,.65); }
    .brand span { color: #22d3ee; }
    nav { display: flex; flex-direction: column; gap: 3px; }
    .nav-item { display: flex; align-items: center; gap: 12px; padding: 11px 12px; border-radius: 11px; color: #97a1b5; font-weight: 650; font-size: 14px; text-decoration: none !important; transition: background .16s ease, color .16s ease, box-shadow .16s ease; }
    .nav-item svg { width: 19px; height: 19px; flex: none; }
    .nav-item:hover, .nav-item:focus-visible { background: rgba(99,102,241,.14); color: #fff; outline: none; box-shadow: inset 0 0 0 1.5px rgba(129,140,248,.55); }
    .rail-foot { margin-top: auto; display: grid; gap: 10px; padding: 14px 10px 4px; border-top: 1px solid rgba(255,255,255,.07); }
    .user { color: #8b95aa; font-size: 13px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .stage { flex: 1; margin-left: 236px; min-width: 0; display: flex; flex-direction: column; }
    header { position: sticky; top: 0; z-index: 10; background: rgba(5,7,15,.72); border-bottom: 1px solid rgba(255,255,255,.06); backdrop-filter: blur(14px); }
    .top-stats { display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap; padding: 12px 28px; min-width: 0; }
    .top-stats span { display: inline-flex; max-width: 100%; padding: 5px 12px; border-radius: 999px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.09); color: #b3bccf; font-size: 11px; font-weight: 800; letter-spacing: .04em; white-space: nowrap; }
    main { width: 100%; max-width: 1560px; margin: 0 auto; padding: 28px 30px 70px; overflow-x: hidden; }
    .grid { display: grid; grid-template-columns: minmax(340px, 430px) minmax(0, 1fr); gap: 18px; align-items: start; }
    .grid > *, .stack, section, .panel { min-width: 0; }
    section, .panel { background: linear-gradient(180deg, rgba(22,30,52,.78), rgba(13,18,33,.82)); border: 1px solid rgba(255,255,255,.07); border-radius: 16px; padding: 20px; box-shadow: 0 14px 44px rgba(0,0,0,.38); }
    h1 { margin: 0 0 10px; font-size: 24px; font-weight: 800; letter-spacing: -.01em; }
    h2 { margin: 0 0 14px; font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .09em; color: #8b95aa; }
    p { color: #9aa4b8; line-height: 1.55; }
    .stack { display: grid; gap: 18px; }
    form { display: grid; gap: 12px; }
    input[type=text], input[type=file], select { width: 100%; min-height: 44px; padding: 10px 14px; border: 1px solid rgba(255,255,255,.13); border-radius: 11px; background: rgba(9,13,26,.85); color: #e8ecf4; font: inherit; transition: border-color .15s ease, box-shadow .15s ease; }
    input[type=file] { border-style: dashed; color: #9aa4b8; }
    input[type=text]:focus, select:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.28); }
    button, .button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; padding: 10px 18px; border: 0; border-radius: 11px; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; font-weight: 800; font-size: 14px; cursor: pointer; text-decoration: none; box-shadow: 0 4px 18px rgba(99,102,241,.35); transition: transform .14s ease, box-shadow .14s ease, filter .14s ease; }
    button:hover, .button:hover, button:focus-visible, .button:focus-visible { transform: translateY(-1px); filter: brightness(1.1); box-shadow: 0 8px 28px rgba(99,102,241,.5); outline: none; }
    .button.secondary { background: rgba(255,255,255,.06); color: #dbe2ee; box-shadow: none; border: 1px solid rgba(255,255,255,.11); }
    .button.secondary:hover, .button.secondary:focus-visible { background: rgba(255,255,255,.11); filter: none; }
    .row { display: flex; gap: 10px; flex-wrap: wrap; }
    .table-scroll { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 11px 12px; border-bottom: 1px solid rgba(255,255,255,.06); vertical-align: top; }
    th { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #7d879c; }
    td { font-size: 14px; overflow-wrap: anywhere; color: #cdd5e3; }
    tr:hover td { background: rgba(255,255,255,.02); }
    a { color: #8ab4ff; text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; }
    .muted { color: #7d879c; }
    .break { overflow-wrap: anywhere; word-break: break-word; }
    .pill { display: inline-flex; align-items: center; padding: 4px 11px; border-radius: 999px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
    .active { background: rgba(16,185,129,.14); color: #34d399; border: 1px solid rgba(16,185,129,.35); }
    .complete { background: rgba(59,130,246,.14); color: #60a5fa; border: 1px solid rgba(59,130,246,.35); }
    .waiting, .paused { background: rgba(245,158,11,.14); color: #fbbf24; border: 1px solid rgba(245,158,11,.35); }
    .error { background: rgba(239,68,68,.14); color: #f87171; border: 1px solid rgba(239,68,68,.35); }
    .torrent-list { display: grid; gap: 12px; }
    .torrent-card { display: grid; gap: 10px; padding: 16px; border: 1px solid rgba(255,255,255,.07); border-radius: 14px; background: rgba(15,21,38,.62); min-width: 0; transition: border-color .15s ease, transform .15s ease; }
    .torrent-card:hover, .torrent-card:focus-within { border-color: rgba(129,140,248,.55); transform: translateY(-1px); }
    .torrent-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; min-width: 0; }
    .torrent-name { font-weight: 800; min-width: 0; overflow-wrap: anywhere; }
    .search-results { display: grid; gap: 12px; }
    .search-card { display: grid; grid-template-columns: 108px minmax(0, 1fr); gap: 16px; padding: 12px; border: 1px solid rgba(255,255,255,.07); border-radius: 14px; background: rgba(15,21,38,.62); min-width: 0; transition: border-color .15s ease, transform .15s ease; }
    .search-card:hover, .search-card:focus-within { border-color: rgba(129,140,248,.55); transform: translateY(-1px); }
    .search-poster { position: relative; display: grid; place-items: center; width: 108px; aspect-ratio: 2 / 3; border-radius: 10px; background: linear-gradient(135deg, #1e293b, #4338ca); color: #fff; font-size: 34px; font-weight: 900; overflow: hidden; box-shadow: 0 6px 18px rgba(0,0,0,.4); }
    .search-poster img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
    .search-poster span { position: relative; text-shadow: 0 2px 10px rgba(0,0,0,.5); }
    .search-info { display: grid; gap: 10px; min-width: 0; align-content: start; }
    .search-meta { display: flex; gap: 8px; flex-wrap: wrap; color: #8b95aa; font-size: 12px; font-weight: 700; }
    .shots { display: flex; gap: 6px; overflow-x: auto; }
    .shots img { width: 108px; height: 60px; border-radius: 8px; object-fit: cover; background: rgba(255,255,255,.06); }
    .media-shelf { display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: 20px; }
    .media-shelf.horizontal { grid-auto-flow: column; grid-auto-columns: 168px; overflow-x: auto; scroll-snap-type: x mandatory; padding: 4px 2px 12px; }
    .media-shelf.horizontal .media-card { scroll-snap-align: start; }
    .trending-shelf { margin-bottom: 18px; }
    .trending-shelf h2 { font-size: 20px; letter-spacing: .4px; margin-bottom: 10px; }
    .trend-card { text-decoration: none; color: inherit; }
    .trend-card .poster { box-shadow: 0 10px 26px rgba(0,0,0,.45); border: 1px solid color-mix(in srgb, var(--accent, #8b5cf6) 45%, transparent); }
    .trend-card:hover .poster { box-shadow: 0 14px 34px color-mix(in srgb, var(--accent, #8b5cf6) 35%, rgba(0,0,0,.5)); }
    .trend-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 12px; }
    .media-card { display: grid; gap: 10px; min-width: 0; padding: 10px; border: 1px solid rgba(255,255,255,.07); border-radius: 14px; background: rgba(15,21,38,.62); transition: border-color .16s ease, transform .16s ease; }
    .media-card:hover, .media-card:focus-within { border-color: rgba(129,140,248,.6); transform: translateY(-3px); }
    .poster { position: relative; display: grid; place-items: center; width: 100%; aspect-ratio: 2 / 3; overflow: hidden; border-radius: 10px; background: linear-gradient(135deg, #1e293b, #4338ca); color: #fff; font-size: 44px; font-weight: 900; box-shadow: 0 10px 26px rgba(0,0,0,.45); }
    .poster img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transition: transform .25s ease; }
    .media-card:hover .poster img { transform: scale(1.05); }
    .poster span { position: relative; text-shadow: 0 2px 12px rgba(0,0,0,.5); }
    .media-info { display: grid; gap: 8px; min-width: 0; }
    .media-title { font-weight: 900; overflow-wrap: anywhere; font-size: 14px; }
    .episode-list { display: grid; gap: 4px; max-height: 190px; overflow: auto; }
    .episode-list a { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 8px; padding: 6px 0; border-top: 1px solid rgba(255,255,255,.06); font-size: 12px; min-width: 0; color: #cdd5e3; }
    .episode-list a:hover { color: #fff; }
    .episode-list small { color: #7d879c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .stat { padding: 10px 12px; border-radius: 10px; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.05); min-width: 0; }
    .stat span { display: block; color: #7d879c; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
    .stat strong { display: block; margin-top: 3px; font-size: 13px; overflow-wrap: anywhere; }
    .progress { height: 8px; background: rgba(255,255,255,.08); border-radius: 999px; overflow: hidden; min-width: 0; }
    .progress span { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #6366f1, #06b6d4); box-shadow: 0 0 12px rgba(6,182,212,.55); }
    .notice { margin-bottom: 16px; padding: 12px 14px; border-radius: 11px; background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); color: #34d399; font-weight: 700; }
    .settings-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 18px; }
    .settings-tab { padding: 12px 22px; border-radius: 999px; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.05); color: #aab3c7; font-weight: 800; font-size: 14px; cursor: pointer; transition: all .16s ease; }
    .settings-tab:hover, .settings-tab:focus-visible { background: rgba(99,102,241,.18); color: #fff; border-color: rgba(129,140,248,.6); }
    .settings-tab.active { background: linear-gradient(135deg, #6366f1, #06b6d4); color: #fff; border-color: transparent; box-shadow: 0 6px 22px rgba(99,102,241,.45); }
    .settings-tabpane { display: none; }
    .settings-tabpane.active { display: block; animation: tvFade .3s ease; }
    .provider-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
    .provider-card { display: grid; gap: 10px; transition: transform .16s ease, box-shadow .16s ease; }
    .provider-card:hover { transform: translateY(-2px); box-shadow: 0 18px 50px rgba(0,0,0,.45); }
    .provider-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .provider-name { font-weight: 900; font-size: 16px; text-transform: capitalize; }
    .provider-base { color: #7d879c; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .provider-result { min-height: 16px; font-size: 12px; overflow-wrap: anywhere; }
    .provider-result.ok { color: #34d399; }
    .provider-result.err { color: #f87171; }
    .dev-group { display: grid; gap: 8px; margin-bottom: 16px; }
    .dev-row { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 11px; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.06); }
    .dev-row .dot { width: 10px; height: 10px; flex: none; border-radius: 999px; background: #10b981; box-shadow: 0 0 10px rgba(16,185,129,.7); }
    .dev-row .dot.off { background: #f87171; box-shadow: 0 0 10px rgba(248,113,113,.7); }
    .dev-row .dev-name { font-weight: 700; font-size: 13px; overflow-wrap: anywhere; }
    .dev-row .dev-path { color: #7d879c; font-size: 11px; margin-left: auto; flex: none; }
    .settings-form { display: grid; gap: 14px; max-width: 720px; }
    .form-row { display: grid; gap: 6px; }
    .form-row label { color: #7d879c; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
    .form-row input, .form-row select { width: 100%; padding: 11px 13px; border-radius: 11px; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.05); color: #e8ecf4; font-size: 14px; }
    .form-row input:focus, .form-row select:focus { border-color: rgba(129,140,248,.65); outline: none; }
    .toast { position: fixed; bottom: 24px; right: 24px; z-index: 99; padding: 12px 18px; border-radius: 12px; background: #0f172a; border: 1px solid rgba(52,211,153,.5); color: #34d399; font-weight: 700; font-size: 13px; box-shadow: 0 10px 30px rgba(0,0,0,.5); animation: tvFade .25s ease; }
    .toast.err { border-color: rgba(248,113,113,.5); color: #f87171; }
    .custom-list { display: grid; gap: 8px; margin-top: 16px; }
    .player { width: 100%; max-height: calc(100vh - 190px); background: #05070b; border-radius: 14px; display: block; border: 1px solid rgba(255,255,255,.07); }
    .player.audio { background: rgba(9,13,26,.85); padding: 16px; }
    .media-controls { display: grid; grid-template-columns: repeat(2, minmax(0, 220px)); gap: 12px; margin-top: 14px; }
    .control-field { display: grid; gap: 6px; }
    .control-field label { color: #7d879c; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .actions .button { min-height: 40px; border-radius: 999px; }
    .login { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
    .login .panel { width: min(440px, 100%); padding: 30px; text-align: center; }
    .login .panel h1 { background: linear-gradient(135deg, #a5b4fc, #22d3ee); -webkit-background-clip: text; background-clip: text; color: transparent; }
    .login .panel p { font-size: 14px; }
    a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid rgba(129,140,248,.75); outline-offset: 2px; border-radius: 8px; }
    @media (max-width: 980px) { .rail { width: 200px; } .stage { margin-left: 200px; } main { padding: 20px; } .grid { grid-template-columns: 1fr; } .top-stats { justify-content: flex-start; padding: 12px 20px; } .stats, .media-controls { grid-template-columns: 1fr; } }
    @media (max-width: 640px) { .rail { display: none; } .stage { margin-left: 0; } .media-shelf { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); } }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,.14); border-radius: 999px; border: 2px solid #05070f; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.24); }
  </style>
</head>
<body>
${user ? `<div class="shell">
<aside class="rail">
  <div class="brand">${(() => { const b = appSettings().brandName || "TORRENT CLOUD"; const parts = String(b).split(/\s+/); return parts.length > 1 ? parts.slice(0, -1).join(" ") + `<span>${parts[parts.length - 1]}</span>` : `<span>${parts[0]}</span>`; })()}</div>
  <nav>
    <a class="nav-item" href="/"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>Home</a>
    <a class="nav-item" href="#torrent-search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>Search</a>
    <a class="nav-item" href="#current-downloads"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m6 11 6 6 6-6"/><path d="M4 21h16"/></svg>Downloads</a>
    <a class="nav-item" href="#add-torrent"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14"/><path d="M5 12h14"/></svg>Add Torrent</a>
    <a class="nav-item" href="http://127.0.0.1:8082" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 3h8v8"/><path d="m21 3-9.5 9.5"/><path d="M19 13v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h7"/></svg>AriaNg</a>
    <a class="nav-item" href="http://213.199.61.156:9200/" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18"/><path d="M3 12h18"/><path d="M3 17h18"/></svg>Library</a>
    <a class="nav-item" href="/control"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="M2 12h3"/><path d="M19 12h3"/><path d="m4.9 4.9 2.1 2.1"/><path d="m17 17 2.1 2.1"/><path d="m19.1 4.9-2.1 2.1"/><path d="m7 17-2.1 2.1"/></svg>Control</a>
    <a class="nav-item" href="/remote"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><rect x="9" y="6" width="6" height="2" rx="1"/><path d="M9.5 17h.01"/><path d="M12 17h.01"/><path d="M14.5 17h.01"/><path d="M9.5 14h.01"/><path d="M12 14h.01"/><path d="M14.5 14h.01"/></svg>Remote</a>
    <a class="nav-item" href="/settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>Settings</a>
  </nav>
  <div class="rail-foot">
    <div class="user">${htmlEscape(user.username)}</div>
    <a class="button secondary" href="/logout">Logout</a>
  </div>
</aside>
<div class="stage">
<header>${statusHtml}</header>
${content}
</div>
</div>` : content}
<script>
(function () {
  var FOCUSABLE = 'a[href], button:not([disabled]), input[type=text], select, [tabindex]:not([tabindex="-1"])';
  function isTyping(el) { return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT"); }
  function isVisible(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  document.addEventListener("keydown", function (e) {
    var dir = e.key;
    if (dir !== "ArrowUp" && dir !== "ArrowDown" && dir !== "ArrowLeft" && dir !== "ArrowRight") return;
    var active = document.activeElement;
    if (isTyping(active)) return;
    e.preventDefault();
    var els = Array.prototype.filter.call(document.querySelectorAll(FOCUSABLE), isVisible);
    if (!els.length) return;
    var cur = (active && els.indexOf(active) !== -1) ? active : els[0];
    var cr = cur.getBoundingClientRect();
    var cx = cr.left + cr.width / 2, cy = cr.top + cr.height / 2;
    var best = null, bestScore = Infinity;
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el === cur) continue;
      var r = el.getBoundingClientRect();
      var dx = (r.left + r.width / 2) - cx;
      var dy = (r.top + r.height / 2) - cy;
      var ok = false, score = 0;
      if (dir === "ArrowRight") { ok = dx > 6 && Math.abs(dy) < Math.max(r.height, cr.height) * 0.65; score = Math.abs(dy) + dx; }
      else if (dir === "ArrowLeft") { ok = dx < -6 && Math.abs(dy) < Math.max(r.height, cr.height) * 0.65; score = Math.abs(dy) - dx; }
      else if (dir === "ArrowDown") { ok = dy > 6 && Math.abs(dx) < Math.max(r.width, cr.width) * 0.65; score = Math.abs(dx) + dy; }
      else if (dir === "ArrowUp") { ok = dy < -6 && Math.abs(dx) < Math.max(r.width, cr.width) * 0.65; score = Math.abs(dx) - dy; }
      if (!ok) continue;
      if (score < bestScore) { bestScore = score; best = el; }
    }
    if (best) best.focus();
  });
})();
</script>
</body>
</html>`;
}

function renderLogin(error = "") {
  return layout(null, `<main class="login">
  <section class="panel">
    <h1>Torrent Cloud</h1>
    <p>Passwordless user login. Enter a username to create or open your private torrent space.</p>
    ${error ? `<div class="notice">${htmlEscape(error)}</div>` : ""}
    <form method="post" action="/login">
      <input type="text" name="username" autocomplete="username" placeholder="username" autofocus>
      <button type="submit">Continue</button>
    </form>
  </section>
</main>`);
}

function renderSearchResults(groups, query = "") {
  if (!query) return "";
  const providerBlocks = groups.map((group) => {
    const notices = group.error ? `<p class="muted">${htmlEscape(group.error)}</p>` : "";
    const cards = group.results.map((item) => {
      const cleanQuery = (query || "").trim();
      const cleanQueryOk = /^[\w' -]{2,40}$/.test(cleanQuery) && !/\b\d{2,4}p\b/i.test(cleanQuery);
      const posterTitle = cleanQueryOk ? cleanQuery : item.title;
      const posterSrc = item.poster || `/poster?title=${encodeURIComponent(posterTitle)}`;
      const letter = htmlEscape(((item.title || "?").replace(/^[^a-z0-9]+/i, "").charAt(0) || "?").toUpperCase());
      const poster = `<div class="search-poster"><img src="${htmlEscape(posterSrc)}" alt="" loading="lazy" onerror="this.remove()"><span>${letter}</span></div>`;
      const shots = item.screenshots?.length ? `<div class="shots">${item.screenshots.map((src) => `<img src="${htmlEscape(src)}" alt="" loading="lazy" onerror="this.remove()">`).join("")}</div>` : "";
      const token = encodeSearchPayload(item);
      return `<article class="search-card">
        ${poster}
        <div class="search-info">
          <div class="torrent-name">${htmlEscape(item.title || "Untitled")}</div>
          <div class="search-meta">
            <span>${htmlEscape(item.provider || group.provider)}</span>
            ${item.size ? `<span>${htmlEscape(item.size)}</span>` : ""}
            ${item.seeds !== "" && item.seeds !== undefined ? `<span>${htmlEscape(item.seeds)} seeders</span>` : ""}
            ${item.peers !== "" && item.peers !== undefined ? `<span>${htmlEscape(item.peers)} peers</span>` : ""}
          </div>
          ${shots}
          <div class="row">
            <form method="post" action="/search-add">
              <input type="hidden" name="payload" value="${htmlEscape(token.payload)}">
              <input type="hidden" name="sig" value="${htmlEscape(token.sig)}">
              <button type="submit">Add</button>
            </form>
            ${item.pageUrl ? `<a class="button secondary" href="${htmlEscape(item.pageUrl)}" target="_blank" rel="noopener noreferrer">Source</a>` : ""}
          </div>
        </div>
      </article>`;
    }).join("");
    return `<section>
      <h2>${htmlEscape(group.provider)}</h2>
      ${notices}
      ${cards ? `<div class="search-results">${cards}</div>` : notices ? "" : `<p class="muted">No results found.</p>`}
    </section>`;
  }).join("");
  return `<div class="stack">${providerBlocks}</div>`;
}

const aria2StatusFields = ["gid", "status", "totalLength", "completedLength", "downloadSpeed", "numSeeders", "files", "bittorrent", "errorMessage", "followedBy"];

async function currentTorrentStatus(user, record) {
  const item = await aria2("aria2.tellStatus", [record.gid, aria2StatusFields]);
  if (Array.isArray(item.followedBy) && item.followedBy.length > 0) {
    const nextGid = item.followedBy[0];
    await pool.query("UPDATE torrents SET gid = ? WHERE user_id = ? AND gid = ?", [nextGid, user.id, record.gid]);
    return aria2("aria2.tellStatus", [nextGid, aria2StatusFields]);
  }
  return item;
}

async function torrentRows(user) {
  return cachedValue(`torrent-rows:${user.id}`, 2500, async () => {
    const [owned] = await pool.query("SELECT gid, label, created_at FROM torrents WHERE user_id = ? ORDER BY id DESC LIMIT 100", [user.id]);
    if (!owned.length) return `<p class="muted">No torrents yet.</p>`;
    const rows = [];
    for (const record of owned) {
      let item;
      try {
        item = await currentTorrentStatus(user, record);
      } catch (error) {
        rows.push(`<article class="torrent-card">
          <div class="torrent-head">
            <div class="torrent-name">${htmlEscape(record.label || record.gid)}</div>
            <span class="pill error">missing</span>
          </div>
          <div class="muted break">${htmlEscape(error.message)}</div>
        </article>`);
        continue;
      }
      const name = item.bittorrent?.info?.name || record.label || item.files?.[0]?.path?.split(/[\\/]/).pop() || item.gid;
      const total = Number(item.totalLength || 0);
      const done = Number(item.completedLength || 0);
      const pct = total ? Math.min(100, Math.round((done / total) * 100)) : 0;
      rows.push(`<article class="torrent-card">
        <div class="torrent-head">
          <div class="torrent-name">${htmlEscape(name)}</div>
          <span class="pill ${htmlEscape(item.status)}">${htmlEscape(item.status)}</span>
        </div>
        <div>
          <div class="progress"><span style="width:${pct}%"></span></div>
          <div class="muted">${pct}% complete</div>
        </div>
        <div class="stats">
          <div class="stat"><span>Size</span><strong>${bytes(done)} / ${bytes(total)}</strong></div>
          <div class="stat"><span>Speed</span><strong>${bytes(item.downloadSpeed)}/s</strong></div>
          <div class="stat"><span>Seeds</span><strong>${htmlEscape(item.numSeeders ?? "-")}</strong></div>
        </div>
        ${item.errorMessage ? `<div class="muted break">${htmlEscape(item.errorMessage)}</div>` : ""}
      </article>`);
    }
    return `<div class="torrent-list">${rows.join("")}</div>`;
  });
}

async function collectMediaFiles(user, relativePath = "", depth = 0, limit = 300) {
  if (depth > 5 || limit <= 0) return [];
  const entries = await mergedEntries(user, relativePath);
  const files = [];
  for (const entry of entries) {
    if (files.length >= limit) break;
    if (entry.name.startsWith(".")) continue;
    const childRel = relativePath ? `${relativePath}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      files.push(...await collectMediaFiles(user, childRel, depth + 1, limit - files.length));
    } else if (isPlayableMedia(entry.name)) {
      const fullPath = absoluteFor(user, childRel);
      const stat = await fs.promises.stat(fullPath);
      files.push({ rel: childRel, name: entry.name, size: stat.size, mtimeMs: stat.mtimeMs });
    }
  }
  return files;
}

async function mediaLibrary(user) {
  await ensureUserDir(user);
  const entries = await mergedEntries(user, "");
  const items = [];
  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    if (entry.isDirectory()) {
      const media = await collectMediaFiles(user, entry.name);
      if (!media.length) continue;
      const title = cleanMediaTitle(entry.name) || entry.name;
      items.push({
        title,
        rel: entry.name,
        folder: true,
        media,
        latest: Math.max(...media.map((file) => file.mtimeMs))
      });
    } else if (isPlayableMedia(entry.name)) {
      const fullPath = absoluteFor(user, entry.name);
      const stat = await fs.promises.stat(fullPath);
      items.push({
        title: cleanMediaTitle(entry.name) || entry.name,
        rel: entry.name,
        folder: false,
        media: [{ rel: entry.name, name: entry.name, size: stat.size, mtimeMs: stat.mtimeMs }],
        latest: stat.mtimeMs
      });
    }
  }
  return items.sort((a, b) => b.latest - a.latest).slice(0, 80);
}

function renderLibrary(items, trailers = []) {
  if (!items.length) return `<p class="muted">Downloaded media will appear here.</p>`;
  return `<div class="media-shelf">${items.map((item) => {
    const first = item.media[0];
    const episodes = item.media
      .slice()
      .sort((a, b) => episodeLabel(a.name).localeCompare(episodeLabel(b.name), undefined, { numeric: true }))
      .slice(0, 10);
    const tr = findTrailer(trailers, item.title);
    return `<article class="media-card">
      <a class="poster" href="/watch?path=${encodeURIComponent(first.rel)}">
        <img src="/poster?title=${encodeURIComponent(item.title)}" alt="" loading="lazy" onerror="this.remove()">
        <span>${htmlEscape(item.title.slice(0, 1).toUpperCase())}</span>
      </a>
      <div class="media-info">
        <div class="media-title">${htmlEscape(item.title)}</div>
        <div class="muted">${item.media.length} item${item.media.length === 1 ? "" : "s"} - ${bytes(item.media.reduce((sum, file) => sum + Number(file.size || 0), 0))}</div>
        <div class="row">
          <a class="button" href="/watch?path=${encodeURIComponent(first.rel)}">Play</a>
          ${trailerButton(tr)}
          ${item.folder ? `<a class="button secondary" href="/?path=${encodeURIComponent(item.rel)}">Open</a>` : `<a class="button secondary" href="/download?path=${encodeURIComponent(first.rel)}">Download</a>`}
        </div>
        <div class="episode-list">
          ${episodes.map((file) => `<a href="/watch?path=${encodeURIComponent(file.rel)}"><span>${htmlEscape(episodeLabel(file.name))}</span><small>${htmlEscape(file.name)}</small></a>`).join("")}
          ${item.media.length > episodes.length ? `<a href="/?path=${encodeURIComponent(item.rel)}"><span>More</span><small>${item.media.length - episodes.length} more files</small></a>` : ""}
        </div>
      </div>
    </article>`;
  }).join("")}</div>`;
}

async function fileRows(user, relativePath) {
  return cachedValue(`file-rows:${user.id}:${relativePath}`, 5000, async () => {
    const full = absoluteFor(user, relativePath);
    await ensureUserDir(user);
    const entries = await mergedEntries(user, relativePath);
    const rows = [];
    if (relativePath) {
      const parent = parentRelative(relativePath);
      rows.push(`<tr><td><a href="/?path=${encodeURIComponent(parent)}">..</a></td><td>Folder</td><td></td><td></td></tr>`);
    }
    for (const entry of entries.sort((a, b) => Number(b.isDirectory()) - Number(a.isDirectory()) || a.name.localeCompare(b.name))) {
      const childRel = relativePath ? `${relativePath}/${entry.name}` : entry.name;
      const childFull = absoluteFor(user, childRel);
      const stat = await fs.promises.stat(childFull);
      const href = entry.isDirectory()
        ? `/?path=${encodeURIComponent(childRel)}`
        : isPlayableMedia(entry.name)
          ? `/watch?path=${encodeURIComponent(childRel)}`
          : `/download?path=${encodeURIComponent(childRel)}`;
      const action = entry.isDirectory()
        ? ""
        : isPlayableMedia(entry.name)
          ? `<a href="/download?path=${encodeURIComponent(childRel)}">Download</a>`
          : "";
      rows.push(`<tr>
        <td><a href="${href}">${htmlEscape(entry.name)}</a></td>
        <td>${entry.isDirectory() ? "Folder" : "File"}</td>
        <td>${entry.isDirectory() ? "" : bytes(stat.size)}</td>
        <td>${new Date(stat.mtimeMs).toLocaleString()} ${action}</td>
      </tr>`);
    }
    return rows.join("") || `<tr><td colspan="4" class="muted">Files downloaded by your torrents will appear here.</td></tr>`;
  });
}

function renderSettingsPage(user) {
  const token = encodeURIComponent(config.vpsSearchToken || "");
  return layout(user, `<main class="settings-page">
    <div class="cc-head">
      <h1>Settings</h1>
      <p class="muted">LLM keys, custom providers, devices and board-wide variables.</p>
    </div>
    <div class="settings-tabs" role="tablist">
      <button class="settings-tab active" data-tab="providers">LLM Providers</button>
      <button class="settings-tab" data-tab="custom">Add Provider</button>
      <button class="settings-tab" data-tab="general">General</button>
      <button class="settings-tab" data-tab="devices">Devices</button>
    </div>
    <section id="tab-providers" class="settings-tabpane active">
      <div id="provider-grid" class="provider-grid"><div class="panel">Loading providers…</div></div>
      <p class="muted" style="margin-top:12px">Keys are stored in <code>${TANK_ENV_FILE}</code> (chmod 600). Saving restarts the TankOS terminals so new keys apply immediately.</p>
    </section>
    <section id="tab-custom" class="settings-tabpane">
      <div class="panel settings-form">
        <h2>Add an LLM provider</h2>
        <p class="muted">Any OpenAI-compatible API endpoint works (OpenAI, local Ollama, LM Studio, Together…).</p>
        <div class="form-row"><label>Name</label><input id="cu-name" placeholder="my-llm" autocomplete="off"></div>
        <div class="form-row"><label>Base URL</label><input id="cu-base" placeholder="https://api.example.com/v1" autocomplete="off"></div>
        <div class="form-row"><label>Model</label><input id="cu-model" placeholder="gpt-4o-mini" autocomplete="off"></div>
        <div class="form-row"><label>API Key</label><input id="cu-key" type="password" placeholder="sk-..." autocomplete="off"></div>
        <div class="actions"><button class="button" id="cu-save">Add Provider</button><span class="provider-result" id="cu-result"></span></div>
      </div>
      <div class="panel" id="custom-list-wrap" style="margin-top:14px"><h2>Custom providers</h2><div class="custom-list" id="custom-list"></div></div>
    </section>
    <section id="tab-general" class="settings-tabpane">
      <div class="panel settings-form">
        <h2>General</h2>
        <div class="form-row"><label>Brand name (top-left)</label><input id="ge-brand" autocomplete="off"></div>
        <div class="form-row"><label>Default LLM provider</label><select id="ge-provider"></select></div>
        <div class="form-row"><label>Temperature</label><input id="ge-temp" type="number" step="0.1" min="0" max="2"></div>
        <div class="form-row"><label>Max tokens</label><input id="ge-tokens" type="number" min="16" max="8192"></div>
        <div class="form-row"><label>Torrent search providers</label><input id="ge-search" placeholder="Nyaa,VPS"></div>
        <div class="form-row"><label>Aria2 RPC URL</label><input id="ge-aria2" placeholder="http://127.0.0.1:6800/jsonrpc"></div>
        <div class="form-row"><label>VPS search URL</label><input id="ge-vps" placeholder="http://213.199.61.156:9100"></div>
        <div class="actions"><button class="button" id="ge-save">Save Settings</button><span class="provider-result" id="ge-result"></span></div>
      </div>
    </section>
    <section id="tab-devices" class="settings-tabpane">
      <div id="device-list"><div class="panel">Scanning devices…</div></div>
      <p class="muted" style="margin-top:12px">The LLM terminal can see this inventory — ask it things like <em>"what devices are connected?"</em></p>
    </section>
  </main>
  <script>
    (function () {
      var token = ${JSON.stringify(config.vpsSearchToken || "")};
      var api = "/api/settings?token=" + encodeURIComponent(token);
      var apiPost = "/api/settings";
      var state = { providers: [], custom: [], app: {} };
      function toast(msg, isErr) {
        var el = document.createElement("div");
        el.className = "toast" + (isErr ? " err" : "");
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(function () { el.remove(); }, 3800);
      }
      function esc(s) {
        return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
          return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
        });
      }
      document.querySelectorAll(".settings-tab").forEach(function (btn) {
        btn.addEventListener("click", function () {
          document.querySelectorAll(".settings-tab").forEach(function (b) { b.classList.remove("active"); });
          document.querySelectorAll(".settings-tabpane").forEach(function (p) { p.classList.remove("active"); });
          btn.classList.add("active");
          document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
        });
      });
      function renderProviders() {
        var grid = document.getElementById("provider-grid");
        if (!state.providers.length) { grid.innerHTML = '<div class="panel">No providers registered.</div>'; return; }
        grid.innerHTML = state.providers.map(function (p) {
          var keyPill = p.hasKey ? '<span class="pill active">Key set</span>' : '<span class="pill paused">No key</span>';
          var regPill = p.registered ? '<span class="pill active">Registered</span>' : '<span class="pill error">Offline</span>';
          return '<div class="panel provider-card" data-name="' + esc(p.name) + '">' +
            '<div class="provider-head"><span class="provider-name">' + esc(p.name) + '</span>' + keyPill + regPill + '</div>' +
            '<div class="provider-base">' + esc(p.baseUrl) + '</div>' +
            '<div class="control-field"><label>Model</label><input data-f="model" value="' + esc(p.model) + '" autocomplete="off"></div>' +
            '<div class="control-field"><label>API Key (' + esc(p.keyEnv) + ')</label><input data-f="key" type="password" placeholder="' + (p.hasKey ? "••••••••  (leave blank to keep)" : "sk-...") + '" autocomplete="new-password"></div>' +
            '<div class="actions">' +
              '<button class="button" data-act="test">Test</button>' +
              '<button class="button secondary" data-act="save">Save</button>' +
              (p.hasKey ? '<button class="button secondary" data-act="clear">Clear Key</button>' : '') +
            '</div>' +
            '<div class="provider-result" data-role="result"></div>' +
          '</div>';
        }).join("");
      }
      function renderDevices() {
        var list = document.getElementById("device-list");
        var d = state.devices || {};
        var types = Object.keys(d);
        if (!types.length) { list.innerHTML = '<div class="panel">No devices detected.</div>'; return; }
        var html = "";
        var labels = { camera: "Cameras", serial: "Serial / USB", display: "Displays", audio: "Audio", storage: "Storage", network: "Network" };
        types.forEach(function (t) {
          var rows = (d[t] || []).map(function (dev) {
            return '<div class="dev-row"><span class="dot' + (dev.connected === false ? " off" : "") + '"></span>' +
              '<span class="dev-name">' + esc(dev.name || "Unknown") + '</span>' +
              (dev.path ? '<span class="dev-path">' + esc(dev.path) + '</span>' : '') + '</div>';
          }).join("");
          html += '<div class="dev-group"><h3 style="margin:0 0 4px">' + (labels[t] || t) + '</h3>' + (rows || '<p class="muted">None</p>') + '</div>';
        });
        list.innerHTML = html;
      }
      function renderCustom() {
        var el = document.getElementById("custom-list");
        if (!state.custom.length) { el.innerHTML = '<p class="muted">No custom providers yet.</p>'; return; }
        el.innerHTML = state.custom.map(function (c) {
          return '<div class="dev-row"><span class="dot"></span><span class="dev-name">' + esc(c.name) + '</span>' +
            '<span class="dev-path">' + esc(c.baseUrl) + '</span>' +
            '<button class="button secondary" data-remove="' + esc(c.name) + '" style="padding:6px 12px;font-size:12px">Remove</button></div>';
        }).join("");
      }
      /* __SETTINGS_PART_B__ */
    function renderGeneral() {
        var a = state.app || {};
        document.getElementById("ge-brand").value = a.brandName || "";
        document.getElementById("ge-temp").value = a.temperature != null ? a.temperature : 0.7;
        document.getElementById("ge-tokens").value = a.maxTokens != null ? a.maxTokens : 512;
        document.getElementById("ge-search").value = a.searchProviders || "";
        document.getElementById("ge-aria2").value = a.aria2Rpc || "";
        document.getElementById("ge-vps").value = a.vpsSearchUrl || "";
        var sel = document.getElementById("ge-provider");
        var names = (state.providers || []).map(function (p) { return p.name; });
        if (names.indexOf("rotation") < 0) names.unshift("rotation");
        sel.innerHTML = names.map(function (n) {
          return '<option value="' + esc(n) + '"' + (n === a.defaultProvider ? " selected" : "") + '>' + esc(n) + '</option>';
        }).join("");
      }
      function load() {
        fetch(api).then(function (r) { return r.json(); }).then(function (d) {
          if (!d || !d.ok) { toast("Failed to load settings", true); return; }
          state.providers = d.providers || [];
          state.custom = d.customProviders || [];
          state.app = d.app || {};
          state.devices = d.devices || {};
          renderProviders(); renderCustom(); renderGeneral(); renderDevices();
        }).catch(function () { toast("Settings API unreachable", true); });
      }
      document.addEventListener("click", function (e) {
        var card = e.target.closest(".provider-card");
        if (card) {
          var name = card.dataset.name;
          var p = state.providers.find(function (x) { return x.name === name; });
          var result = card.querySelector('[data-role="result"]');
          var act = e.target.dataset && e.target.dataset.act;
          if (act === "test") {
            result.className = "provider-result"; result.textContent = "Testing…";
            fetch(apiPost + "/test-llm?token=" + encodeURIComponent(token), {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ provider: name, message: "Reply with just: OK" })
            }).then(function (r) { return r.json(); }).then(function (d) {
              result.className = "provider-result " + (d.ok ? "ok" : "err");
              result.textContent = d.ok ? "✓ " + d.text + "  (" + d.provider + ", " + d.durationMs + "ms)" : "✗ " + (d.error || "failed");
            }).catch(function () { result.className = "provider-result err"; result.textContent = "✗ request failed"; });
          } else if (act === "save") {
            var keys = {};
            var keyInput = card.querySelector('[data-f="key"]');
            var modelInput = card.querySelector('[data-f="model"]');
            keys[p.modelEnv] = modelInput.value.trim();
            if (keyInput.value.trim()) keys[p.keyEnv] = keyInput.value.trim();
            result.className = "provider-result"; result.textContent = "Saving…";
            fetch(apiPost + "/llm?token=" + encodeURIComponent(token), {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ keys: keys })
            }).then(function (r) { return r.json(); }).then(function (d) {
              if (d.ok) { toast("Saved " + name + " — terminals restarted"); keyInput.value = ""; load(); }
              else { result.className = "provider-result err"; result.textContent = "✗ " + (d.error || "failed"); }
            });
          } else if (act === "clear") {
            var k2 = {}; k2[p.keyEnv] = "";
            fetch(apiPost + "/llm?token=" + encodeURIComponent(token), {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ keys: k2 })
            }).then(function (r) { return r.json(); }).then(function (d) {
              toast(d.ok ? "Key cleared for " + name : "Failed to clear key", !d.ok);
              load();
            });
          }
          return;
        }
        var rm = e.target.closest("[data-remove]");
        if (rm) {
          fetch(apiPost + "/custom?token=" + encodeURIComponent(token), {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: rm.dataset.remove, remove: true })
          }).then(function (r) { return r.json(); }).then(function (d) { toast(d.ok ? "Removed " + rm.dataset.remove : "Remove failed", !d.ok); load(); });
        }
      });
      document.getElementById("cu-save").addEventListener("click", function () {
        var body = {
          name: document.getElementById("cu-name").value.trim(),
          baseUrl: document.getElementById("cu-base").value.trim(),
          model: document.getElementById("cu-model").value.trim(),
          key: document.getElementById("cu-key").value.trim()
        };
        if (!body.name || !body.baseUrl || !body.key) { toast("Name, base URL and key are required", true); return; }
        var res = document.getElementById("cu-result");
        res.className = "provider-result"; res.textContent = "Adding…";
        fetch(apiPost + "/custom?token=" + encodeURIComponent(token), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }).then(function (r) { return r.json(); }).then(function (d) {
          if (d.ok) { toast("Added provider " + body.name + " — terminals restarted"); document.getElementById("cu-key").value = ""; load(); }
          else { res.className = "provider-result err"; res.textContent = "✗ " + (d.error || "failed"); }
        });
      });
      document.getElementById("ge-save").addEventListener("click", function () {
        var body = {
          brandName: document.getElementById("ge-brand").value.trim(),
          defaultProvider: document.getElementById("ge-provider").value,
          temperature: Number(document.getElementById("ge-temp").value),
          maxTokens: Number(document.getElementById("ge-tokens").value),
          searchProviders: document.getElementById("ge-search").value.trim(),
          aria2Rpc: document.getElementById("ge-aria2").value.trim(),
          vpsSearchUrl: document.getElementById("ge-vps").value.trim()
        };
        var res = document.getElementById("ge-result");
        res.className = "provider-result"; res.textContent = "Saving…";
        fetch(apiPost + "/general?token=" + encodeURIComponent(token), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        }).then(function (r) { return r.json(); }).then(function (d) {
          if (d.ok) { toast("General settings saved"); res.className = "provider-result ok"; res.textContent = "✓ Saved"; load(); }
          else { res.className = "provider-result err"; res.textContent = "✗ " + (d.error || "failed"); }
        });
      });
      load();
      setInterval(load, 60000);
    })();
  </script>`, "");
  /* end of renderSettingsPage */
}

function renderRemotePage(user) {
  return layout(user, `<main class="remote-main">
  <style>
    .remote-main { max-width: 1400px; }
    .rm-top { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 20px; }
    .rm-top h1 { margin: 0; font-size: 26px; }
    .rm-status { display: flex; align-items: center; gap: 10px; }
    .rm-status .dot { width: 10px; height: 10px; border-radius: 50%; background: #f87171; box-shadow: 0 0 12px rgba(248,113,113,.7); }
    .rm-status .dot.on { background: #34d399; box-shadow: 0 0 12px rgba(52,211,153,.7); }
    .rm-status .dot.warn { background: #fbbf24; box-shadow: 0 0 12px rgba(251,191,36,.7); }
    .rm-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
    .rm-tab { padding: 10px 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,.1); background: rgba(255,255,255,.04); color: #b3bccf; font-weight: 800; font-size: 14px; cursor: pointer; transition: all .15s ease; }
    .rm-tab:hover { background: rgba(99,102,241,.14); color: #fff; }
    .rm-tab.active { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; border-color: transparent; box-shadow: 0 4px 18px rgba(99,102,241,.4); }
    .rm-view { display: none; }
    .rm-view.active { display: block; animation: tvFade .3s ease; }
    .rm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media (max-width: 900px) { .rm-grid { grid-template-columns: 1fr; } }
    .rm-card { background: linear-gradient(180deg, rgba(22,30,52,.78), rgba(13,18,33,.82)); border: 1px solid rgba(255,255,255,.07); border-radius: 16px; padding: 20px; box-shadow: 0 14px 44px rgba(0,0,0,.38); }
    .rm-card h3 { margin: 0 0 14px; font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .09em; color: #8b95aa; }
    .big-tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
    .big-tile { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 26px 16px; border-radius: 16px; background: linear-gradient(135deg, #1e293b, #4338ca); border: 1px solid rgba(255,255,255,.1); cursor: pointer; transition: transform .15s ease, box-shadow .15s ease, filter .15s ease; }
    .big-tile:hover, .big-tile:focus-visible { transform: translateY(-2px); filter: brightness(1.12); box-shadow: 0 10px 32px rgba(99,102,241,.4); outline: none; }
    .big-tile .ic { font-size: 40px; line-height: 1; }
    .big-tile .lb { font-weight: 800; font-size: 15px; color: #fff; }
    .dpad { display: grid; grid-template-columns: 76px 76px 76px; grid-template-rows: 76px 76px 76px; gap: 10px; justify-content: center; margin: 6px 0 18px; }
    .dpad button { border: 1px solid rgba(255,255,255,.12); border-radius: 14px; background: rgba(255,255,255,.05); color: #e8ecf4; font-size: 20px; font-weight: 900; cursor: pointer; transition: all .13s ease; }
    .dpad button:hover, .dpad button:focus-visible { background: rgba(99,102,241,.3); border-color: rgba(129,140,248,.7); transform: scale(1.05); outline: none; }
    .dpad .ok { background: linear-gradient(135deg, #6366f1, #8b5cf6); border-color: transparent; box-shadow: 0 4px 18px rgba(99,102,241,.45); }
    .ctrl-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .ctrl-row .lbl { font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: #7d879c; width: 90px; }
    .numpad { display: grid; grid-template-columns: repeat(3, 62px); gap: 8px; justify-content: center; }
    .numpad button { height: 46px; border: 1px solid rgba(255,255,255,.1); border-radius: 10px; background: rgba(255,255,255,.05); color: #e8ecf4; font-weight: 800; font-size: 16px; cursor: pointer; }
    .numpad button:hover { background: rgba(99,102,241,.25); }
    .field { display: grid; gap: 6px; margin-bottom: 12px; }
    .field label { font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: #8b95aa; }
    .field input { width: 100%; min-height: 44px; padding: 10px 14px; border: 1px solid rgba(255,255,255,.13); border-radius: 11px; background: rgba(9,13,26,.85); color: #e8ecf4; font: inherit; }
    .field input:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.28); }
    .out-box { margin-top: 14px; padding: 12px; border-radius: 10px; background: rgba(9,13,26,.7); border: 1px solid rgba(255,255,255,.08); color: #9aa4b8; font: 12px/1.5 ui-monospace, Consolas, monospace; max-height: 220px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
    .dev-list { display: grid; gap: 8px; }
    .dev-item { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 14px; border-radius: 10px; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.07); font-size: 14px; }
    .dev-item .ip { font-weight: 800; color: #e8ecf4; }
    .dev-item button { min-height: 32px; padding: 6px 14px; font-size: 12px; }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
    .stat { padding: 14px; border-radius: 12px; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.07); text-align: center; }
    .stat .v { font-size: 22px; font-weight: 900; color: #fff; }
    .stat .k { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: #7d879c; margin-top: 4px; }
    .cast-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
    .cast-row .chip { padding: 8px 16px; border-radius: 999px; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.05); color: #cdd5e3; font-weight: 700; font-size: 13px; cursor: pointer; }
    .cast-row .chip.active { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; border-color: transparent; }
    .row-flex { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  </style>

  <div class="rm-top">
    <h1>📺 TV Remote</h1>
    <div class="rm-status">
      <span class="dot" id="rmDot"></span>
      <span id="rmStatusText" class="muted">Checking…</span>
      <button class="button secondary" onclick="rmRefreshStatus()">↻ Refresh</button>
    </div>
  </div>

  <div class="rm-tabs">
    <button class="rm-tab active" data-tab="remote" onclick="rmTab('remote')">🎛 Remote</button>
    <button class="rm-tab" data-tab="cast" onclick="rmTab('cast')">📡 Cast</button>
    <button class="rm-tab" data-tab="network" onclick="rmTab('network')">🌐 Network</button>
    <button class="rm-tab" data-tab="setup" onclick="rmTab('setup')">⚙️ Setup</button>
  </div>

  <div class="rm-view active" id="view-remote">
    <div class="big-tiles">
      <div class="big-tile" onclick="rmKey('power')" title="Power toggle"><span class="ic">⏻</span><span class="lb">POWER</span></div>
      <div class="big-tile" onclick="rmCastNow('')" title="Cast screen / YouTube"><span class="ic">📺</span><span class="lb">CAST</span></div>
    </div>
    <div class="rm-grid">
      <div class="rm-card">
        <h3>Remote Control</h3>
        <div class="dpad">
          <button onclick="rmKey('up')" title="Up">▲</button>
          <button onclick="rmKey('ok')" class="ok" title="OK">OK</button>
          <button onclick="rmKey('down')" title="Down">▼</button>
          <button onclick="rmKey('left')" title="Left">◀</button>
          <button onclick="rmKey('ok')" class="ok" title="Select">⏺</button>
          <button onclick="rmKey('right')" title="Right">▶</button>
        </div>
        <div class="ctrl-row" style="justify-content:center">
          <button class="button secondary" onclick="rmKey('home')">🏠 Home</button>
          <button class="button secondary" onclick="rmKey('back')">⬅ Back</button>
          <button class="button secondary" onclick="rmKey('menu')">☰ Menu</button>
          <button class="button secondary" onclick="rmKey('guide')">📋 Guide</button>
          <button class="button secondary" onclick="rmKey('search')">🔍 Search</button>
        </div>
      </div>
      <div class="rm-card">
        <h3>Volume & Channels</h3>
        <div class="ctrl-row">
          <span class="lbl">Volume</span>
          <button onclick="rmKey('voldown')">−</button>
          <button class="button secondary" onclick="rmKey('mute')">🔇 Mute</button>
          <button onclick="rmKey('volup')">+</button>
        </div>
        <div class="ctrl-row" style="margin-top:12px">
          <span class="lbl">Channel</span>
          <button onclick="rmKey('chdown')">−</button>
          <button class="button secondary" onclick="rmKey('tvinput')">📺 Input</button>
          <button onclick="rmKey('chup')">+</button>
        </div>
        <div class="ctrl-row" style="margin-top:16px"><span class="lbl">Numpad</span></div>
        <div class="numpad" id="numpad"></div>
        <div class="ctrl-row" style="margin-top:16px">
          <span class="lbl">Media</span>
          <button onclick="rmKey('rew')">⏪</button>
          <button class="button secondary" onclick="rmKey('play')">▶</button>
          <button class="button secondary" onclick="rmKey('pause')">⏸</button>
          <button onclick="rmKey('ff')">⏩</button>
        </div>
      </div>
    </div>
  </div>

  <div class="rm-view" id="view-cast">
    <div class="rm-grid">
      <div class="rm-card">
        <h3>Cast to TV</h3>
        <div class="cast-row" id="castChips">
          <span class="chip active" onclick="rmCastApp('youtube', this)">▶ YouTube</span>
          <span class="chip" onclick="rmCastApp('chrome', this)">🌐 Chrome</span>
        </div>
        <div class="field">
          <label>YouTube video URL or search</label>
          <input id="castUrl" placeholder="https://www.youtube.com/watch?v=…  or  search: cats" onkeydown="if(event.key==='Enter')rmCastNow()">
        </div>
        <div class="row-flex">
          <button onclick="rmCastNow()">📡 Cast now</button>
          <button class="button secondary" onclick="rmCastSearch()">🔍 Search & cast</button>
          <button class="button secondary" onclick="rmKey('play')">▶ Play</button>
          <button class="button secondary" onclick="rmKey('pause')">⏸ Pause</button>
          <button class="button secondary" onclick="rmKey('stop')">⏹ Stop</button>
        </div>
        <div class="out-box" id="castOut">Ready. Cast a URL or pick a trailer below.</div>
      </div>
      <div class="rm-card">
        <h3>Library trailers → cast</h3>
        <div class="dev-list" id="castLib"></div>
        <p class="muted" style="font-size:13px;margin-top:10px">Pick a trailer from your library and it opens straight on the TV.</p>
      </div>
    </div>
  </div>

  <div class="rm-view" id="view-network">
    <div class="rm-grid">
      <div class="rm-card">
        <h3>Network Status</h3>
        <div class="stat-grid">
          <div class="stat"><div class="v" id="netPing">–</div><div class="k">Ping ms</div></div>
          <div class="stat"><div class="v" id="netJitter">–</div><div class="k">Jitter</div></div>
          <div class="stat"><div class="v" id="netDown">–</div><div class="k">Down Mbps</div></div>
          <div class="stat"><div class="v" id="netLan">–</div><div class="k">LAN IP</div></div>
        </div>
        <div class="row-flex">
          <button onclick="rmSpeed()">⚡ Run speed test</button>
          <button class="button secondary" onclick="rmPing()">📡 Ping TV</button>
        </div>
        <div class="out-box" id="netOut"></div>
      </div>
      <div class="rm-card">
        <h3>Device Discovery</h3>
        <button onclick="rmDiscover()">🔍 Scan LAN</button>
        <div class="dev-list" id="devList" style="margin-top:12px"></div>
        <p class="muted" style="font-size:13px;margin-top:10px">Devices found on your network. Click Use to pair as the remote target.</p>
      </div>
    </div>
  </div>

  <div class="rm-view" id="view-setup">
    <div class="rm-grid">
      <div class="rm-card">
        <h3>TV Connection</h3>
        <div class="field"><label>TV IP address</label><input id="setIp" placeholder="192.168.1.100"></div>
        <div class="field"><label>ADB port</label><input id="setPort" placeholder="5555"></div>
        <div class="field"><label>MAC address (for Wake-on-LAN)</label><input id="setMac" placeholder="AA:BB:CC:DD:EE:FF"></div>
        <div class="row-flex">
          <button onclick="rmConnect()">🔗 Connect</button>
          <button class="button secondary" onclick="rmWol()">⏻ Wake (WoL)</button>
          <button class="button secondary" onclick="rmDisconnect()">✂ Disconnect</button>
        </div>
        <div class="out-box" id="setupOut"></div>
      </div>
      <div class="rm-card">
        <h3>TV Information</h3>
        <div class="stat-grid" style="grid-template-columns:1fr 1fr">
          <div class="stat"><div class="v" id="infoModel">–</div><div class="k">Model</div></div>
          <div class="stat"><div class="v" id="infoAndroid">–</div><div class="k">Android</div></div>
        </div>
        <div class="dev-list">
          <div class="dev-item"><span>Connection</span><span id="infoConn" class="muted">–</span></div>
          <div class="dev-item"><span>Target</span><span id="infoTarget" class="muted">–</span></div>
        </div>
        <p class="muted" style="font-size:13px;margin-top:12px">💡 On your TV: <b>Settings → Developer options → USB/Network debugging ON</b>, then enter its IP above. Wake-on-LAN needs the TV's MAC address.</p>
      </div>
    </div>
  </div>

  <script>
  let rmCastTarget = "youtube";
  function rmTab(name) {
    document.querySelectorAll(".rm-tab").forEach(function (t) { t.classList.toggle("active", t.dataset.tab === name); });
    document.querySelectorAll(".rm-view").forEach(function (v) { v.classList.toggle("active", v.id === "view-" + name); });
  }
  function rmCastApp(app, el) {
    rmCastTarget = app;
    document.querySelectorAll("#castChips .chip").forEach(function (c) { c.classList.remove("active"); });
    if (el) el.classList.add("active");
  }
  function rmApi(action, data, method) {
    return fetch("/api/tv/" + action, { method: method || "POST", headers: { "Content-Type": "application/json" }, body: data ? JSON.stringify(data) : undefined })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: "bad response" }; }); });
  }
  function rmKey(key) {
    rmApi("key", { key: key }).then(function (r) {
      if (!r.ok && r.error) alert("Key failed: " + r.error);
    }).catch(function (e) { alert("Key failed: " + e.message); });
  }
  function rmCastNow(url) {
    const u = url || document.getElementById("castUrl").value;
    if (!u) { alert("Enter a YouTube URL or search first"); return; }
    let target = u;
    if (/^search:/i.test(u.trim())) target = "https://www.youtube.com/results?search_query=" + encodeURIComponent(u.trim().replace(/^search:/i, "").trim());
    else if (!/^https?:/.test(u.trim())) target = "https://www.youtube.com/results?search_query=" + encodeURIComponent(u.trim());
    document.getElementById("castOut").textContent = "Casting… " + target;
    rmApi("cast", { url: target, app: rmCastTarget }).then(function (r) {
      document.getElementById("castOut").textContent = r.ok ? ("✅ Sent to TV\n" + (r.out || "")) : ("❌ " + (r.error || "failed"));
    }).catch(function (e) { document.getElementById("castOut").textContent = "❌ " + e.message; });
  }
  function rmCastSearch() {
    document.getElementById("castUrl").value = "search: ";
    document.getElementById("castUrl").focus();
  }
  function rmConnect() {
    const ip = document.getElementById("setIp").value.trim();
    const port = document.getElementById("setPort").value.trim() || "5555";
    if (!ip) { alert("Enter TV IP"); return; }
    document.getElementById("setupOut").textContent = "Connecting…";
    rmApi("connect", { ip: ip, port: port }).then(function (r) {
      document.getElementById("setupOut").textContent = r.ok ? ("✅ " + r.out) : ("❌ " + (r.error || "failed"));
      rmSaveFields();
      rmRefreshStatus();
    }).catch(function (e) { document.getElementById("setupOut").textContent = "❌ " + e.message; });
  }
  function rmDisconnect() {
    rmApi("disconnect", {}).then(function (r) { document.getElementById("setupOut").textContent = r.ok ? ("✅ " + r.out) : ("❌ " + r.error); rmRefreshStatus(); });
  }
  function rmWol() {
    const mac = document.getElementById("setMac").value.trim();
    if (!mac) { alert("Enter TV MAC address"); return; }
    document.getElementById("setupOut").textContent = "Sending wake packet…";
    rmApi("wol", { mac: mac }).then(function (r) {
      document.getElementById("setupOut").textContent = r.ok ? ("✅ Magic packet sent to " + mac) : ("❌ " + (r.error || "failed"));
    });
  }
  function rmSaveFields() {
    rmApi("settings", { tvIp: document.getElementById("setIp").value.trim(), tvPort: document.getElementById("setPort").value.trim() || "5555", tvMac: document.getElementById("setMac").value.trim() }, "POST");
  }
  function rmRefreshStatus() {
    rmApi("status", {}, "GET").then(function (r) {
      const dot = document.getElementById("rmDot");
      const txt = document.getElementById("rmStatusText");
      if (r.ok && r.tvIp) {
        if (r.connected) { dot.className = "dot on"; txt.textContent = "Connected · " + r.tvIp + (r.model ? " · " + r.model : ""); }
        else { dot.className = "dot warn"; txt.textContent = "Configured but offline · " + r.tvIp; }
      } else { dot.className = "dot"; txt.textContent = "No TV configured — open Setup"; }
      document.getElementById("infoModel").textContent = r.model || "–";
      document.getElementById("infoAndroid").textContent = r.androidVer || "–";
      document.getElementById("infoConn").textContent = r.connected ? "Connected" : (r.tvIp ? "Offline" : "Not configured");
      document.getElementById("infoTarget").textContent = r.tvIp ? (r.tvIp + ":" + (r.tvPort || "5555")) : "–";
      if (!document.getElementById("setIp").value && r.tvIp) {
        document.getElementById("setIp").value = r.tvIp;
        document.getElementById("setPort").value = r.tvPort || "5555";
        document.getElementById("setMac").value = r.tvMac || "";
      }
    }).catch(function () {});
  }
  function rmPing() {
    document.getElementById("netOut").textContent = "Pinging…";
    rmApi("ping", {}).then(function (r) {
      document.getElementById("netOut").textContent = r.ok ? ("Ping " + r.target + ": avg " + (r.avgMs || "?") + " ms\n" + r.out) : ("❌ " + (r.error || "failed"));
    }).catch(function (e) { document.getElementById("netOut").textContent = "❌ " + e.message; });
  }
  function rmSpeed() {
    document.getElementById("netOut").textContent = "Running speed test (8 MB download)…";
    rmApi("speed", {}).then(function (r) {
      if (!r.ok) { document.getElementById("netOut").textContent = "❌ " + (r.error || "failed"); return; }
      document.getElementById("netPing").textContent = r.ms || "–";
      document.getElementById("netJitter").textContent = r.jitter || "–";
      document.getElementById("netDown").textContent = r.downMbps || "–";
      document.getElementById("netOut").textContent = r.note || "Done";
    }).catch(function (e) { document.getElementById("netOut").textContent = "❌ " + e.message; });
  }
  function rmDiscover() {
    document.getElementById("devList").innerHTML = '<div class="dev-item"><span class="muted">Scanning 254 hosts…</span></div>';
    rmApi("discover", {}).then(function (r) {
      const list = document.getElementById("devList");
      if (!r.ok || !r.devices || !r.devices.length) { list.innerHTML = '<div class="dev-item"><span class="muted">No devices found</span></div>'; return; }
      list.innerHTML = r.devices.map(function (ip) {
        return '<div class="dev-item"><span class="ip">' + ip + '</span><button onclick="rmUseIp(\'' + ip + '\')">Use</button></div>';
      }).join("");
    }).catch(function (e) { document.getElementById("devList").innerHTML = '<div class="dev-item"><span class="muted">❌ ' + e.message + '</span></div>'; });
  }
  function rmUseIp(ip) {
    document.getElementById("setIp").value = ip;
    rmTab("setup");
    rmConnect();
  }
  function rmLoadCastLib() {
    fetch("/api/trailers?limit=8").then(function (r) { return r.json(); }).then(function (r) {
      const list = document.getElementById("castLib");
      if (!r.ok || !r.trailers || !r.trailers.length) { list.innerHTML = '<div class="dev-item"><span class="muted">No trailers in DB yet</span></div>'; return; }
      list.innerHTML = r.trailers.map(function (t) {
        const url = "https://www.youtube.com/watch?v=" + t.youtube_id;
        return '<div class="dev-item"><span class="ip" style="max-width:60%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (t.title || "") + '</span><button onclick="rmCastNow(\'' + url + '\')">▶</button></div>';
      }).join("");
    }).catch(function () {});
  }
  (function () {
    const pad = document.getElementById("numpad");
    if (pad) {
      let html = "";
      for (let i = 0; i <= 9; i++) html += '<button onclick="rmKey(\'' + (i === 0 ? 0 : i) + '\')">' + (i === 0 ? "0" : i) + "</button>";
      html += '<button onclick="rmKey(\'ok\')">OK</button><button onclick="rmKey(\'chup\')">CH+</button>';
      pad.innerHTML = html;
    }
    rmRefreshStatus();
    rmLoadCastLib();
    setInterval(rmRefreshStatus, 30000);
  })();
  </script>
</main>
`);
}

function renderControlCenter(user) {
  const token = encodeURIComponent(config.vpsSearchToken || "");
  const card = (title, body, extra = "") => `<section class="panel"><h2>${title}</h2>${body}${extra}</section>`;
  const gauge = (label, id, suffix = "%") => `
    <div class="stat">
      <span>${label}</span>
      <strong id="${id}">--${suffix}</strong>
      <div class="progress"><span id="${id}-bar" style="width:0%"></span></div>
    </div>`;
  const svc = (name, label, id) => `
    <div class="svc-row">
      <span class="svc-name">${label}</span>
      <span class="pill" id="${id}">...</span>
    </div>`;
  return layout(user, `<main class="control-center">
    <div class="cc-head">
      <h1>Control Center</h1>
      <p class="muted">Everything on the board in one place.</p>
    </div>
    <div class="cc-grid">
      ${card("System", `
        <div class="stats">
          ${gauge("CPU", "cc-cpu")}
          ${gauge("RAM", "cc-ram")}
          ${gauge("Disk", "cc-disk")}
        </div>
        <div class="stat-row">
          <div class="stat"><span>Temp</span><strong id="cc-temp">--</strong></div>
          <div class="stat"><span>Uptime</span><strong id="cc-uptime">--</strong></div>
          <div class="stat"><span>Host</span><strong id="cc-host">--</strong></div>
        </div>`)}
      ${card("Services", `
        <div class="svc-list">
          ${svc("cloud", "Torrent Cloud", "s-cloud")}
          ${svc("aria2", "Aria2 (Docker)", "s-aria2")}
          ${svc("vpn", "VPN to VPS", "s-vpn")}
          ${svc("tailscale", "Tailscale", "s-tailscale")}
          ${svc("tankos", "TankOS Terminal", "s-tankos")}
          ${svc("tankosWeb", "TankOS Web", "s-tankosWeb")}
          ${svc("mariadb", "MariaDB", "s-mariadb")}
        </div>
        <div class="row" style="margin-top:12px">
          <button class="button" data-action="vpn:start">VPN On</button>
          <button class="button secondary" data-action="vpn:stop">VPN Off</button>
          <button class="button secondary" data-action="vpn:restart">VPN Restart</button>
        </div>`)}
      ${card("Network", `
        <div class="stat-row">
          <div class="stat"><span>VPN tunnel IP</span><strong id="cc-vpnip">--</strong></div>
          <div class="stat"><span>Tailscale IP</span><strong id="cc-tsip">--</strong></div>
          <div class="stat"><span>Tailscale name</span><strong id="cc-tsname">--</strong></div>
        </div>
        <div class="row" style="margin-top:12px">
          <button class="button secondary" data-action="tailscale:restart">Restart Tailscale</button>
          <a class="button secondary" href="http://192.168.31.72:8082" target="_blank" rel="noopener noreferrer">AriaNg</a>
          <a class="button secondary" href="http://213.199.61.156:9200/" target="_blank" rel="noopener noreferrer">VPS Library</a>
        </div>`)}
      ${card("TankOS AI Terminal", `
        <p class="muted">Interactive AI terminal - ask, torrent, search. (login: arduino / 9936468425)</p>
        <iframe src="http://127.0.0.1:7682" class="term-frame" title="TankOS Terminal"></iframe>`)}
    </div>
  </main>
  <script>
    (function () {
      var token = ${JSON.stringify(config.vpsSearchToken || "")};
      var api = "/api/system?token=" + encodeURIComponent(token);
      function fmtBytes(n) {
        if (!n) return "0 B";
        var u = ["B", "KB", "MB", "GB", "TB"], i = 0;
        while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
        return n.toFixed(1) + " " + u[i];
      }
      function fmtUptime(sec) {
        var d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
        return d + "d " + h + "h " + m + "m";
      }
      function setBar(id, pct) {
        var bar = document.getElementById(id + "-bar");
        if (bar) bar.style.width = Math.min(100, Math.max(0, pct)) + "%";
      }
      function refresh() {
        fetch(api).then(function (r) { return r.json(); }).then(function (d) {
          if (!d || !d.ok) return;
          var cpu = d.cpu || 0;
          document.getElementById("cc-cpu").textContent = cpu + "%";
          setBar("cc-cpu", cpu);
          var memPct = d.memTotal ? Math.round(((d.memTotal - d.memAvail) / d.memTotal) * 100) : 0;
          document.getElementById("cc-ram").textContent = fmtBytes(d.memTotal - d.memAvail) + " / " + fmtBytes(d.memTotal);
          setBar("cc-ram", memPct);
          var diskPct = d.diskTotal ? Math.round(((d.diskTotal - d.diskFree) / d.diskTotal) * 100) : 0;
          document.getElementById("cc-disk").textContent = fmtBytes(d.diskFree) + " free";
          setBar("cc-disk", diskPct);
          document.getElementById("cc-temp").textContent = d.temp != null ? d.temp + "°C" : "n/a";
          document.getElementById("cc-uptime").textContent = fmtUptime(d.uptime || 0);
          document.getElementById("cc-host").textContent = d.hostname || "unoq";
          document.getElementById("cc-vpnip").textContent = d.vpnIp || "down";
          document.getElementById("cc-tsip").textContent = (d.tailscale && d.tailscale.ip) || "off";
          document.getElementById("cc-tsname").textContent = (d.tailscale && d.tailscale.name) || "off";
          var svcMap = d.services || {};
          ["cloud", "aria2", "vpn", "tailscale", "tankos", "tankosWeb", "mariadb"].forEach(function (k) {
            var el = document.getElementById("s-" + k);
            if (!el) return;
            var state = svcMap[k] || "unknown";
            el.textContent = state;
            el.className = "pill " + (state === "active" ? "active" : state === "inactive" ? "paused" : "error");
          });
        }).catch(function () {});
      }
      document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-action]");
        if (!btn) return;
        var act = btn.getAttribute("data-action").split(":");
        var fd = new FormData();
        fd.append("_x", "1");
        fetch("/api/service?token=" + encodeURIComponent(token) + "&action=" + act[1] + "&target=" + act[0], { method: "POST" })
          .then(function () { setTimeout(refresh, 1200); });
      });
      refresh();
      setInterval(refresh, 4000);
    })();
  </script>`, "");

  /* end of renderControlCenter */
}

async function renderHome(req, res, user, message = "") {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const relativePath = safeRelative(url.searchParams.get("path") || "");
  const query = cleanQuery(url.searchParams.get("q") || "");
  const providers = searchProviderMap();
  const provider = providers.has(url.searchParams.get("provider")) ? url.searchParams.get("provider") : "all";
  const category = ["All", "Movies", "TV", "Games", "Music", "Applications", "Anime", "Books"].includes(url.searchParams.get("category")) ? url.searchParams.get("category") : "All";
  const [torrents, files, searchGroups, statusHtml, trending, trailers, library] = await Promise.all([
    torrentRows(user),
    fileRows(user, relativePath),
    query ? searchTorrents(query, provider, category) : Promise.resolve([]),
    systemStatusHtml(),
    query ? Promise.resolve({ movies: [], tv: [] }) : fetchTrending(),
    query ? Promise.resolve([]) : fetchTrailers(),
    query ? Promise.resolve([]) : mediaLibrary(user)
  ]);
  const providerOptions = [...providers.entries()].map(([value, label]) =>
    `<option value="${htmlEscape(value)}"${value === provider ? " selected" : ""}>${htmlEscape(label)}</option>`
  ).join("");
  const categoryOptions = ["All", "Movies", "TV", "Games", "Music", "Applications", "Anime", "Books"].map((value) =>
    `<option value="${htmlEscape(value)}"${value === category ? " selected" : ""}>${htmlEscape(value)}</option>`
  ).join("");
  const trendingRail = query ? "" : renderTrendingRail(trending, trailers);
  const libraryHtml = query ? "" : renderLibrary(library, trailers);
  send(res, 200, layout(user, `<main>
  ${message ? `<div class="notice">${htmlEscape(message)}</div>` : ""}
  ${trendingRail}
  <div class="actions" style="margin:0 0 14px">
    <a class="button" href="#add-torrent">Add Torrent</a>
    <a class="button secondary" href="#torrent-search">Search</a>
    <a class="button secondary" href="#current-downloads">Current Downloads</a>
    <a class="button secondary" href="http://213.199.61.156:9200/">All Downloads</a>
  </div>
  <div class="grid">
    <div class="stack">
      <section id="torrent-search">
        <h1>Search Torrents</h1>
        <form method="get" action="/">
          <input type="text" name="q" value="${htmlEscape(query)}" placeholder="Search torrents">
          <select name="provider">${providerOptions}</select>
          <select name="category">${categoryOptions}</select>
          <button type="submit">Search</button>
        </form>
      </section>
      ${renderSearchResults(searchGroups, query)}
      <section id="add-torrent">
        <h1>Add Torrent</h1>
        <p>Add a magnet, a torrent URL, or upload a .torrent file. Downloads are saved only in your private folder.</p>
        <form method="post" action="/add" enctype="multipart/form-data">
          <input type="text" name="uri" placeholder="magnet:?xt=... or https://...torrent">
          <input type="file" name="torrent" accept=".torrent,application/x-bittorrent">
          <button type="submit">Start Download</button>
        </form>
      </section>
      <section id="your-library">
        <h2>Your Library</h2>
        ${libraryHtml}
      </section>
      <section>
        <h2>Your Folder</h2>
        <p class="muted">${htmlEscape(userRoot(user))}</p>
      </section>
    </div>
    <div class="stack">
      <section id="current-downloads">
        <h2>Current Downloads</h2>
        ${torrents}
      </section>
      <section id="files">
        <h2>Files /${htmlEscape(relativePath)}</h2>
        <div class="table-scroll"><table><thead><tr><th>Name</th><th>Type</th><th>Size</th><th>Modified</th></tr></thead><tbody>${files}</tbody></table></div>
      </section>
    </div>
  </div>
  <script>
    setInterval(() => {
      const active = document.activeElement;
      const typing = active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
      if (!document.hidden && !typing) window.location.reload();
    }, 8000);
  </script>
</main>`, statusHtml));
}

async function handleLogin(req, res) {
  const body = await collectBody(req, 64 * 1024);
  const params = new URLSearchParams(body.toString("utf8"));
  try {
    const token = await createSession(params.get("username"));
    res.writeHead(303, {
      Location: "/",
      "Set-Cookie": `${config.cookieName}=${encodeURIComponent(token)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${60 * 60 * 24 * 30}`,
      "Cache-Control": "no-store"
    });
    res.end();
  } catch (error) {
    send(res, 400, renderLogin(error.message));
  }
}

async function handleAdd(req, res, user) {
  const body = await collectBody(req);
  const contentType = req.headers["content-type"] || "";
  const hostDir = await ensureUserDir(user);
  const aria2Dir = aria2UserRoot(user);
  let gid = "";
  let label = "";
  if (contentType.includes("multipart/form-data")) {
    const fields = parseMultipart(body, contentType);
    const uri = fields.uri?.text?.trim();
    if (uri) {
      gid = await aria2("aria2.addUri", [[uri], { dir: aria2Dir }]);
      label = uri.slice(0, 512);
    } else if (fields.torrent?.filename && fields.torrent.content.length > 0) {
      gid = await aria2("aria2.addTorrent", [fields.torrent.content.toString("base64"), [], { dir: aria2Dir }]);
      label = fields.torrent.filename;
    }
  }
  if (!gid) {
    redirect(res, "/?msg=Paste a link or choose a .torrent file");
    return;
  }
  await pool.query("INSERT INTO torrents (user_id, gid, label) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE user_id = VALUES(user_id), label = VALUES(label)", [user.id, gid, label]);
  clearCachePrefix(`torrent-rows:${user.id}`);
  clearCachePrefix(`file-rows:${user.id}:`);
  redirect(res, "/?msg=Torrent added");
}

async function handleSearchAdd(req, res, user) {
  const body = await collectBody(req, 2 * 1024 * 1024);
  const params = new URLSearchParams(body.toString("utf8"));
  const torrent = decodeSearchPayload(params.get("payload") || "", params.get("sig") || "");
  await ensureUserDir(user);
  const aria2Dir = aria2UserRoot(user);
  let gid = "";
  let label = torrent.title || torrent.name || torrent.link || torrent.desc || "search result";
  const directUri = torrent.magnet || torrent.uri || (typeof torrent.link === "string" && /^magnet:/i.test(torrent.link) ? torrent.link : "");
  if (directUri) {
    gid = await aria2("aria2.addUri", [[directUri], { dir: aria2Dir }]);
  } else {
    let magnet = "";
    if (config.vpsSearchUrl) {
      try {
        const token = config.vpsSearchToken ? `&token=${encodeURIComponent(config.vpsSearchToken)}` : "";
        const mUrl = `${config.vpsSearchUrl}/api/magnet?url=${encodeURIComponent(torrent.desc || torrent.link || "")}&title=${encodeURIComponent(torrent.title || "")}&provider=${encodeURIComponent(torrent.provider || "")}${token}`;
        const mResp = await fetch(mUrl, { signal: AbortSignal.timeout(25000) });
        const mData = await mResp.json();
        magnet = mData && mData.magnet ? mData.magnet : "";
      } catch {
        magnet = "";
      }
    }
    if (!magnet) {
      try {
        magnet = await TorrentSearchApi.getMagnet(torrent);
      } catch {
        magnet = "";
      }
    }
    if (magnet) {
      gid = await aria2("aria2.addUri", [[magnet], { dir: aria2Dir }]);
    } else {
      const torrentBuffer = await TorrentSearchApi.downloadTorrent(torrent);
      gid = await aria2("aria2.addTorrent", [Buffer.from(torrentBuffer).toString("base64"), [], { dir: aria2Dir }]);
    }
  }
  if (!gid) {
    redirect(res, "/?msg=Could not add that search result");
    return;
  }
  await pool.query("INSERT INTO torrents (user_id, gid, label) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE user_id = VALUES(user_id), label = VALUES(label)", [user.id, gid, String(label).slice(0, 512)]);
  clearCachePrefix(`torrent-rows:${user.id}`);
  clearCachePrefix(`file-rows:${user.id}:`);
  redirect(res, "/?msg=Torrent added");
}

async function handleWatch(req, res, user) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const relativePath = safeRelative(url.searchParams.get("path") || "");
  const audioParam = url.searchParams.get("audio");
  const full = absoluteFor(user, relativePath);
  const stat = await fs.promises.stat(full);
  if (stat.isDirectory()) {
    redirect(res, `/?path=${encodeURIComponent(relativePath)}`);
    return;
  }
  const type = mediaTypeFor(full);
  if (!type) {
    redirect(res, `/download?path=${encodeURIComponent(relativePath)}`);
    return;
  }
  const probe = type.startsWith("video/") ? await probeMedia(full).catch(() => null) : null;
  const requestedAudio = audioParam !== null && audioParam !== "" && Number.isFinite(Number(audioParam)) ? Number(audioParam) : "";
  const selectedAudio = requestedAudio !== "" && probe?.audio?.some((stream) => stream.globalIndex === requestedAudio || stream.index === requestedAudio)
    ? requestedAudio
    : "";
  const selectedAudioStream = selectedAudio === ""
    ? null
    : probe?.audio?.find((stream) => stream.globalIndex === selectedAudio) || probe?.audio?.find((stream) => stream.index === selectedAudio) || null;
  const selectedAudioValue = selectedAudioStream?.globalIndex ?? "";
  const source = `/media?path=${encodeURIComponent(relativePath)}${selectedAudioValue === "" ? "" : `&audio=${selectedAudioValue}`}`;
  const sourceType = selectedAudio === "" ? type : "video/mp4";
  const subtitleTracks = type.startsWith("video/") ? await subtitleTracksFor(user, relativePath) : [];
  const trackTags = subtitleTracks.map((track, index) => track.external
    ? `<track kind="subtitles" src="/subtitle?path=${encodeURIComponent(track.rel)}" label="${htmlEscape(track.label)}" srclang="und"${index === 0 && track.preferred ? " default" : ""}>`
    : `<track kind="subtitles" src="/subtitle?path=${encodeURIComponent(relativePath)}&stream=${track.stream}" label="${htmlEscape(track.label)}" srclang="und"${track.preferred ? " default" : ""}>`
  ).join("");
  const folder = parentRelative(relativePath);
  const player = type.startsWith("audio/")
    ? `<audio class="player audio" controls preload="metadata" src="${source}"></audio>`
    : `<video id="mediaPlayer" class="player" controls preload="metadata" playsinline><source src="${source}" type="${htmlEscape(sourceType)}">${trackTags}</video>`;
  const audioOptions = probe?.audio?.length
    ? `<option value=""${selectedAudioValue === "" ? " selected" : ""}>Default embedded audio</option>` +
      probe.audio.map((stream) => `<option value="${stream.globalIndex}"${selectedAudioValue === stream.globalIndex ? " selected" : ""}>${htmlEscape(streamLabel(stream, `Track ${stream.index + 1}`))}${stream.default ? " (default)" : ""}</option>`).join("")
    : `<option value="">Default</option>`;
  const subtitleOptions = subtitleTracks.length
    ? subtitleTracks.map((track, index) => `<option value="${index}"${index === 0 && track.preferred ? " selected" : ""}>${htmlEscape(track.label)}</option>`).join("")
    : `<option value="-1" disabled>No subtitle tracks found</option>`;
  const controls = type.startsWith("video/") ? `<div class="media-controls">
        <div class="control-field">
          <label for="subtitleSelect">Subtitles</label>
          <select id="subtitleSelect">
            <option value="-1">Off</option>
            ${subtitleOptions}
          </select>
        </div>
        <div class="control-field">
          <label for="audioSelect">Audio</label>
          <select id="audioSelect">${audioOptions}</select>
        </div>
      </div>` : "";
  const statusHtml = await systemStatusHtml();
  send(res, 200, layout(user, `<main>
    <section>
      <h1 class="break">${htmlEscape(path.basename(full))}</h1>
      ${player}
      ${controls}
      <div class="actions">
        <a class="button secondary" href="/?path=${encodeURIComponent(folder === "." ? "" : folder)}">Back</a>
        <a class="button" href="/download?path=${encodeURIComponent(relativePath)}">Download</a>
      </div>
      ${path.extname(full).toLowerCase() === ".mkv" ? `<p class="muted">MKV tracks are probed server-side. If the browser cannot play the codecs in this file, use Download and open it in VLC.</p>` : ""}
    </section>
    <script>
      const media = document.getElementById("mediaPlayer");
      const subtitleSelect = document.getElementById("subtitleSelect");
      const audioSelect = document.getElementById("audioSelect");
      const baseUrl = new URL(window.location.href);
      let resumeAt = 0;
      let resumePlaying = false;
      function applySubtitle() {
        if (!media || !subtitleSelect) return;
        const selected = Number(subtitleSelect.value);
        Array.from(media.textTracks || []).forEach((track, index) => {
          track.mode = index === selected ? "showing" : "disabled";
        });
      }
      subtitleSelect?.addEventListener("change", applySubtitle);
      audioSelect?.addEventListener("change", () => {
        if (!media || !audioSelect) return;
        const selected = audioSelect.value;
        const next = new URL("/media", window.location.href);
        next.searchParams.set("path", ${JSON.stringify(relativePath)});
        if (selected) next.searchParams.set("audio", selected);
        resumeAt = media.currentTime || 0;
        resumePlaying = !media.paused;
        media.querySelector("source")?.setAttribute("type", selected ? "video/mp4" : ${JSON.stringify(type)});
        media.src = next.toString();
        media.load();
        baseUrl.searchParams.delete("audio");
        if (selected) baseUrl.searchParams.set("audio", selected);
        history.replaceState(null, "", baseUrl.toString());
      });
      media?.addEventListener("loadedmetadata", () => {
        if (resumeAt > 0 && Number.isFinite(media.duration)) {
          media.currentTime = Math.min(resumeAt, Math.max(0, media.duration - 1));
          resumeAt = 0;
        }
        if (resumePlaying) {
          resumePlaying = false;
          media.play().catch(() => {});
        }
      });
      media?.addEventListener("loadedmetadata", applySubtitle);
    </script>
  </main>`, statusHtml));
}

async function handleMedia(req, res, user) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const relativePath = safeRelative(url.searchParams.get("path") || "");
  const audioParam = url.searchParams.get("audio");
  const full = absoluteFor(user, relativePath);
  const stat = await fs.promises.stat(full);
  const type = mediaTypeFor(full);
  if (stat.isDirectory() || !type) {
    send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }

  const wantsRemux = type.startsWith("video/") && audioParam !== null && audioParam !== "";
  if (wantsRemux) {
    const selectedAudio = Number(audioParam);
    if (!Number.isInteger(selectedAudio) || selectedAudio < 0) {
      send(res, 400, "Invalid audio track", { "Content-Type": "text/plain; charset=utf-8" });
      return;
    }
    const probe = await probeMedia(full).catch(() => null);
    const audioStream = probe?.audio?.find((stream) => stream.globalIndex === selectedAudio) || probe?.audio?.find((stream) => stream.index === selectedAudio);
    if (!audioStream) {
      send(res, 400, "Audio track not found", { "Content-Type": "text/plain; charset=utf-8" });
      return;
    }
    const ffmpeg = spawn("ffmpeg", [
      "-hide_banner",
      "-loglevel", "error",
      "-i", full,
      "-map", "0:v:0",
      "-map", `0:${audioStream.globalIndex}`,
      "-c:v", "copy",
      "-c:a", "aac",
      "-b:a", "192k",
      "-sn",
      "-dn",
      "-movflags", "frag_keyframe+empty_moov+default_base_moof",
      "-f", "mp4",
      "pipe:1"
    ], { stdio: ["ignore", "pipe", "pipe"] });
    const stderrChunks = [];
    ffmpeg.stderr.on("data", (chunk) => stderrChunks.push(chunk));
    req.on("close", () => ffmpeg.kill("SIGKILL"));
    res.writeHead(200, {
      "Content-Type": "video/mp4",
      "Cache-Control": "private, max-age=0",
      "Content-Disposition": `inline; filename="${path.basename(full).replaceAll('"', "")}.mp4"`
    });
    ffmpeg.stdout.pipe(res);
    ffmpeg.on("error", (error) => {
      if (!res.headersSent) {
        send(res, 500, "Failed to start ffmpeg", { "Content-Type": "text/plain; charset=utf-8" });
      } else {
        res.destroy(error);
      }
    });
    ffmpeg.on("close", (code) => {
      if (code !== 0 && !res.writableEnded) {
        const stderr = Buffer.concat(stderrChunks).toString("utf8").trim();
        if (!res.headersSent) {
          send(res, 500, stderr || "ffmpeg remux failed", { "Content-Type": "text/plain; charset=utf-8" });
        } else {
          res.destroy(new Error(stderr || "ffmpeg remux failed"));
        }
      }
    });
    return;
  }

  const common = {
    "Content-Type": type,
    "Accept-Ranges": "bytes",
    "Content-Disposition": `inline; filename="${path.basename(full).replaceAll('"', "")}"`,
    "Cache-Control": "private, max-age=0"
  };
  const range = req.headers.range;
  if (range) {
    const match = /^bytes=(\d*)-(\d*)$/.exec(range);
    if (!match) {
      res.writeHead(416, { ...common, "Content-Range": `bytes */${stat.size}` });
      res.end();
      return;
    }
    let start = match[1] ? Number(match[1]) : 0;
    let end = match[2] ? Number(match[2]) : stat.size - 1;
    if (!match[1] && match[2]) {
      const suffix = Number(match[2]);
      start = Math.max(0, stat.size - suffix);
      end = stat.size - 1;
    }
    if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || start >= stat.size) {
      res.writeHead(416, { ...common, "Content-Range": `bytes */${stat.size}` });
      res.end();
      return;
    }
    end = Math.min(end, stat.size - 1);
    res.writeHead(206, {
      ...common,
      "Content-Range": `bytes ${start}-${end}/${stat.size}`,
      "Content-Length": end - start + 1
    });
    fs.createReadStream(full, { start, end }).pipe(res);
    return;
  }

  res.writeHead(200, { ...common, "Content-Length": stat.size });
  fs.createReadStream(full).pipe(res);
}

async function handleSubtitle(req, res, user) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const relativePath = safeRelative(url.searchParams.get("path") || "");
  const embeddedStream = url.searchParams.get("stream");
  const full = absoluteFor(user, relativePath);
  const stat = await fs.promises.stat(full);
  if (stat.isDirectory()) {
    send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }
  if (embeddedStream !== null && embeddedStream !== "") {
    const index = Number(embeddedStream);
    if (!Number.isInteger(index) || index < 0) {
      send(res, 400, "Invalid subtitle track", { "Content-Type": "text/plain; charset=utf-8" });
      return;
    }
    const probe = await probeMedia(full).catch(() => null);
    const subtitleStream = probe?.subtitles?.find((stream) => stream.globalIndex === index) || probe?.subtitles?.find((stream) => stream.index === index);
    if (!subtitleStream) {
      send(res, 400, "Subtitle track not found", { "Content-Type": "text/plain; charset=utf-8" });
      return;
    }
    const ffmpeg = spawn("ffmpeg", [
      "-hide_banner",
      "-loglevel", "error",
      "-i", full,
      "-map", `0:${subtitleStream.globalIndex}`,
      "-f", "webvtt",
      "pipe:1"
    ], { stdio: ["ignore", "pipe", "pipe"] });
    const stderrChunks = [];
    ffmpeg.stderr.on("data", (chunk) => stderrChunks.push(chunk));
    req.on("close", () => ffmpeg.kill("SIGKILL"));
    res.writeHead(200, {
      "Content-Type": "text/vtt; charset=utf-8",
      "Cache-Control": "private, max-age=60"
    });
    ffmpeg.stdout.pipe(res);
    ffmpeg.on("close", (code) => {
      if (code !== 0 && !res.writableEnded) {
        const stderr = Buffer.concat(stderrChunks).toString("utf8").trim();
        if (!res.headersSent) {
          send(res, 500, stderr || "ffmpeg subtitle extract failed", { "Content-Type": "text/plain; charset=utf-8" });
        } else {
          res.destroy(new Error(stderr || "ffmpeg subtitle extract failed"));
        }
      }
    });
    return;
  }
  if (!isSubtitleFile(full)) {
    send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }
  const ext = path.extname(full).toLowerCase();
  const raw = await fs.promises.readFile(full, "utf8");
  const body = ext === ".srt" ? srtToVtt(raw) : raw.replace(/^\uFEFF/, "").startsWith("WEBVTT") ? raw : `WEBVTT\n\n${raw}`;
  res.writeHead(200, {
    "Content-Type": "text/vtt; charset=utf-8",
    "Cache-Control": "private, max-age=60",
    "Content-Length": Buffer.byteLength(body)
  });
  res.end(body);
}

async function handlePoster(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const title = cleanMediaTitle(url.searchParams.get("title") || "");
  if (!title) {
    send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }
  await fs.promises.mkdir(config.posterCacheDir, { recursive: true });
  const cachePath = path.join(config.posterCacheDir, `${posterSlug(title)}.jpg`);
  try {
    const cached = await fs.promises.readFile(cachePath);
    res.writeHead(200, {
      "Content-Type": "image/jpeg",
      "Cache-Control": "public, max-age=86400",
      "Content-Length": cached.length
    });
    res.end(cached);
    return;
  } catch {
    // Continue to lookup.
  }

  try {
    const lookup = await fetch(`https://api.tvmaze.com/search/shows?q=${encodeURIComponent(title)}`, {
      signal: AbortSignal.timeout(3500)
    });
    if (!lookup.ok) throw new Error("poster lookup failed");
    const data = await lookup.json();
    const best = Array.isArray(data) && data.length ? data[0] : null;
    if (!best || Number(best.score || 0) < 0.5) throw new Error("poster missing");
    const imageUrl = best?.show?.image?.medium || best?.show?.image?.original;
    if (!imageUrl) throw new Error("poster missing");
    const image = await fetch(imageUrl, { signal: AbortSignal.timeout(5000) });
    if (!image.ok) throw new Error("poster download failed");
    const body = Buffer.from(await image.arrayBuffer());
    await fs.promises.writeFile(cachePath, body);
    res.writeHead(200, {
      "Content-Type": image.headers.get("content-type") || "image/jpeg",
      "Cache-Control": "public, max-age=86400",
      "Content-Length": body.length
    });
    res.end(body);
    return;
  } catch {
    // Fall through to iTunes movie lookup (TVMaze only covers TV shows).
  }

  // iTunes Search API - free, keyless, covers movies.
  try {
    const itunesUrl = 'https://itunes.apple.com/search?term=' + encodeURIComponent(title) + '&country=US&limit=10';
    const itunes = await fetch(itunesUrl, {
      signal: AbortSignal.timeout(4000)
    });
    if (!itunes.ok) throw new Error("itunes lookup failed");
    const itunesData = await itunes.json();
    const movieResults = Array.isArray(itunesData.results) ? itunesData.results.filter((r) => r?.wrapperType === "movie" || r?.kind === "feature-movie") : [];
    const best = movieResults.length ? movieResults[0] : null;
    const imageUrl = best?.artworkUrl100;
    if (!imageUrl) throw new Error("itunes poster missing");
    const image = await fetch(imageUrl.replace("100x100bb", "600x600bb"), { signal: AbortSignal.timeout(5000) });
    if (!image.ok) throw new Error("itunes poster download failed");
    const body = Buffer.from(await image.arrayBuffer());
    await fs.promises.writeFile(cachePath, body);
    res.writeHead(200, {
      "Content-Type": image.headers.get("content-type") || "image/jpeg",
      "Cache-Control": "public, max-age=86400",
      "Content-Length": body.length
    });
    res.end(body);
  } catch {
    send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
  }
}

async function handleDownload(req, res, user) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const relativePath = safeRelative(url.searchParams.get("path") || "");
  const full = absoluteFor(user, relativePath);
  const stat = await fs.promises.stat(full);
  if (stat.isDirectory()) {
    redirect(res, `/?path=${encodeURIComponent(relativePath)}`);
    return;
  }
  res.writeHead(200, {
    "Content-Type": "application/octet-stream",
    "Content-Length": stat.size,
    "Content-Disposition": `attachment; filename="${path.basename(full).replaceAll('"', "")}"`
  });
  fs.createReadStream(full).pipe(res);
}

async function handleApiSettings(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (!config.vpsSearchToken || url.searchParams.get("token") !== config.vpsSearchToken) {
    send(res, 401, "Unauthorized", { "Content-Type": "text/plain; charset=utf-8" });
    return;
  }
  try {
    const providersResult = await cachedValue("settings:providers", 30000, () => runTankOs(["--providers"]));
    const devicesResult = await cachedValue("settings:devices", 15000, () => runTankOs(["--devices"]));
    const custom = readJsonFile(CUSTOM_PROVIDERS_FILE, { providers: [] });
    send(res, 200, JSON.stringify({
      ok: true,
      app: appSettings(),
      envFile: TANK_ENV_FILE,
      providers: providersResult.providers || [],
      customProviders: Array.isArray(custom.providers) ? custom.providers : [],
      devices: devicesResult.devices || {},
      devicesError: devicesResult.error || null
    }), { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), { "Content-Type": "application/json; charset=utf-8" });
  }
}

async function handleApiSettingsLlm(req, res) {
  let data = {};
  try { data = JSON.parse((await collectBody(req, 128 * 1024)).toString("utf8") || "{}"); } catch {}
  const updates = {};
  for (const [k, v] of Object.entries(data.keys || {})) {
    if (typeof v === "string") updates[k.toUpperCase()] = v.trim();
  }
  if (!Object.keys(updates).length) {
    send(res, 400, JSON.stringify({ ok: false, error: "no keys provided" }), { "Content-Type": "application/json; charset=utf-8" });
    return;
  }
  try {
    updateEnvFile(updates);
    clearCachePrefix("settings:providers");
    const restarts = await restartTankTerminals();
    send(res, 200, JSON.stringify({ ok: true, saved: Object.keys(updates), restarts }), { "Content-Type": "application/json; charset=utf-8" });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), { "Content-Type": "application/json; charset=utf-8" });
  }
}

async function handleApiSettingsCustom(req, res) {
  let data = {};
  try { data = JSON.parse((await collectBody(req, 128 * 1024)).toString("utf8") || "{}"); } catch {}
  const name = String(data.name || "").trim().toLowerCase().replace(/\s+/g, "-");
  const baseUrl = String(data.baseUrl || "").trim();
  const model = String(data.model || "").trim() || "gpt-4o-mini";
  const key = String(data.key || "").trim();
  const remove = data.remove === true;
  if (!name || (!remove && (!baseUrl || !key))) {
    send(res, 400, JSON.stringify({ ok: false, error: "name, base URL and key are required" }), { "Content-Type": "application/json; charset=utf-8" });
    return;
  }
  try {
    const file = readJsonFile(CUSTOM_PROVIDERS_FILE, { providers: [] });
    let list = Array.isArray(file.providers) ? file.providers : [];
    const keyEnv = name.toUpperCase().replace(/-/g, "_") + "_API_KEY";
    if (remove) {
      list = list.filter((p) => p.name !== name);
      updateEnvFile({ [keyEnv]: "" });
    } else {
      const entry = { name, baseUrl, keyEnv, model };
      const idx = list.findIndex((p) => p.name === name);
      if (idx >= 0) list[idx] = entry; else list.push(entry);
      updateEnvFile({ [keyEnv]: key });
    }
    fs.writeFileSync(CUSTOM_PROVIDERS_FILE, JSON.stringify({ providers: list }, null, 2), { mode: 0o600 });
    clearCachePrefix("settings:providers");
    const restarts = await restartTankTerminals();
    send(res, 200, JSON.stringify({ ok: true, name, remove, restarts }), { "Content-Type": "application/json; charset=utf-8" });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), { "Content-Type": "application/json; charset=utf-8" });
  }
}

async function handleApiSettingsTest(req, res) {
  let data = {};
  try { data = JSON.parse((await collectBody(req, 128 * 1024)).toString("utf8") || "{}"); } catch {}
  const provider = String(data.provider || "").trim();
  const message = String(data.message || "Reply with OK").trim();
  if (!provider) {
    send(res, 400, JSON.stringify({ ok: false, error: "provider required" }), { "Content-Type": "application/json; charset=utf-8" });
    return;
  }
  const result = await runTankOs(["--test", provider, message], 90000);
  send(res, 200, JSON.stringify(result), { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
}

async function handleApiSettingsGeneral(req, res) {
  let data = {};
  try { data = JSON.parse((await collectBody(req, 128 * 1024)).toString("utf8") || "{}"); } catch {}
  const allowed = ["brandName", "defaultProvider", "temperature", "maxTokens", "searchProviders", "aria2Rpc", "vpsSearchUrl"];
  const patch = {};
  for (const k of allowed) {
    if (k in data) patch[k] = typeof data[k] === "string" ? data[k].trim() : data[k];
  }
  try {
    const saved = saveAppSettings(patch);
    send(res, 200, JSON.stringify({ ok: true, saved }), { "Content-Type": "application/json; charset=utf-8" });
  } catch (error) {
    send(res, 500, JSON.stringify({ ok: false, error: String(error && error.message || error) }), { "Content-Type": "application/json; charset=utf-8" });
  }
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (req.method === "GET" && url.pathname === "/login") {
      send(res, 200, renderLogin());
      return;
    }
    if (req.method === "POST" && url.pathname === "/login") {
      await handleLogin(req, res);
      return;
    }
    if (req.method === "GET" && url.pathname === "/api/system") {
      await handleApiSystem(req, res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/service") {
      await handleApiService(req, res);
      return;
    }
    if (req.method === "GET" && url.pathname === "/api/library-titles") {
      const url2 = new URL(req.url, `http://${req.headers.host}`);
      if (!config.vpsSearchToken || url2.searchParams.get("token") !== config.vpsSearchToken) {
        send(res, 401, "Unauthorized", { "Content-Type": "text/plain; charset=utf-8" });
        return;
      }
      const items = await mediaLibrary({ username: "shashi", slug: "shashi" });
      const titles = items.map((it) => it.title).filter(Boolean).slice(0, 200);
      send(res, 200, JSON.stringify({ ok: true, titles }), {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store"
      });
      return;
    }
    let user = await getSessionUser(req);
    if (!user) {
      if (config.publicMode) {
        user = { id: 0, username: "guest", slug: "guest" };
      } else {
        redirect(res, "/login");
        return;
      }
    }
    if (req.method === "GET" && url.pathname === "/logout") {
      await destroySession(req);
      res.writeHead(303, {
        Location: "/login",
        "Set-Cookie": `${config.cookieName}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`,
        "Cache-Control": "no-store"
      });
      res.end();
      return;
    }
    if (req.method === "POST" && url.pathname === "/add") {
      await handleAdd(req, res, user);
      return;
    }
    if (req.method === "POST" && url.pathname === "/search-add") {
      await handleSearchAdd(req, res, user);
      return;
    }
    if (req.method === "GET" && url.pathname === "/watch") {
      await handleWatch(req, res, user);
      return;
    }
    if (req.method === "GET" && url.pathname === "/media") {
      await handleMedia(req, res, user);
      return;
    }
    if (req.method === "GET" && url.pathname === "/subtitle") {
      await handleSubtitle(req, res, user);
      return;
    }
    if (req.method === "GET" && url.pathname === "/control") {
      send(res, 200, renderControlCenter(user));
      return;
    }
    if (req.method === "GET" && url.pathname === "/settings") {
      send(res, 200, renderSettingsPage(user));
      return;
    }
    if (req.method === "GET" && url.pathname === "/remote") {
      send(res, 200, renderRemotePage(user));
      return;
    }
    if (url.pathname.startsWith("/api/tv/")) {
      await handleApiTv(req, res);
      return;
    }
    if (req.method === "GET" && url.pathname === "/api/settings") {
      await handleApiSettings(req, res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/settings/llm") {
      await handleApiSettingsLlm(req, res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/settings/custom") {
      await handleApiSettingsCustom(req, res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/settings/test-llm") {
      await handleApiSettingsTest(req, res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/api/settings/general") {
      await handleApiSettingsGeneral(req, res);
      return;
    }
    if (req.method === "GET" && url.pathname === "/poster") {
      await handlePoster(req, res);
      return;
    }
    if (req.method === "GET" && url.pathname === "/download") {
      await handleDownload(req, res, user);
      return;
    }
    if (req.method === "GET" && url.pathname === "/") {
      await renderHome(req, res, user, url.searchParams.get("msg") || "");
      return;
    }
    send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
  } catch (error) {
    send(res, 500, layout(null, `<main><section><h1>Error</h1><pre>${htmlEscape(error.stack || error.message)}</pre></section></main>`));
  }
});

async function main() {
  await fs.promises.mkdir(config.downloadsDir, { recursive: true, mode: 0o777 });
  await fs.promises.chmod(config.downloadsDir, 0o777);
  await initDb();
  setTimeout(() => {
    systemStatusHtml().catch(() => {});
  }, 1000);
  server.listen(config.port, config.host, () => {
    console.log(JSON.stringify({
      message: "Torrent Cloud started",
      host: config.host,
      port: config.port,
      downloadsDir: config.downloadsDir,
      aria2DownloadsDir: config.aria2DownloadsDir,
      dbHost: config.dbHost,
      dbPort: config.dbPort
    }));
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
