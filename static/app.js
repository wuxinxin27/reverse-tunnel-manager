"use strict";

/* ================= 双语 ================= */

const I18N = {
  zh: {
    "app.title": "反向隧道管理器",
    "btn.start_all": "全部启动", "btn.stop_all": "全部停止", "btn.new": "＋ 新建隧道",
    "btn.settings": "设置", "btn.save": "保存", "btn.cancel": "取消", "btn.close": "关闭",
    "log.title": "日志", "log.title_of": "日志 · {0}", "log.autoscroll": "自动滚动", "log.clear": "清空视图",
    "summary": "共 {0} 条隧道 · 运行中 {1} · 重连中 {2} · 错误 {3} · 已停止 {4}",
    "state.stopped": "已停止", "state.starting": "连接中", "state.running": "运行中",
    "state.retry": "重连中", "state.error": "错误",
    "server.alias": "别名 {0}",
    "card.started_ago": "已运行 {0}", "card.pid": "ssh PID {0}", "card.retries": "重试 {0} 次",
    "card.no_auto_reconnect": "未启用自动重连",
    "card.start": "▶ 启动", "card.stop": "■ 停止", "card.restart": "⟳ 重启",
    "card.edit": "✎ 编辑", "card.dup": "⧉ 复制", "card.del": "🗑 删除", "card.reset": "清零",
    "card.reset_title": "清零这条隧道的流量统计（含图表与持久化记录）",
    "card.today": "今日", "card.total": "累计",
    "card.traffic_tip": "隧道总流量（上下行合计）；今日/累计为持久化统计（重启不丢），基于 ssh 进程 I/O",
    "card.chart_left": "← 最近 10 分钟", "card.chart_right": "每柱 ≈10 秒 · 峰值 {0}/s",
    "card.chart_tip": "{0} · 合计 {1}（约 {2}/s）",
    "card.proxy_down": "⚠ 本机代理 {0} 未监听（隧道已就绪，代理启动后即通）",
    "empty.tunnels": "还没有隧道。点击右上角「＋ 新建隧道」开始配置。",
    "toast.started_all": "已启动全部隧道", "toast.stopped_all": "已停止全部隧道",
    "toast.saved_restart": "已保存（运行中的隧道需要重启后生效）", "toast.created": "已创建隧道",
    "toast.deleted": "已删除「{0}」",
    "toast.name_required": "请填写名称",
    "toast.alias_required": "请选择 SSH 别名（可先点“刷新”或检查 ~/.ssh/config）",
    "toast.host_required": "请填写服务器地址",
    "toast.need_rule": "至少需要一条转发规则",
    "toast.bad_rport": "远端端口不合法：{0}",
    "toast.bad_target": "本机目标格式应为 host:port：{0}",
    "toast.parse_first": "请先粘贴 ssh 命令", "toast.parse_fail": "没能从命令里解析出主机地址",
    "toast.parsed": "已解析：{0}",
    "toast.imported": "配置已导入", "confirm.import": "导入会覆盖当前所有隧道配置（先停止全部隧道），继续？",
    "toast.settings_saved": "设置已保存",
    "confirm.delete": "确定删除隧道「{0}」吗？（会先停止它）",
    "confirm.quit": "停止全部隧道并退出工具？（退出后隧道将全部断开）",
    "editor.title_new": "新建隧道", "editor.title_edit": "编辑隧道",
    "editor.name": "名称", "editor.name_ph": "例如：sensecore-A100",
    "editor.note": "备注（可选）", "editor.note_ph": "例如：GPU 训练机",
    "editor.connect": "连接方式",
    "editor.mode_custom": "自定义主机", "editor.mode_alias": "使用 ~/.ssh/config 别名",
    "editor.host": "服务器地址（host 或 IP）", "editor.host_ph": "例如：192.168.1.100",
    "editor.ssh_port": "SSH 端口", "editor.user": "用户名", "editor.user_ph": "例如：root",
    "editor.identity": "私钥文件（可留空，使用默认 ~/.ssh/ 下的密钥）", "editor.identity_ph": "例如：~/.ssh/id_rsa",
    "editor.hostkey": "主机密钥检查",
    "editor.hostkey_accept": "accept-new（首次自动记录到工具专用 known_hosts，推荐）",
    "editor.hostkey_no": "no（不检查，适合主机密钥会变化的临时平台）",
    "editor.hostkey_yes": "yes（严格校验）",
    "editor.parse": "从 SSH 命令解析（粘贴平台给的 ssh 命令）", "editor.parse_ph": "例如：ssh -p 2222 user@198.51.100.10",
    "editor.parse_btn": "解析并填充",
    "editor.alias": "主机别名", "editor.alias_refresh": "刷新",
    "editor.alias_hint": "别名中若自带 RemoteForward 转发，本工具会自动忽略它，只用下面配置的规则。",
    "editor.rules": "转发规则（远端端口 → 本机目标）", "editor.add_rule": "＋ 添加规则",
    "editor.rules_hint": "远端访问 127.0.0.1:远端端口 时，会经由隧道连到“本机目标”。远端绑定地址一般留空即可（默认只绑回环地址）。",
    "editor.advanced": "高级", "editor.extra_args": "额外 ssh 参数（可选，直接追加到命令行）",
    "editor.extra_args_ph": "例如：-o Compression=yes",
    "editor.auto_reconnect": "断线自动重连", "editor.auto_start": "工具启动时自动启动",
    "editor.test": "测试连接", "editor.testing": "测试中…（最长约 45 秒）",
    "editor.test_ok": "✅ SSH 连接成功，认证正常", "editor.test_fail": "❌ 连接失败：{0}",
    "editor.raw": "--- 原始输出 ---",
    "editor.port_free": "✔ 远端端口 {0}：空闲", "editor.port_busy": "⚠ 远端端口 {0}：已被占用",
    "rules.bind": "远端绑定地址（一般留空）", "rules.bind_ph": "远端绑定地址(可空)",
    "rules.port": "远端端口", "rules.target": "本机目标 host:port", "rules.target_ph": "本机目标，如 127.0.0.1:7890",
    "settings.title": "设置",
    "settings.retry": "重连间隔（秒）", "settings.ui_port": "Web 界面端口（重启工具后生效）",
    "settings.theme": "主题", "settings.theme_auto": "跟随系统", "settings.theme_dark": "深色", "settings.theme_light": "浅色",
    "settings.language": "语言", "settings.lang_auto": "跟随系统",
    "settings.extra_args": "额外 ssh 参数（追加到所有隧道命令）", "settings.extra_args_ph": "例如：-o IdentitiesOnly=yes",
    "settings.auto_start": "启动工具时自动启动已勾选“随工具启动”的隧道",
    "settings.autostart": "开机自动运行本工具",
    "settings.notify": "断线 / 重连等事件发送系统通知",
    "settings.proxy_check": "定期检查本机代理端口是否在监听",
    "settings.update_check": "启动时自动检查新版本",
    "settings.export": "导出配置", "settings.import": "导入配置", "settings.check_update": "检查更新",
    "settings.quit": "停止全部并退出工具", "settings.save": "保存设置",
    "settings.about": "版本 {0}",
    "settings.checking": "检查中…", "settings.up_to_date": "已是最新版本",
    "settings.update_available": "发现新版本 {0}",
    "settings.check_failed": "检查失败：{0}",
    "update.banner": "🎉 新版本 {0} · 点此查看",
    "offline": "与工具后端失去连接 —— 如果工具已退出，请重新运行 app.py",
    "tray.unavailable": "⚠ 系统托盘不可用：关闭或最小化窗口将退出。详见 logs/desktop.log",
    "time.h": "{0} 小时 {1} 分", "time.m": "{0} 分 {1} 秒", "time.s": "{0} 秒",
    "ago.seconds": "{0} 秒前", "ago.minutes": "{0} 分钟前",
  },
  en: {
    "app.title": "Reverse Tunnel Manager",
    "btn.start_all": "Start all", "btn.stop_all": "Stop all", "btn.new": "＋ New tunnel",
    "btn.settings": "Settings", "btn.save": "Save", "btn.cancel": "Cancel", "btn.close": "Close",
    "log.title": "Log", "log.title_of": "Log · {0}", "log.autoscroll": "Auto-scroll", "log.clear": "Clear",
    "summary": "{0} tunnels · {1} running · {2} reconnecting · {3} error(s) · {4} stopped",
    "state.stopped": "Stopped", "state.starting": "Connecting", "state.running": "Running",
    "state.retry": "Reconnecting", "state.error": "Error",
    "server.alias": "alias {0}",
    "card.started_ago": "up {0}", "card.pid": "ssh PID {0}", "card.retries": "{0} retries",
    "card.no_auto_reconnect": "auto-reconnect off",
    "card.start": "▶ Start", "card.stop": "■ Stop", "card.restart": "⟳ Restart",
    "card.edit": "✎ Edit", "card.dup": "⧉ Duplicate", "card.del": "🗑 Delete", "card.reset": "Reset",
    "card.reset_title": "Reset traffic stats for this tunnel (chart and persisted totals)",
    "card.today": "Today", "card.total": "Total",
    "card.traffic_tip": "Total traffic (up+down). Today/Total are persisted across restarts; measured from the ssh process I/O",
    "card.chart_left": "← last 10 minutes", "card.chart_right": "≈10 s/bar · peak {0}/s",
    "card.chart_tip": "{0} · {1} (≈{2}/s)",
    "card.proxy_down": "⚠ local proxy {0} is not listening (tunnel is fine; it works once the proxy is up)",
    "empty.tunnels": "No tunnels yet. Click “＋ New tunnel” to get started.",
    "toast.started_all": "All tunnels started", "toast.stopped_all": "All tunnels stopped",
    "toast.saved_restart": "Saved (restart running tunnels to apply)", "toast.created": "Tunnel created",
    "toast.deleted": "Deleted “{0}”",
    "toast.name_required": "Please enter a name",
    "toast.alias_required": "Please pick an SSH alias (click Refresh or check ~/.ssh/config)",
    "toast.host_required": "Please enter the server address",
    "toast.need_rule": "At least one forwarding rule is required",
    "toast.bad_rport": "Invalid remote port: {0}",
    "toast.bad_target": "Local target must be host:port: {0}",
    "toast.parse_first": "Paste an ssh command first", "toast.parse_fail": "Could not parse a host from the command",
    "toast.parsed": "Parsed: {0}",
    "toast.imported": "Config imported", "confirm.import": "Importing will replace all tunnels (they will be stopped first). Continue?",
    "toast.settings_saved": "Settings saved",
    "confirm.delete": "Delete tunnel “{0}”? (it will be stopped first)",
    "confirm.quit": "Stop all tunnels and quit? (all connections will be closed)",
    "editor.title_new": "New tunnel", "editor.title_edit": "Edit tunnel",
    "editor.name": "Name", "editor.name_ph": "e.g. sensecore-A100",
    "editor.note": "Note (optional)", "editor.note_ph": "e.g. GPU box",
    "editor.connect": "Connection",
    "editor.mode_custom": "Custom host", "editor.mode_alias": "Use ~/.ssh/config alias",
    "editor.host": "Server address (host or IP)", "editor.host_ph": "e.g. 192.168.1.100",
    "editor.ssh_port": "SSH port", "editor.user": "User", "editor.user_ph": "e.g. root",
    "editor.identity": "Private key file (optional; defaults to keys in ~/.ssh/)", "editor.identity_ph": "e.g. ~/.ssh/id_rsa",
    "editor.hostkey": "Host key policy",
    "editor.hostkey_accept": "accept-new (trust on first use, tool-private known_hosts; recommended)",
    "editor.hostkey_no": "no (skip checking; for ephemeral platforms with rotating host keys)",
    "editor.hostkey_yes": "yes (strict)",
    "editor.parse": "Parse an ssh command (paste the one from your platform)", "editor.parse_ph": "e.g. ssh -p 2222 user@198.51.100.10",
    "editor.parse_btn": "Parse & fill",
    "editor.alias": "Host alias", "editor.alias_refresh": "Refresh",
    "editor.alias_hint": "RemoteForward entries from the alias are ignored; only the rules below are used.",
    "editor.rules": "Forwarding rules (remote port → local target)", "editor.add_rule": "＋ Add rule",
    "editor.rules_hint": "Connections to 127.0.0.1:<remote port> on the server are tunneled to the local target. Leave bind address empty (loopback only).",
    "editor.advanced": "Advanced", "editor.extra_args": "Extra ssh arguments (optional)",
    "editor.extra_args_ph": "e.g. -o Compression=yes",
    "editor.auto_reconnect": "Auto-reconnect", "editor.auto_start": "Start with the app",
    "editor.test": "Test connection", "editor.testing": "Testing… (up to 45 s)",
    "editor.test_ok": "✅ SSH connection OK", "editor.test_fail": "❌ Failed: {0}",
    "editor.raw": "--- raw output ---",
    "editor.port_free": "✔ remote port {0}: free", "editor.port_busy": "⚠ remote port {0}: busy",
    "rules.bind": "Bind address (usually empty)", "rules.bind_ph": "bind address (optional)",
    "rules.port": "Remote port", "rules.target": "Local target host:port", "rules.target_ph": "e.g. 127.0.0.1:7890",
    "settings.title": "Settings",
    "settings.retry": "Retry interval (seconds)", "settings.ui_port": "Web UI port (restart to apply)",
    "settings.theme": "Theme", "settings.theme_auto": "System", "settings.theme_dark": "Dark", "settings.theme_light": "Light",
    "settings.language": "Language", "settings.lang_auto": "System",
    "settings.extra_args": "Extra ssh arguments (appended to every tunnel)", "settings.extra_args_ph": "e.g. -o IdentitiesOnly=yes",
    "settings.auto_start": "Start tunnels marked “start with the app” on launch",
    "settings.autostart": "Launch the app at login",
    "settings.notify": "Show system notifications on disconnect / reconnect",
    "settings.proxy_check": "Periodically check the local proxy port",
    "settings.update_check": "Check for updates on launch",
    "settings.export": "Export config", "settings.import": "Import config", "settings.check_update": "Check update",
    "settings.quit": "Stop all & quit", "settings.save": "Save settings",
    "settings.about": "version {0}",
    "settings.checking": "Checking…", "settings.up_to_date": "Up to date",
    "settings.update_available": "New version {0} available",
    "settings.check_failed": "Check failed: {0}",
    "update.banner": "🎉 New version {0} · click here",
    "offline": "Backend unreachable — restart the app if it was closed",
    "tray.unavailable": "⚠ System tray unavailable: closing or minimizing will quit. See logs/desktop.log",
    "time.h": "{0}h {1}m", "time.m": "{0}m {1}s", "time.s": "{0}s",
    "ago.seconds": "{0}s ago", "ago.minutes": "{0}m ago",
  },
};

