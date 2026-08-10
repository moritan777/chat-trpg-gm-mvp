"use strict";

const byId = (id) => document.getElementById(id);
const scenarioSelect = byId("scenario");
const settingsDetails = byId("settings-details");
const history = byId("history");
const errorBox = byId("error");
const connection = byId("connection");
const locationHeading = byId("location");
const commandInput = byId("command");
const settingsMessage = byId("settings-message");
const newMessageButton = byId("new-message");
const commandSubmit = byId("command-submit");
const HISTORY_BOTTOM_THRESHOLD = 120;
const connectionStates = { chat: "unknown", embedding: "unknown" };
let sessionId = null;
let publicSettings = null;
let hasSavedSettings = false;

function distanceFromHistoryBottom() { return history.scrollHeight - history.scrollTop - history.clientHeight; }
function isHistoryNearBottom() { return distanceFromHistoryBottom() <= HISTORY_BOTTOM_THRESHOLD; }
function scrollHistoryToBottom() {
  requestAnimationFrame(() => { history.scrollTop = history.scrollHeight; newMessageButton.hidden = true; });
}
function appendLines(lines, follow) {
  lines.forEach(({ speaker, text }) => addLine(speaker, text));
  if (follow) scrollHistoryToBottom(); else newMessageButton.hidden = false;
}
function addLine(speaker, text) {
  const line = document.createElement("p");
  const label = document.createElement("strong");
  label.textContent = `${speaker}: `;
  const content = document.createElement("span");
  content.textContent = text;
  line.append(label, content); history.append(line);
}
function updateChatProviderUi(providerChanged = false) {
  const provider = byId("chat-provider").value;
  const disabled = provider === "none";
  const external = provider === "openai_compatible";
  byId("chat-provider-help").textContent = disabled ? "Chat LLMを使わず既存のフォールバックで遊びます。接続テストは不要です。" : external ? "契約しているサービスのOpenAI互換Base URLとModelを入力し、接続テストしてください。" : "ローカルのllama.cppサーバーが必要です。";
  byId("external-chat-notice").hidden = !external;
  for (const id of ["chat-url", "chat-model", "chat-key-use", "chat-key"]) byId(id).disabled = disabled || Boolean(sessionId) || (id === "chat-key" && !byId("chat-key-use").checked);
  byId("chat-test").disabled = disabled || Boolean(sessionId);
  if (providerChanged && external && !byId("chat-key-use").checked) byId("chat-key-use").checked = true;
  if (disabled) setConnectionState("chat", "disabled");
  toggleKeyField("chat");
}
function setLocation(location) { locationHeading.textContent = `現在地: ${location.name}`; }
function setSettingsDisabled(disabled) {
  document.querySelectorAll("#settings-panel input, #settings-panel select, #settings-panel button").forEach((element) => { element.disabled = disabled; });
  settingsDetails.classList.toggle("is-locked", disabled);
}
async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `APIエラー (HTTP ${response.status})`;
    try { message = (await response.json()).detail || message; } catch (_) { /* safe fallback */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function formSettings() {
  return {
    selected_scenario: scenarioSelect.value,
    chat: { provider: byId("chat-provider").value, base_url: byId("chat-url").value, model: byId("chat-model").value, api_key: byId("chat-key-use").checked ? byId("chat-key").value : "" },
    embedding: { base_url: byId("embedding-url").value, model: byId("embedding-model").value, api_key: byId("embedding-key-use").checked ? byId("embedding-key").value : "" },
  };
}
function sourceLabel(source) {
  if (String(source).startsWith("environment:")) return "環境変数";
  if (source === "settings.json") return "設定ファイル";
  return "既定値";
}
function sourceDetail(source) {
  return String(source).startsWith("environment:") ? String(source).slice("environment:".length) : sourceLabel(source);
}
function shortEndpoint(value) {
  try { const parsed = new URL(value); return parsed.host || String(value).slice(0, 48); }
  catch (_) { const safe = String(value || "未設定"); return safe.length > 48 ? `${safe.slice(0, 45)}…` : safe; }
}
function keyStatusText(service) {
  const status = publicSettings && publicSettings.api_keys[service];
  if (!status || !status.configured) return "未設定";
  return status.source === "environment" ? "環境変数から設定済み" : "このセッションで設定済み";
}
function stateText(state) { return state === "success" ? "接続成功" : state === "failure" ? "接続失敗" : state === "disabled" ? "無効" : "未確認"; }
function setConnectionState(service, state) {
  connectionStates[service] = state;
  const target = byId(`summary-${service}-state`);
  target.className = `connection-state state-${state}`;
  target.textContent = `● ${stateText(state)}`;
}
function updateSummary() {
  if (!publicSettings) return;
  const selected = publicSettings.scenarios.find((scenario) => scenario.id === scenarioSelect.value);
  byId("summary-scenario").textContent = selected ? selected.title : scenarioSelect.value || "未選択";
  byId("summary-chat-endpoint").textContent = shortEndpoint(byId("chat-url").value);
  byId("summary-chat-model").textContent = `Model: ${byId("chat-model").value || "未設定"}`;
  byId("summary-embedding-endpoint").textContent = shortEndpoint(byId("embedding-url").value);
  byId("summary-embedding-model").textContent = `Model: ${byId("embedding-model").value || "未設定"}`;
  byId("summary-chat-key").textContent = `APIキー: ${keyStatusText("chat")}`;
  byId("summary-embedding-key").textContent = `APIキー: ${keyStatusText("embedding")}`;
  byId("summary-save-state").textContent = publicSettings.warning ? "読込時に警告あり" : hasSavedSettings ? "保存済み" : "未保存";
  setConnectionState("chat", connectionStates.chat); setConnectionState("embedding", connectionStates.embedding);
}
function showSource(id, value, source) {
  const target = byId(id);
  target.textContent = `適用中: ${sourceLabel(source)}（適用値: ${value} / 設定元: ${sourceDetail(source)}）`;
  target.title = `適用値: ${value}\n設定元: ${sourceDetail(source)}`;
}
function toggleKeyField(service) {
  const checked = byId(`${service}-key-use`).checked;
  byId(`${service}-key-row`).hidden = !checked;
  byId(`${service}-key`).disabled = !checked || Boolean(sessionId);
}
function showSettings(data) {
  publicSettings = data;
  const supportedProviders = Array.isArray(data.chat_providers) ? data.chat_providers.map((item) => item.value) : ["llama_cpp", "none"];
  const externalOption = byId("chat-provider").querySelector('option[value="openai_compatible"]');
  externalOption.disabled = !supportedProviders.includes("openai_compatible");
  hasSavedSettings = data.effective.sources.selected_scenario === "settings.json";
  byId("settings-path").textContent = data.settings_path;
  scenarioSelect.replaceChildren(...data.scenarios.map((scenario) => {
    const option = document.createElement("option"); option.value = scenario.id;
    option.textContent = `${scenario.title} (${scenario.id}${scenario.scenario_revision ? ` / ${scenario.scenario_revision}` : ""})`;
    return option;
  }));
  scenarioSelect.value = data.selected_scenario;
  showSource("scenario-source", data.selected_scenario, data.effective.sources.selected_scenario);
  byId("chat-provider").value = data.saved.chat.provider;
  showSource("chat-provider-source", data.effective.chat.provider, data.effective.sources["chat.provider"]);
  byId("chat-url").value = data.saved.chat.base_url; byId("chat-model").value = data.saved.chat.model;
  byId("embedding-url").value = data.saved.embedding.base_url; byId("embedding-model").value = data.saved.embedding.model;
  showSource("chat-url-source", data.effective.chat.base_url, data.effective.sources["chat.base_url"]);
  showSource("chat-model-source", data.effective.chat.model, data.effective.sources["chat.model"]);
  showSource("embedding-url-source", data.effective.embedding.base_url, data.effective.sources["embedding.base_url"]);
  showSource("embedding-model-source", data.effective.embedding.model, data.effective.sources["embedding.model"]);
  byId("chat-key").value = ""; byId("embedding-key").value = "";
  byId("chat-key-use").checked = data.api_keys.chat.configured;
  byId("embedding-key-use").checked = data.api_keys.embedding.configured;
  toggleKeyField("chat"); toggleKeyField("embedding");
  updateChatProviderUi();
  byId("chat-key-status").textContent = `APIキー: ${keyStatusText("chat")}`;
  byId("embedding-key-status").textContent = `APIキー: ${keyStatusText("embedding")}`;
  byId("first-run-guide").hidden = hasSavedSettings;
  settingsDetails.open = !hasSavedSettings || Boolean(data.warning);
  settingsMessage.textContent = !supportedProviders.includes("openai_compatible")
    ? "起動中のPython APIは外部OpenAI互換Providerに対応していません。更新後はWebサーバーを再起動してください。"
    : data.warning || "接続テストを推奨します。保存済み設定または初期設定で開始できます。";
  updateSummary();
}
async function loadSettings() {
  try {
    const health = await api("/api/health"); connection.textContent = `Python API: 接続済み (${health.version})`;
    showSettings(await api("/api/settings"));
  } catch (error) { errorBox.textContent = error.message; connection.textContent = "Python API: 接続失敗"; settingsDetails.open = true; }
}
async function saveSettings() {
  try {
    const data = await api("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(formSettings()) });
    showSettings(data); settingsDetails.open = false; settingsMessage.textContent = "設定を保存しました。新しいゲームから反映されます。";
  } catch (error) {
    settingsMessage.textContent = error.message.includes("Chat Providerはllama_cppまたはnone")
      ? "起動中のPython APIが古いため保存できません。Webサーバーを停止し、更新後のコードで再起動してください。"
      : error.message;
    settingsDetails.open = true;
  }
}
async function testConnection(service) {
  const button = byId(`${service}-test`); const result = byId(`${service}-result`);
  button.disabled = true; result.textContent = "接続テスト中…";
  try {
    const data = await api(`/api/connections/${service}/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ settings: formSettings() }) });
    setConnectionState(service, data.ok ? "success" : "failure");
    const responseModel = data.response_model ? ` / 応答モデル: ${data.response_model}` : "";
    result.textContent = data.ok ? `接続成功 (${data.latency_ms} ms${responseModel}${data.dimensions ? ` / ${data.dimensions}次元` : ""})` : data.status;
    if (!data.ok) { settingsDetails.open = true; byId(`${service}-settings`).scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  } catch (error) { setConnectionState(service, "failure"); result.textContent = error.message; settingsDetails.open = true; }
  finally { button.disabled = Boolean(sessionId); updateSummary(); }
}
function connectionFailure() { return connectionStates.chat === "failure" || connectionStates.embedding === "failure"; }
async function startGame() {
  errorBox.textContent = "";
  if (connectionFailure()) { errorBox.textContent = "接続テストに失敗しています。接続設定を確認してください。"; settingsDetails.open = true; return; }
  const chatRequired = byId("chat-provider").value !== "none";
  if (!hasSavedSettings && ((chatRequired && connectionStates.chat === "unknown") || connectionStates.embedding === "unknown")) {
    errorBox.textContent = "初回はChatとEmbeddingの接続テストを行い、設定を保存してください。"; settingsDetails.open = true; return;
  }
  if (hasSavedSettings && (connectionStates.chat === "unknown" || connectionStates.embedding === "unknown")) settingsMessage.textContent = "接続未確認の保存済み設定で開始します。";
  try {
    if (sessionId) await api(`/api/sessions/${sessionId}`, { method: "DELETE" });
    const data = await api("/api/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenario_id: scenarioSelect.value }) });
    sessionId = data.session_id; history.replaceChildren(); newMessageButton.hidden = true; appendLines(data.opening.map((text) => ({ speaker: "導入", text })), true); setLocation(data.current_location);
    setSettingsDisabled(true); settingsDetails.open = false; updateSummary();
    byId("game-panel").scrollIntoView({ behavior: "smooth", block: "start" }); commandInput.focus();
  } catch (error) { errorBox.textContent = error.message; settingsDetails.open = true; }
}
async function prepareNewGame() {
  if (sessionId && !window.confirm("進行中のゲームを終了して新しいゲームの準備をしますか？")) return;
  if (sessionId) { try { await api(`/api/sessions/${sessionId}`, { method: "DELETE" }); } catch (_) { /* already gone */ } }
  sessionId = null; history.replaceChildren(); newMessageButton.hidden = true; locationHeading.textContent = "未開始"; setSettingsDisabled(false); updateChatProviderUi(); settingsMessage.textContent = "設定を確認してゲームを開始してください。"; updateSummary();
}
function resetConnectionState(service) { setConnectionState(service, "unknown"); updateSummary(); }
for (const service of ["chat", "embedding"]) {
  for (const suffix of ["url", "model", "key"]) byId(`${service}-${suffix}`).addEventListener("input", () => resetConnectionState(service));
  byId(`${service}-key-use`).addEventListener("change", () => { toggleKeyField(service); resetConnectionState(service); });
}
scenarioSelect.addEventListener("change", updateSummary);
byId("chat-provider").addEventListener("change", () => {
  resetConnectionState("chat");
  if (byId("chat-provider").value === "openai_compatible") {
    byId("chat-url").value = "";
    byId("chat-model").value = "";
  }
  updateChatProviderUi(true); updateSummary();
});
history.addEventListener("scroll", () => { if (isHistoryNearBottom()) newMessageButton.hidden = true; });
newMessageButton.addEventListener("click", scrollHistoryToBottom);
byId("save-settings").addEventListener("click", saveSettings);
byId("reset-settings").addEventListener("click", async () => {
  if (!window.confirm("保存設定とメモリ上のAPIキーを初期設定へ戻しますか？")) return;
  try { showSettings(await api("/api/settings/reset", { method: "POST" })); resetConnectionState("chat"); resetConnectionState("embedding"); settingsDetails.open = true; settingsMessage.textContent = "初期設定へ戻しました。"; }
  catch (error) { settingsMessage.textContent = error.message; settingsDetails.open = true; }
});
byId("clear-keys").addEventListener("click", async () => {
  if (!window.confirm("メモリ上のChatとEmbedding APIキーを削除しますか？")) return;
  try { showSettings(await api("/api/settings/secrets/clear", { method: "POST" })); resetConnectionState("chat"); resetConnectionState("embedding"); settingsMessage.textContent = "APIキーをメモリから削除しました。"; }
  catch (error) { settingsMessage.textContent = error.message; settingsDetails.open = true; }
});
byId("chat-test").addEventListener("click", () => testConnection("chat")); byId("embedding-test").addEventListener("click", () => testConnection("embedding"));
byId("start").addEventListener("click", startGame); byId("new-game").addEventListener("click", prepareNewGame);
byId("command-form").addEventListener("submit", async (event) => {
  event.preventDefault(); if (!sessionId) { errorBox.textContent = "先にゲームを開始してください。"; return; }
  const text = commandInput.value.trim(); if (!text) return;
  appendLines([{ speaker: "あなた", text }], true); commandInput.value = ""; errorBox.textContent = "";
  commandInput.disabled = true; commandSubmit.disabled = true;
  try {
    const data = await api(`/api/sessions/${sessionId}/commands`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    const follow = isHistoryNearBottom();
    appendLines(data.lines.map((line) => ({ speaker: "GM", text: line })), follow); setLocation(data.current_location);
  } catch (error) { errorBox.textContent = error.message; }
  finally { commandInput.disabled = false; commandSubmit.disabled = false; commandInput.focus(); }
});
loadSettings();
