"use strict";

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
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* ignore */ }
  if (!res.ok) throw new Error((data && data.error) || ("HTTP " + res.status));
  return data;
}

function fmtUptime(sec) {
  if (!sec) return "—";
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  if (h) return `${h} 小时 ${m} 分`;
  if (m) return `${m} 分 ${s} 秒`;
  return `${s} 秒`;
}

const STATE_LABEL = { stopped: "已停止", starting: "连接中", running: "运行中", retry: "重连中", error: "错误" };

/* ================= 全局状态 ================= */

const S = {
  tunnels: [],
  settings: {},
  version: "",
  selectedId: null,
  logTotal: 0,
  logLines: [],
  editingId: null,
  stateTimer: null,
  logTimer: null,
};

/* ================= 状态轮询与渲染 ================= */

async function loadState() {
  try {
    const data = await api("/api/state");
    S.tunnels = data.tunnels || [];
    S.settings = data.settings || {};
    S.version = data.version || "";
    $("#offline").classList.add("hidden");
    renderList();
    renderSummary();
    if (S.selectedId && !S.tunnels.some((t) => t.id === S.selectedId)) {
      selectTunnel(null);
    }
  } catch (e) {
    $("#offline").classList.remove("hidden");
  }
}

function renderSummary() {
  const counts = { running: 0, retry: 0, error: 0, other: 0 };
  for (const t of S.tunnels) {
    if (t.state === "running") counts.running++;
    else if (t.state === "retry" || t.state === "starting") counts.retry++;
    else if (t.state === "error") counts.error++;
    else counts.other++;
  }
  $("#summary").textContent =
    `共 ${S.tunnels.length} 条隧道 · 运行中 ${counts.running} · 重连中 ${counts.retry} · 错误 ${counts.error} · 已停止 ${counts.other}`;
}

function serverText(t) {
  return t.mode === "alias"
    ? `别名 ${t.alias || "?"}`
    : `${t.user ? t.user + "@" : ""}${t.host || "?"}:${t.port || 22}`;
}

function renderList() {
  const box = $("#tunnels");
  box.textContent = "";
  if (!S.tunnels.length) {
    box.appendChild(el("div", "empty", "还没有隧道。点击右上角「＋ 新建隧道」开始配置。"));
    return;
  }
  for (const t of S.tunnels) {
    box.appendChild(renderCard(t));
  }
}