let LANG = "zh";

function t(key, ...args) {
  const s = (I18N[LANG] && I18N[LANG][key]) ?? I18N.zh[key] ?? key;
  return args.length ? String(s).replace(/\{(\d+)\}/g, (_, i) => args[i]) : s;
}

function applyStaticI18n() {
  document.querySelectorAll("[data-i18n]").forEach((elm) => { elm.textContent = t(elm.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((elm) => { elm.placeholder = t(elm.dataset.i18nPh); });
  document.querySelectorAll("[data-i18n-title]").forEach((elm) => { elm.title = t(elm.dataset.i18nTitle); });
}

function resolveLang(setting) {
  if (setting === "zh" || setting === "en") return setting;
  return (navigator.language || "zh").toLowerCase().startsWith("zh") ? "zh" : "en";
}

/* ================= 主题 ================= */

function resolveTheme(setting) {
  if (setting === "light" || setting === "dark") return setting;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(setting) {
  document.documentElement.dataset.theme = resolveTheme(setting);
}

if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
    if (S.settings.theme === "auto" || !S.settings.theme) applyTheme("auto");
  });
}

/* ================= 工具函数 ================= */

const $ = (sel) => document.querySelector(sel);

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function toast(msg, type = "info") {
  const box = el("div", "toast " + type, msg);
  $("#toasts").appendChild(box);
  setTimeout(() => box.remove(), 4200);
}

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  let data = null;
  try { data = await res.json(); } catch (e) { /* ignore */ }
  if (!res.ok) throw new Error((data && data.error) || ("HTTP " + res.status));
  return data;
}

