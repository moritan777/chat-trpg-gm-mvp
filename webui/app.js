"use strict";

const byId = (id) => document.getElementById(id);
const scenarioSelect = byId("scenario");
const history = byId("history");
const errorBox = byId("error");
const connection = byId("connection");
const locationHeading = byId("location");
const commandInput = byId("command");
const settingsMessage = byId("settings-message");
let sessionId = null;
let publicSettings = null;

function addLine(speaker, text) {
  const line = document.createElement("p");
  const label = document.createElement("strong");
  label.textContent = `${speaker}: `;
  const content = document.createElement("span");
  content.textContent = text;
  line.append(label, content); history.append(line);
}
function setLocation(location) { locationHeading.textContent = `現在地: ${location.name}`; }
function setSettingsDisabled(disabled) {
  document.querySelectorAll("#settings-panel input, #settings-panel select, #settings-panel button:not(#new-game)").forEach((element) => { element.disabled = disabled; });
  byId("new-game").disabled = false;
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
    chat: { provider: byId("chat-provider").value, base_url: byId("chat-url").value, model: byId("chat-model").value, api_key: byId("chat-key").value },
    embedding: { base_url: byId("embedding-url").value, model: byId("embedding-model").value, api_key: byId("embedding-key").value },
  };
}
function showSettings(data) {
  publicSettings = data;
  byId("settings-path").textContent = data.settings_path;
  scenarioSelect.replaceChildren(...data.scenarios.map((scenario) => {
    const option = document.createElement("option"); option.value = scenario.id;
    option.textContent = `${scenario.title} (${scenario.id}${scenario.scenario_revision ? ` / ${scenario.scenario_revision}` : ""})`;
    return option;
  }));
  scenarioSelect.value = data.selected_scenario;
  byId("scenario-source").textContent = `現在適用: ${data.selected_scenario} / 設定元: ${data.effective.sources.selected_scenario}`;
  byId("chat-provider").value = data.saved.chat.provider;
  byId("chat-provider-source").textContent = `現在適用: ${data.effective.chat.provider} / 設定元: ${data.effective.sources["chat.provider"]}`;
  byId("chat-url").value = data.saved.chat.base_url; byId("chat-model").value = data.saved.chat.model;
  byId("embedding-url").value = data.saved.embedding.base_url; byId("embedding-model").value = data.saved.embedding.model;
  byId("chat-url-source").textContent = `現在適用: ${data.effective.chat.base_url} / 設定元: ${data.effective.sources["chat.base_url"]}`;
  byId("chat-model-source").textContent = `現在適用: ${data.effective.chat.model} / 設定元: ${data.effective.sources["chat.model"]}`;
  byId("embedding-url-source").textContent = `現在適用: ${data.effective.embedding.base_url} / 設定元: ${data.effective.sources["embedding.base_url"]}`;
  byId("embedding-model-source").textContent = `現在適用: ${data.effective.embedding.model} / 設定元: ${data.effective.sources["embedding.model"]}`;
  byId("chat-key-status").textContent = data.api_keys.chat.configured ? "APIキー: このPythonセッションで設定済み" : "APIキー: 未設定";
  byId("embedding-key-status").textContent = data.api_keys.embedding.configured ? "APIキー: このPythonセッションで設定済み" : "APIキー: 未設定";
  settingsMessage.textContent = data.warning || "接続テストを推奨します。保存済み設定または初期設定で開始できます。";
}
async function loadSettings() {
  try {
    const health = await api("/api/health"); connection.textContent = `接続済み: ${health.version}`;
    showSettings(await api("/api/settings"));
  } catch (error) { errorBox.textContent = error.message; connection.textContent = "APIへ接続できません"; }
}
async function saveSettings() {
  try {
    const data = await api("/api/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(formSettings()) });
    byId("chat-key").value = ""; byId("embedding-key").value = ""; showSettings(data); settingsMessage.textContent = "設定を保存しました。新しいゲームから反映されます。";
  } catch (error) { settingsMessage.textContent = error.message; }
}
async function testConnection(service) {
  const button = byId(`${service}-test`); const result = byId(`${service}-result`); button.disabled = true; result.textContent = "接続テスト中…";
  try {
    const data = await api(`/api/connections/${service}/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ settings: formSettings() }) });
    result.textContent = data.ok ? `接続成功 (${data.latency_ms} ms${data.dimensions ? ` / ${data.dimensions}次元` : ""})` : data.status;
  } catch (error) { result.textContent = error.message; } finally { button.disabled = false; }
}
async function startGame() {
  errorBox.textContent = "";
  try {
    if (sessionId) await api(`/api/sessions/${sessionId}`, { method: "DELETE" });
    const data = await api("/api/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenario_id: scenarioSelect.value }) });
    sessionId = data.session_id; history.replaceChildren(); data.opening.forEach((line) => addLine("導入", line)); setLocation(data.current_location); setSettingsDisabled(true);
  } catch (error) { errorBox.textContent = error.message; }
}
async function prepareNewGame() {
  if (sessionId) { try { await api(`/api/sessions/${sessionId}`, { method: "DELETE" }); } catch (_) { /* already gone */ } }
  sessionId = null; history.replaceChildren(); locationHeading.textContent = "未開始"; setSettingsDisabled(false); settingsMessage.textContent = "設定を確認してゲームを開始してください。";
}
byId("save-settings").addEventListener("click", saveSettings);
byId("reset-settings").addEventListener("click", async () => { try { showSettings(await api("/api/settings/reset", { method: "POST" })); settingsMessage.textContent = "初期設定へ戻しました。"; } catch (error) { settingsMessage.textContent = error.message; } });
byId("clear-keys").addEventListener("click", async () => { try { showSettings(await api("/api/settings/secrets/clear", { method: "POST" })); byId("chat-key").value = ""; byId("embedding-key").value = ""; settingsMessage.textContent = "APIキーをメモリから削除しました。"; } catch (error) { settingsMessage.textContent = error.message; } });
byId("chat-test").addEventListener("click", () => testConnection("chat")); byId("embedding-test").addEventListener("click", () => testConnection("embedding"));
byId("start").addEventListener("click", startGame); byId("new-game").addEventListener("click", prepareNewGame);
byId("command-form").addEventListener("submit", async (event) => {
  event.preventDefault(); if (!sessionId) { errorBox.textContent = "先にゲームを開始してください。"; return; }
  const text = commandInput.value.trim(); if (!text) return; addLine("あなた", text); commandInput.value = ""; errorBox.textContent = "";
  try { const data = await api(`/api/sessions/${sessionId}/commands`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }); data.lines.forEach((line) => addLine("GM", line)); setLocation(data.current_location); }
  catch (error) { errorBox.textContent = error.message; }
});
loadSettings();