function renderCard(t) {
  const card = el("div", "card" + (t.id === S.selectedId ? " selected" : ""));
  card.addEventListener("click", () => selectTunnel(t.id));

  // 第一行：名称 + 状态 + 服务器
  const top = el("div", "card-top");
  top.appendChild(el("div", "card-name", t.name));
  const badge = el("span", "badge " + t.state);
  badge.appendChild(el("span", "dot"));
  badge.appendChild(document.createTextNode(STATE_LABEL[t.state] || t.state));
  top.appendChild(badge);
  top.appendChild(el("div", "card-server", serverText(t)));
  card.appendChild(top);

  // 规则
  const rules = el("div", "card-rules");
  for (const r of t.rules || []) {
    const bind = r.bind ? r.bind + ":" : "";
    rules.appendChild(el("span", "chip", `${bind}${r.remote_port} → ${r.local_target}`));
  }
  card.appendChild(rules);

  // 元信息
  const meta = el("div", "card-meta");
  if (t.state === "running") meta.appendChild(el("span", null, "已运行 " + fmtUptime(t.uptime)));
  if (t.pid) meta.appendChild(el("span", null, "ssh PID " + t.pid));
  if (t.retries) meta.appendChild(el("span", null, "重试 " + t.retries + " 次"));
  if (!t.auto_reconnect) meta.appendChild(el("span", null, "未启用自动重连"));
  card.appendChild(meta);

  // 详情（错误 / 警告）
  if (t.detail) {
    const d = el("div", "card-detail" + (t.state === "error" || t.state === "retry" ? " error" : ""), t.detail);
    card.appendChild(d);
  }
  if (t.note) card.appendChild(el("div", "card-note", "备注：" + t.note));

  // 操作按钮
  const actions = el("div", "card-actions");
  const mkBtn = (label, cls, fn) => {
    const b = el("button", "btn tiny " + (cls || ""), label);
    b.addEventListener("click", (ev) => { ev.stopPropagation(); fn(); });
    return b;
  };
  const active = t.state === "running" || t.state === "starting" || t.state === "retry";
  if (active) {
    actions.appendChild(mkBtn("■ 停止", "", () => act(t.id, "stop")));
  } else {
    actions.appendChild(mkBtn("▶ 启动", "primary", () => act(t.id, "start")));
  }
  if (active) actions.appendChild(mkBtn("⟳ 重启", "", () => act(t.id, "restart")));
  actions.appendChild(mkBtn("✎ 编辑", "", () => openEditor(t)));
  actions.appendChild(mkBtn("⧉ 复制", "", () => act(t.id, "duplicate")));
  actions.appendChild(mkBtn("🗑 删除", "danger", () => removeTunnel(t)));
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

async function removeTunnel(t) {
  if (!confirm(`确定删除隧道「${t.name}」吗？（会先停止它）`)) return;
  try {
    await api(`/api/tunnels/${t.id}`, { method: "DELETE" });
    toast("已删除「" + t.name + "」", "success");
    if (S.selectedId === t.id) selectTunnel(null);
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
  const t = S.tunnels.find((x) => x.id === id);
  $("#log-title").textContent = t ? "日志 · " + t.name : "日志";
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

function addRuleRow(rule = {}) {
  const row = el("div", "rule-row");
  const bind = el("input"); bind.placeholder = "远端绑定地址(可空)"; bind.value = rule.bind || "";
  const rport = el("input"); rport.type = "number"; rport.min = 1; rport.max = 65535;
  rport.placeholder = "远端端口"; rport.value = rule.remote_port || "";
  const target = el("input"); target.placeholder = "本机目标，如 127.0.0.1:7890";
  target.value = rule.local_target || "127.0.0.1:7890";
  const del = el("button", "btn tiny danger", "✕");
  del.type = "button";
  del.addEventListener("click", () => row.remove());
  row.append(
    wrapLabel("远端绑定地址（一般留空）", bind),
    wrapLabel("远端端口", rport),
    wrapLabel("本机目标 host:port", target),
    del,
  );
  $("#rules").appendChild(row);
}

function wrapLabel(text, input) {
  const label = el("label", null, text);
  label.appendChild(input);
  return label;
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

function validateForm(t) {
  if (!t.name) return "请填写名称";
  if (t.mode === "alias" && !t.alias) return "请选择 SSH 别名（可先点“刷新”或检查 ~/.ssh/config）";
  if (t.mode === "custom" && !t.host) return "请填写服务器地址";
  if (!t.rules.length) return "至少需要一条转发规则";
  for (const r of t.rules) {
    const p = parseInt(r.remote_port, 10);
    if (!(p >= 1 && p <= 65535)) return `远端端口不合法：${r.remote_port || "(空)"}`;
    if (!/^\S+:\d{1,5}$/.test(r.local_target)) return `本机目标格式应为 host:port：${r.local_target}`;
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
      sel.appendChild(el("option", null, "（~/.ssh/config 中没有别名）"));
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

function openEditor(t) {
  S.editingId = t ? t.id : null;
  $("#editor-title").textContent = t ? "编辑隧道" : "新建隧道";
  $("#f-name").value = t ? t.name : "";
  $("#f-note").value = t ? t.note || "" : "";
  $("#f-host").value = t ? t.host || "" : "";
  $("#f-port").value = t ? t.port || 22 : 22;
  $("#f-user").value = t ? t.user || "" : "";
  $("#f-identity").value = t ? t.identity || "" : "";
  $("#f-hostkey").value = t ? t.hostkey_policy || "accept-new" : "accept-new";
  $("#f-extra").value = t ? t.extra_args || "" : "";
  $("#f-auto-reconnect").checked = t ? !!t.auto_reconnect : true;
  $("#f-enabled").checked = t ? !!t.enabled : true;
  $("#f-sshcmd").value = "";
  $("#test-output").classList.add("hidden");
  $("#test-output").textContent = "";

  document.querySelector(`input[name="mode"][value="${t && t.mode === "alias" ? "alias" : "custom"}"]`).checked = true;
  setModeUI();
  loadAliases(t && t.mode === "alias" ? t.alias : "");

  $("#rules").textContent = "";
  const rules = t && t.rules && t.rules.length ? t.rules : [{}];
  for (const r of rules) addRuleRow(r);

  $("#editor").classList.remove("hidden");
}

function closeEditor() {
  $("#editor").classList.add("hidden");
}

async function saveEditor() {
  const t = collectForm();
  const err = validateForm(t);
  if (err) return toast(err, "error");
  try {
    if (S.editingId) {
      await api(`/api/tunnels/${S.editingId}`, { method: "PUT", body: JSON.stringify(t) });
      toast("已保存（运行中的隧道需要重启后生效）", "success");
    } else {
      await api("/api/tunnels", { method: "POST", body: JSON.stringify(t) });
      toast("已创建隧道", "success");
    }
    closeEditor();
    await loadState();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function testConnection() {
  const t = collectForm();
  const err = validateForm(t);
  if (err) return toast(err, "error");
  const out = $("#test-output");
  out.classList.remove("hidden");
  out.textContent = "测试中…（最长约 45 秒）";
  try {
    const r = await api("/api/test", { method: "POST", body: JSON.stringify(t) });
    const lines = [];
    if (r.ok) {
      lines.push("✅ SSH 连接成功，认证正常");
      for (const [port, status] of Object.entries(r.ports || {})) {
        lines.push(status === "busy" ? `⚠ 远端端口 ${port}：已被占用` : `✔ 远端端口 ${port}：空闲`);
      }
    } else {
      lines.push("❌ 连接失败：" + (r.error || "未知原因"));
    }
    if (r.output) lines.push("\n--- 原始输出 ---\n" + r.output.slice(0, 1500));
    out.textContent = lines.join("\n");
  } catch (e) {
    out.textContent = "测试失败：" + e.message;
  }
}

function parseSshCommand() {
  const text = $("#f-sshcmd").value.trim();
  if (!text) return toast("请先粘贴 ssh 命令", "error");
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
  if (!res.host) return toast("没能从命令里解析出主机地址", "error");
  document.querySelector('input[name="mode"][value="custom"]').checked = true;
  setModeUI();
  $("#f-host").value = res.host;
  if (res.user) $("#f-user").value = res.user;
  if (res.port) $("#f-port").value = res.port;
  if (res.identity) $("#f-identity").value = res.identity;
  toast("已解析：" + (res.user ? res.user + "@" : "") + res.host + (res.port ? ":" + res.port : ""), "success");
}

/* ================= 设置 ================= */

function openSettings() {
  const s = S.settings;
  $("#s-retry").value = s.retry_seconds ?? 5;
  $("#s-port").value = s.ui_port ?? 8787;
  $("#s-extra").value = s.extra_ssh_args ?? "";
  $("#s-auto-start").checked = !!s.auto_start;
  $("#about").textContent = `版本 ${S.version} · 配置：~/.config/reverse-tunnel-manager/config.json`;
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
        auto_start: $("#s-auto-start").checked,
      }),
    });
    await api("/api/autostart", {
      method: "POST",
      body: JSON.stringify({ enabled: $("#s-autostart").checked }),
    });
    toast("设置已保存", "success");
    $("#settings").classList.add("hidden");
    await loadState();
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ================= 全局操作 ================= */

async function startAll() {
  try { await api("/api/start_all", { method: "POST" }); toast("已启动全部隧道", "success"); }
  catch (e) { toast(e.message, "error"); }
  await loadState();
}

async function stopAll() {
  try { await api("/api/stop_all", { method: "POST" }); toast("已停止全部隧道", "success"); }
  catch (e) { toast(e.message, "error"); }
  await loadState();
}

async function quitTool() {
  if (!confirm("停止全部隧道并退出工具？（退出后隧道将全部断开）")) return;
  try { await api("/api/quit", { method: "POST" }); } catch (e) { /* 服务已关 */ }
  document.body.innerHTML =
    '<div style="display:grid;place-items:center;height:100%;color:#8a94a3;font-size:15px">' +
    "工具已退出。需要重新使用时再次运行 app.py 即可。</div>";
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
  $("#btn-quit").addEventListener("click", quitTool);
  $("#btn-import").addEventListener("click", () => $("#import-file").click());
  $("#import-file").addEventListener("change", async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const text = await file.text();
    if (!confirm("导入会覆盖当前所有隧道配置（先停止全部隧道），继续？")) return;
    try {
      await api("/api/import", { method: "POST", body: JSON.stringify({ config: text }) });
      toast("配置已导入", "success");
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

  // Esc 关闭弹窗
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