function fmtUptime(sec) {
  if (!sec) return "—";
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  if (h) return t("time.h", h, m);
  if (m) return t("time.m", m, s);
  return t("time.s", s);
}

function fmtBytes(n) {
  if (n === null || n === undefined || isNaN(n)) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = Number(n), i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return (i === 0 ? Math.round(v) : v.toFixed(1)) + " " + units[i];
}

function timeAgo(ts) {
  const sec = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (sec < 90) return t("ago.seconds", sec);
  return t("ago.minutes", Math.round(sec / 60));
}

/* ================= 流量柱状图 ================= */

const CHART_SAMPLES_PER_BAR = 5;   // 5 × ~2 秒 ≈ 10 秒/柱
const CHART_BAR_COUNT = 60;        // 60 柱 ≈ 10 分钟

function aggregateBars(history, samplesPerBar, maxBars) {
  // history: [[timestamp, bytes], ...]
  const vals = Array.isArray(history) ? history : [];
  const bars = [];
  for (let end = vals.length; end > 0 && bars.length < maxBars; end -= samplesPerBar) {
    const start = Math.max(0, end - samplesPerBar);
    let sum = 0;
    for (let i = start; i < end; i++) sum += Number(vals[i][1]) || 0;
    const last = vals[end - 1];
    bars.push({ t: Number(last[0]) || 0, v: sum });
  }
  bars.reverse();
  return bars;
}

