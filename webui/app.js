"use strict";

const scenarioSelect = document.querySelector("#scenario");
const history = document.querySelector("#history");
const errorBox = document.querySelector("#error");
const connection = document.querySelector("#connection");
const locationHeading = document.querySelector("#location");
const commandInput = document.querySelector("#command");
let sessionId = null;

function addLine(speaker, text) {
  const line = document.createElement("p");
  const label = document.createElement("strong");
  label.textContent = `${speaker}: `;
  const content = document.createElement("span");
  content.textContent = text;
  line.append(label, content);
  history.append(line);
}

function setLocation(location) {
  locationHeading.textContent = `現在地: ${location.name}`;
}

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `APIエラー (HTTP ${response.status})`;
    try { message = (await response.json()).detail || message; } catch (_) { /* use safe message */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

async function loadScenarios() {
  try {
    const health = await api("/api/health");
    connection.textContent = `接続済み: ${health.version}`;
    const data = await api("/api/scenarios");
    scenarioSelect.replaceChildren(...data.scenarios.map((scenario) => {
      const option = document.createElement("option");
      option.value = scenario.id;
      option.textContent = scenario.title;
      return option;
    }));
  } catch (error) { errorBox.textContent = error.message; connection.textContent = "APIへ接続できません"; }
}

async function startGame() {
  errorBox.textContent = "";
  try {
    if (sessionId) await api(`/api/sessions/${sessionId}`, { method: "DELETE" });
    const data = await api("/api/sessions", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioSelect.value }),
    });
    sessionId = data.session_id;
    history.replaceChildren();
    data.opening.forEach((line) => addLine("導入", line));
    setLocation(data.current_location);
  } catch (error) { errorBox.textContent = error.message; }
}

document.querySelector("#start").addEventListener("click", startGame);
document.querySelector("#new-game").addEventListener("click", startGame);
document.querySelector("#command-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!sessionId) { errorBox.textContent = "先にゲームを開始してください。"; return; }
  const text = commandInput.value.trim();
  if (!text) return;
  addLine("あなた", text); commandInput.value = ""; errorBox.textContent = "";
  try {
    const data = await api(`/api/sessions/${sessionId}/commands`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
    });
    data.lines.forEach((line) => addLine("GM", line));
    setLocation(data.current_location);
  } catch (error) { errorBox.textContent = error.message; }
});

loadScenarios();