function drawChart(canvas, bars) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  const max = Math.max(1, ...bars.map((b) => b.v));
  const bw = w / CHART_BAR_COUNT;
  ctx.fillStyle = "rgba(76, 141, 255, 0.18)";
  ctx.fillRect(0, h - 6, w, 2);
  for (let i = 0; i < bars.length; i++) {
    const v = bars[i].v;
    const x = w - (bars.length - i) * bw;
    const bh = Math.max(v > 0 ? 5 : 1.5, (v / max) * (h - 14));
    const alpha = 0.4 + 0.6 * (v / max);
    ctx.fillStyle = `rgba(76, 141, 255, ${alpha.toFixed(2)})`;
    ctx.fillRect(x + 1.5, h - bh - 6, Math.max(2, bw - 3), bh);
  }
  canvas._bars = bars;
}

/* ================= 全局状态 ================= */

const S = {
  tunnels: [],
  settings: {},
  version: "",
  update: null,
  selectedId: null,
  logTotal: 0,
  logLines: [],
  editingId: null,
  updateToastShown: false,
  trayWarnShown: false,
};

/* ================= 状态轮询与渲染 ================= */

async function loadState() {
  try {
    const data = await api("/api/state");
    S.tunnels = data.tunnels || [];
    S.settings = data.settings || {};
    S.version = data.version || "";
    S.update = data.update || null;
    if (data.tray === false && !S.trayWarnShown) {
      S.trayWarnShown = true;
      toast(t("tray.unavailable"), "error");
    }
    applyTheme(S.settings.theme || "auto");
    const lang = resolveLang(S.settings.language || "auto");
    if (lang !== LANG) {
      LANG = lang;
      applyStaticI18n();
    }
    $("#offline").classList.add("hidden");
    renderUpdateBanner();
    renderList();
    renderSummary();
    if (S.selectedId && !S.tunnels.some((x) => x.id === S.selectedId)) selectTunnel(null);
  } catch (e) {
    $("#offline").classList.remove("hidden");
  }
}

function renderUpdateBanner() {
  const banner = $("#update-banner");
  const u = S.update;
  if (u && u.has_update && u.latest) {
    banner.href = u.asset_url || u.url || "#";
    banner.textContent = t("update.banner", "v" + u.latest);
    banner.classList.remove("hidden");
    if (!S.updateToastShown) {
      S.updateToastShown = true;
      toast(t("settings.update_available", "v" + u.latest), "success");
    }
  } else {
    banner.classList.add("hidden");
  }
}

function renderSummary() {
  const counts = { running: 0, retry: 0, error: 0, other: 0 };
  for (const x of S.tunnels) {
    if (x.state === "running") counts.running++;
    else if (x.state === "retry" || x.state === "starting") counts.retry++;
    else if (x.state === "error") counts.error++;
    else counts.other++;
  }
  $("#summary").textContent = t("summary", S.tunnels.length, counts.running, counts.retry, counts.error, counts.other);
}

function serverText(x) {
  return x.mode === "alias" ? t("server.alias", x.alias || "?") : `${x.user ? x.user + "@" : ""}${x.host || "?"}:${x.port || 22}`;
}

function renderList() {
  const box = $("#tunnels");
  box.textContent = "";
  if (!S.tunnels.length) {
    box.appendChild(el("div", "empty", t("empty.tunnels")));
    return;
  }
  for (const x of S.tunnels) box.appendChild(renderCard(x));
}

function renderCard(x) {
  const card = el("div", "card" + (x.id === S.selectedId ? " selected" : ""));
  card.addEventListener("click", () => selectTunnel(x.id));

  const top = el("div", "card-top");
  top.appendChild(el("div", "card-name", x.name));
  const badge = el("span", "badge " + x.state);
  badge.appendChild(el("span", "dot"));
  badge.appendChild(document.createTextNode(t("state." + x.state) || x.state));
  top.appendChild(badge);
  top.appendChild(el("div", "card-server", serverText(x)));
  card.appendChild(top);

  const rules = el("div", "card-rules");
  for (const r of x.rules || []) {
    const bind = r.bind ? r.bind + ":" : "";
    rules.appendChild(el("span", "chip", `${bind}${r.remote_port} → ${r.local_target}`));
  }
  card.appendChild(rules);

  const meta = el("div", "card-meta");
  if (x.state === "running") meta.appendChild(el("span", null, t("card.started_ago", fmtUptime(x.uptime))));
  if (x.pid) meta.appendChild(el("span", null, t("card.pid", x.pid)));
  if (x.retries) meta.appendChild(el("span", null, t("card.retries", x.retries)));
  if (!x.auto_reconnect) meta.appendChild(el("span", null, t("card.no_auto_reconnect")));
  card.appendChild(meta);

  // 流量统计行：实时速率 + 今日 / 累计（持久化）
  const traffic = el("div", "card-traffic");
  const tspan = el("span", null,
    `⇅ ${fmtBytes(x.rate)}/s · ${t("card.today")} ${fmtBytes(x.traffic_today)} · ${t("card.total")} ${fmtBytes(x.traffic_total)}`);
  tspan.title = t("card.traffic_tip");
  traffic.appendChild(tspan);
  const resetT = el("button", "btn tiny", t("card.reset"));
  resetT.title = t("card.reset_title");
  resetT.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    try { await api(`/api/tunnels/${x.id}/traffic_reset`, { method: "POST" }); await loadState(); }
    catch (e) { toast(e.message, "error"); }
  });
  traffic.appendChild(resetT);
  card.appendChild(traffic);

  // 柱状图 + 悬停提示
  const hist = Array.isArray(x.history) ? x.history : [];
  const bars = aggregateBars(hist, CHART_SAMPLES_PER_BAR, CHART_BAR_COUNT);
  const wrap = el("div", "chart-wrap");
  const chart = document.createElement("canvas");
  chart.className = "traffic-chart";
  chart.width = 1200;
  chart.height = 96;
  wrap.appendChild(chart);
  const tip = el("div", "chart-tip hidden");
  wrap.appendChild(tip);
  card.appendChild(wrap);
  drawChart(chart, bars);
  const note = el("div", "chart-note");
  note.appendChild(el("span", null, t("card.chart_left")));
  const peak = bars.length ? Math.max(...bars.map((b) => b.v)) : 0;
  note.appendChild(el("span", null, t("card.chart_right", fmtBytes(peak / 10))));
  card.appendChild(note);

  chart.addEventListener("mousemove", (ev) => {
    const my = chart._bars || [];
    if (!my.length) return;
    const rect = chart.getBoundingClientRect();
    const bw = rect.width / CHART_BAR_COUNT;
    const fromRight = Math.floor((rect.right - ev.clientX) / bw);
    const idx = my.length - 1 - fromRight;
    if (idx < 0 || idx >= my.length) { tip.classList.add("hidden"); return; }
    const b = my[idx];
    tip.textContent = t("card.chart_tip", timeAgo(b.t), fmtBytes(b.v), fmtBytes(b.v / 10));
    tip.classList.remove("hidden");
    const wrapRect = wrap.getBoundingClientRect();
    tip.style.left = Math.max(0, Math.min(ev.clientX - wrapRect.left + 10, wrapRect.width - 220)) + "px";
  });
  chart.addEventListener("mouseleave", () => tip.classList.add("hidden"));

  // 本机代理健康警示
  if (x.state === "running" && x.target_ok === false) {
    card.appendChild(el("div", "card-detail", t("card.proxy_down", x.target_info || "127.0.0.1:7890")));
  } else if (x.detail) {
    card.appendChild(el("div", "card-detail" + (x.state === "error" || x.state === "retry" ? " error" : ""), x.detail));
  }
  if (x.note) card.appendChild(el("div", "card-note", x.note));

  const actions = el("div", "card-actions");
  const mkBtn = (label, cls, fn) => {
    const b = el("button", "btn tiny " + (cls || ""), label);
    b.addEventListener("click", (ev) => { ev.stopPropagation(); fn(); });
    return b;
  };
  const active = x.state === "running" || x.state === "starting" || x.state === "retry";
  if (active) actions.appendChild(mkBtn(t("card.stop"), "", () => act(x.id, "stop")));
  else actions.appendChild(mkBtn(t("card.start"), "primary", () => act(x.id, "start")));
  if (active) actions.appendChild(mkBtn(t("card.restart"), "", () => act(x.id, "restart")));
  actions.appendChild(mkBtn(t("card.edit"), "", () => openEditor(x)));
  actions.appendChild(mkBtn(t("card.dup"), "", () => act(x.id, "duplicate")));
  actions.appendChild(mkBtn(t("card.del"), "danger", () => removeTunnel(x)));
  card.appendChild(actions);

  return card;
}

async function act(id, action) {
  try {
    await api(`/api/tunnels/${id}/${action}`, { method: "POST" });
    await loadState();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function removeTunnel(x) {
  if (!confirm(t("confirm.delete", x.name))) return;
  try {
    await api(`/api/tunnels/${x.id}`, { method: "DELETE" });
    toast(t("toast.deleted", x.name), "success");
    if (S.selectedId === x.id) selectTunnel(null);
    await loadState();
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ================= 日志 ================= */

function selectTunnel(id) {
  S.selectedId = id;
  S.logTotal = 0;
  S.logLines = [];
  const x = S.tunnels.find((v) => v.id === id);
  $("#log-title").textContent = x ? t("log.title_of", x.name) : t("log.title");
  $("#logview").textContent = "";
  renderList();
  if (id) fetchLogs();
}

async function fetchLogs() {
  if (!S.selectedId) return;
  const id = S.selectedId;
  try {
    const data = await api(`/api/logs/${id}?since=${S.logTotal}`);
    if (id !== S.selectedId) return; // 期间切换了选中隧道，丢弃过期响应
    if (data.lines && data.lines.length) {
      S.logLines.push(...data.lines);
      if (S.logLines.length > 3000) S.logLines = S.logLines.slice(-2000);
      S.logTotal = data.total;
      const view = $("#logview");
      view.textContent = S.logLines.join("\n");
      if ($("#log-autoscroll").checked) view.scrollTop = view.scrollHeight;
    } else {
      S.logTotal = data.total;
    }
  } catch (e) { /* 后端可能已退出，忽略 */ }
}

/* ================= 编辑器 ================= */

function mode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function wrapLabel(text, input) {
  const label = el("label", null, text);
  label.appendChild(input);
  return label;
}

function addRuleRow(rule = {}) {
  const row = el("div", "rule-row");
  const bind = el("input"); bind.placeholder = t("rules.bind_ph"); bind.value = rule.bind || "";
  const rport = el("input"); rport.type = "number"; rport.min = 1; rport.max = 65535;
  rport.placeholder = t("rules.port"); rport.value = rule.remote_port || "";
  const target = el("input"); target.placeholder = t("rules.target_ph");
  target.value = rule.local_target || "127.0.0.1:7890";
  const del = el("button", "btn tiny danger", "✕");
  del.type = "button";
  del.addEventListener("click", () => row.remove());
  row.append(
    wrapLabel(t("rules.bind"), bind),
    wrapLabel(t("rules.port"), rport),
    wrapLabel(t("rules.target"), target),
    del,
  );
  $("#rules").appendChild(row);
}

function collectRules() {
  const rules = [];
  for (const row of document.querySelectorAll("#rules .rule-row")) {
    const inputs = row.querySelectorAll("input");
    rules.push({
      bind: inputs[0].value.trim(),
      remote_port: inputs[1].value.trim(),
      local_target: inputs[2].value.trim(),
    });
  }
  return rules;
}

function collectForm() {
  return {
    name: $("#f-name").value.trim(),
    note: $("#f-note").value.trim(),
    mode: mode(),
    alias: $("#f-alias").value,
    host: $("#f-host").value.trim(),
    port: parseInt($("#f-port").value || "22", 10),
    user: $("#f-user").value.trim(),
    identity: $("#f-identity").value.trim(),
    hostkey_policy: $("#f-hostkey").value,
    extra_args: $("#f-extra").value.trim(),
    auto_reconnect: $("#f-auto-reconnect").checked,
    enabled: $("#f-enabled").checked,
    rules: collectRules(),
  };
}

function validateForm(x) {
  if (!x.name) return t("toast.name_required");
  if (x.mode === "alias" && !x.alias) return t("toast.alias_required");
  if (x.mode === "custom" && !x.host) return t("toast.host_required");
  if (!x.rules.length) return t("toast.need_rule");
  for (const r of x.rules) {
    const p = parseInt(r.remote_port, 10);
    if (!(p >= 1 && p <= 65535)) return t("toast.bad_rport", r.remote_port || "(empty)");
    if (!/^\S+:\d{1,5}$/.test(r.local_target)) return t("toast.bad_target", r.local_target);
  }
  return "";
}

async function loadAliases(current) {
  try {
    const data = await api("/api/ssh_hosts");
    const sel = $("#f-alias");
    sel.textContent = "";
    const hosts = data.hosts || [];
    if (current && !hosts.includes(current)) hosts.unshift(current);
    if (!hosts.length) {
      const opt = el("option", null, "（~/.ssh/config 中没有别名）");
      sel.appendChild(opt);
    }
    for (const h of hosts) {
      const opt = el("option", null, h);
      opt.value = h;
      sel.appendChild(opt);
    }
    if (current) sel.value = current;
  } catch (e) { /* ignore */ }
}

function setModeUI() {
  const m = mode();
  $("#pane-custom").classList.toggle("hidden", m !== "custom");
  $("#pane-alias").classList.toggle("hidden", m !== "alias");
}

function openEditor(x) {
  S.editingId = x ? x.id : null;
  $("#editor-title").textContent = x ? t("editor.title_edit") : t("editor.title_new");
  $("#f-name").value = x ? x.name : "";
  $("#f-note").value = x ? x.note || "" : "";
  $("#f-host").value = x ? x.host || "" : "";
  $("#f-port").value = x ? x.port || 22 : 22;
  $("#f-user").value = x ? x.user || "" : "";
  $("#f-identity").value = x ? x.identity || "" : "";
  $("#f-hostkey").value = x ? x.hostkey_policy || "accept-new" : "accept-new";
  $("#f-extra").value = x ? x.extra_args || "" : "";
  $("#f-auto-reconnect").checked = x ? !!x.auto_reconnect : true;
  $("#f-enabled").checked = x ? !!x.enabled : true;
  $("#f-sshcmd").value = "";
  $("#test-output").classList.add("hidden");
  $("#test-output").textContent = "";

  document.querySelector(`input[name="mode"][value="${x && x.mode === "alias" ? "alias" : "custom"}"]`).checked = true;
  setModeUI();
  loadAliases(x && x.mode === "alias" ? x.alias : "");

  $("#rules").textContent = "";
  const rules = x && x.rules && x.rules.length ? x.rules : [{}];
  for (const r of rules) addRuleRow(r);

  $("#editor").classList.remove("hidden");
}

function closeEditor() {
  $("#editor").classList.add("hidden");
}

async function saveEditor() {
  const x = collectForm();
  const err = validateForm(x);
  if (err) return toast(err, "error");
  try {
    if (S.editingId) {
      await api(`/api/tunnels/${S.editingId}`, { method: "PUT", body: JSON.stringify(x) });
      toast(t("toast.saved_restart"), "success");
    } else {
      await api("/api/tunnels", { method: "POST", body: JSON.stringify(x) });
      toast(t("toast.created"), "success");
    }
    closeEditor();
    await loadState();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function testConnection() {
  const x = collectForm();
  const err = validateForm(x);
  if (err) return toast(err, "error");
  const out = $("#test-output");
  out.classList.remove("hidden");
  out.textContent = t("editor.testing");
  try {
    const r = await api("/api/test", { method: "POST", body: JSON.stringify(x) });
    const lines = [];
    if (r.ok) {
      lines.push(t("editor.test_ok"));
      for (const [port, status] of Object.entries(r.ports || {})) {
        lines.push(status === "busy" ? t("editor.port_busy", port) : t("editor.port_free", port));
      }
    } else {
      lines.push(t("editor.test_fail", r.error || "unknown"));
    }
    if (r.output) lines.push("\n" + t("editor.raw") + "\n" + r.output.slice(0, 1500));
    out.textContent = lines.join("\n");
  } catch (e) {
    out.textContent = t("editor.test_fail", e.message);
  }
}

function parseSshCommand() {
  const text = $("#f-sshcmd").value.trim();
  if (!text) return toast(t("toast.parse_first"), "error");
  const res = { host: "", user: "", port: "", identity: "" };
  const tokens = text.split(/\s+/);
  let i = tokens[0] === "ssh" ? 1 : 0;
  const skipValue = new Set(["-o", "-J", "-F", "-E", "-b", "-c", "-D", "-L", "-m", "-O", "-Q", "-S", "-W", "-w"]);
  while (i < tokens.length) {
    const tok = tokens[i];
    if (tok === "-p") res.port = tokens[++i] || "";
    else if (tok === "-i") res.identity = tokens[++i] || "";
    else if (tok === "-l") res.user = tokens[++i] || "";
    else if (skipValue.has(tok)) i++;
    else if (!tok.startsWith("-")) {
      const m = tok.match(/^([^@]+)@(.+)$/);
      if (m) { res.user = res.user || m[1]; res.host = m[2]; }
      else if (!res.host) res.host = tok;
    }
    i++;
  }
  if (!res.host) return toast(t("toast.parse_fail"), "error");
  document.querySelector('input[name="mode"][value="custom"]').checked = true;
  setModeUI();
  $("#f-host").value = res.host;
  if (res.user) $("#f-user").value = res.user;
  if (res.port) $("#f-port").value = res.port;
  if (res.identity) $("#f-identity").value = res.identity;
  toast(t("toast.parsed", (res.user ? res.user + "@" : "") + res.host + (res.port ? ":" + res.port : "")), "success");
}

/* ================= 设置 ================= */

function openSettings() {
  const s = S.settings;
  $("#s-retry").value = s.retry_seconds ?? 5;
  $("#s-port").value = s.ui_port ?? 8787;
  $("#s-extra").value = s.extra_ssh_args ?? "";
  $("#s-theme").value = s.theme || "auto";
  $("#s-language").value = s.language || "auto";
  $("#s-auto-start").checked = !!s.auto_start;
  $("#s-notify").checked = s.notify !== false;
  $("#s-proxy-check").checked = s.proxy_check !== false;
  $("#s-update-check").checked = s.update_check !== false;
  $("#about").textContent = t("settings.about", "v" + S.version);
  api("/api/autostart").then((r) => { $("#s-autostart").checked = !!r.enabled; }).catch(() => {});
  $("#settings").classList.remove("hidden");
}

async function saveSettings() {
  try {
    await api("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        retry_seconds: parseInt($("#s-retry").value || "5", 10),
        ui_port: parseInt($("#s-port").value || "8787", 10),
        extra_ssh_args: $("#s-extra").value.trim(),
        theme: $("#s-theme").value,
        language: $("#s-language").value,
        auto_start: $("#s-auto-start").checked,
        notify: $("#s-notify").checked,
        proxy_check: $("#s-proxy-check").checked,
        update_check: $("#s-update-check").checked,
      }),
    });
    await api("/api/autostart", {
      method: "POST",
      body: JSON.stringify({ enabled: $("#s-autostart").checked }),
    });
    toast(t("toast.settings_saved"), "success");
    $("#settings").classList.add("hidden");
    await loadState();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function checkUpdateNow() {
  const about = $("#about");
  about.textContent = t("settings.checking");
  try {
    const info = await api("/api/update_check", { method: "POST", body: JSON.stringify({ force: true }) });
    S.update = info;
    renderUpdateBanner();
    if (info.has_update) about.textContent = t("settings.update_available", "v" + info.latest);
    else if (info.error) about.textContent = t("settings.check_failed", info.error);
    else about.textContent = t("settings.up_to_date");
  } catch (e) {
    about.textContent = t("settings.check_failed", e.message);
  }
}

/* ================= 全局操作 ================= */

async function startAll() {
  try { await api("/api/start_all", { method: "POST" }); toast(t("toast.started_all"), "success"); }
  catch (e) { toast(e.message, "error"); }
  await loadState();
}

async function stopAll() {
  try { await api("/api/stop_all", { method: "POST" }); toast(t("toast.stopped_all"), "success"); }
  catch (e) { toast(e.message, "error"); }
  await loadState();
}

async function quitTool() {
  if (!confirm(t("confirm.quit"))) return;
  try { await api("/api/quit", { method: "POST" }); } catch (e) { /* 服务已关 */ }
  document.body.innerHTML =
    '<div style="display:grid;place-items:center;height:100%;color:#8a94a3;font-size:15px">' +
    escapeHtml(t("app.title")) + "</div>";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ================= 事件绑定 ================= */

function bind() {
  $("#btn-start-all").addEventListener("click", startAll);
  $("#btn-stop-all").addEventListener("click", stopAll);
  $("#btn-new").addEventListener("click", () => openEditor(null));
  $("#btn-settings").addEventListener("click", openSettings);

  document.querySelectorAll('input[name="mode"]').forEach((r) => r.addEventListener("change", setModeUI));
  $("#btn-add-rule").addEventListener("click", () => addRuleRow({}));
  $("#btn-parse").addEventListener("click", parseSshCommand);
  $("#btn-refresh-aliases").addEventListener("click", () => loadAliases($("#f-alias").value));
  $("#btn-test").addEventListener("click", testConnection);
  $("#btn-save").addEventListener("click", saveEditor);
  $("#btn-cancel").addEventListener("click", closeEditor);

  $("#btn-settings-save").addEventListener("click", saveSettings);
  $("#btn-settings-close").addEventListener("click", () => $("#settings").classList.add("hidden"));
  $("#btn-export").addEventListener("click", () => { window.location.href = "/api/export"; });
  $("#btn-check-update").addEventListener("click", checkUpdateNow);
  $("#btn-quit").addEventListener("click", quitTool);
  $("#btn-import").addEventListener("click", () => $("#import-file").click());
  $("#import-file").addEventListener("change", async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const text = await file.text();
    if (!confirm(t("confirm.import"))) return;
    try {
      await api("/api/import", { method: "POST", body: JSON.stringify({ config: text }) });
      toast(t("toast.imported"), "success");
      $("#settings").classList.add("hidden");
      await loadState();
    } catch (e) {
      toast(e.message, "error");
    }
    ev.target.value = "";
  });

  $("#btn-clear-log").addEventListener("click", () => {
    S.logLines = [];
    $("#logview").textContent = "";
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      closeEditor();
      $("#settings").classList.add("hidden");
    }
  });
}

/* ================= 启动 ================= */

bind();
loadState().then(() => {
  if (S.tunnels.length) selectTunnel(S.tunnels[0].id);
});
setInterval(loadState, 2000);
setInterval(fetchLogs, 1000);
