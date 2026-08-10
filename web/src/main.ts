import "./style.css";
import { ChatClientError, OpenAiCompatibleChatClient, chatCompletionsUrl } from "./api/openAiCompatibleChatClient";
import type { ChatConnectionConfig, ChatMessage } from "./api/types";
import { loadScenario, loadScenarioIndex, type Scenario } from "./scenarios";
import { appendTextMessage } from "./render";

const root = document.querySelector<HTMLDivElement>("#app")!;
let config: ChatConnectionConfig | undefined;
let scenario: Scenario | undefined;
let messages: ChatMessage[] = [];

const preview = `<aside class="notice">Web版は現在プレビュー段階です。Phase 1では接続確認とシナリオ表示のみ対応しています。正式なゲーム状態管理は今後のPhaseで追加予定です。</aside>`;
function safeError(error: unknown): string {
  if (error instanceof ChatClientError) {
    if (error.kind === "http") return `接続失敗 (HTTP ${error.status ?? "不明"})。モデル名またはAPIキーを確認してください。401/403は認証、404はURLまたはモデル設定が主な候補です。`;
    if (error.kind === "network") return "接続失敗。サーバー未起動、URL、CORS、HTTPSからHTTPへの制約、localhost/127.0.0.1の違いを確認してください。";
    if (error.kind === "response") return "接続先の応答形式がOpenAI互換ではありません。";
    return "Base URLとModelを確認してください。";
  }
  return error instanceof Error && error.message.startsWith("シナリオ") ? error.message : "処理に失敗しました。設定と接続状態を確認してください。";
}

async function showSettings(): Promise<void> {
  scenario = undefined; messages = [];
  root.innerHTML = `<main><h1>Chat TTRPG GM <small>Web Preview</small></h1>${preview}<section class="card"><h2>1. シナリオ</h2><label>シナリオ<select id="scenario"></select></label><div id="scenario-error" role="alert"></div></section><section class="card"><h2>2. API接続設定</h2><label>Base URL<input id="base-url" type="url" value="http://127.0.0.1:8080/v1" autocomplete="off"></label><label>Model<input id="model" value="local-model" autocomplete="off"></label><label>API Key<input id="api-key" type="password" autocomplete="off" spellcheck="false" placeholder="ローカルllama.cppでは空欄可"></label><p>送信先: <code id="endpoint"></code></p><div class="actions"><button id="test">接続テスト</button><button id="play" class="primary">プレイ画面へ進む</button><button id="clear">設定をクリア</button></div><p id="status" role="status"></p><p class="security">API Keyを含む設定はメモリだけに保持し、Web Storage・URL・ログへ保存しません。入力したBase URL以外への中継はありません。</p></section></main>`;
  const base = root.querySelector<HTMLInputElement>("#base-url")!;
  const model = root.querySelector<HTMLInputElement>("#model")!;
  const key = root.querySelector<HTMLInputElement>("#api-key")!;
  const select = root.querySelector<HTMLSelectElement>("#scenario")!;
  const endpoint = root.querySelector<HTMLElement>("#endpoint")!;
  const status = root.querySelector<HTMLElement>("#status")!;
  const updateEndpoint = () => { try { endpoint.textContent = chatCompletionsUrl(base.value); } catch { endpoint.textContent = "Base URLを入力してください"; } };
  base.addEventListener("input", updateEndpoint); updateEndpoint();
  try { (await loadScenarioIndex()).scenarios.forEach(x => select.add(new Option(x.title, x.path))); }
  catch (e) { root.querySelector<HTMLElement>("#scenario-error")!.textContent = safeError(e); }
  const readConfig = (): ChatConnectionConfig => ({ baseUrl: base.value, model: model.value, apiKey: key.value });
  root.querySelector("#test")!.addEventListener("click", async () => {
    status.textContent = "接続中…";
    try {
      const result = await new OpenAiCompatibleChatClient(readConfig()).complete([{ role: "user", content: "Reply OK." }], 3);
      status.textContent = `接続成功 — model: ${result.model} / 応答時間: ${result.elapsedMs} ms`;
    } catch (e) { status.textContent = safeError(e); }
  });
  root.querySelector("#clear")!.addEventListener("click", () => { base.value = ""; model.value = ""; key.value = ""; config = undefined; status.textContent = "設定をクリアしました。"; updateEndpoint(); });
  root.querySelector("#play")!.addEventListener("click", async () => {
    status.textContent = "シナリオを読み込み中…";
    try { config = readConfig(); scenario = await loadScenario(select.value); showPlay(); } catch (e) { status.textContent = safeError(e); }
  });
}

function showPlay(): void {
  if (!scenario || !config) return;
  const location = scenario.locations.find(x => x.id === scenario!.opening_scene)!;
  root.innerHTML = `<main><h1></h1>${preview}<section class="card"><h2>導入</h2><div id="opening" class="opening"></div><dl><dt>現在地</dt><dd></dd><dt>プレイヤー技能</dt><dd id="skills"></dd></dl></section><section class="card"><h2>会話</h2><div id="history" class="history" aria-live="polite"></div><form id="chat"><label>プレイヤー入力<textarea id="input" required rows="3"></textarea></label><button class="primary">送信</button></form><div class="actions"><button id="new">新しいゲーム</button><button id="back">設定画面へ戻る</button></div><p id="play-status" role="status"></p></section></main>`;
  root.querySelector("h1")!.textContent = scenario.title;
  root.querySelector("dd")!.textContent = location.name;
  root.querySelector("#skills")!.textContent = Object.entries(scenario.player.skills).map(([k,v]) => `${k}: ${v}`).join(" / ");
  const history = root.querySelector<HTMLElement>("#history")!;
  const opening = root.querySelector<HTMLElement>("#opening")!;
  (Array.isArray(scenario.opening) ? scenario.opening : [scenario.opening]).forEach(line => appendTextMessage(opening, "シナリオ", line));
  messages = [{ role: "system", content: `これはPhase 1接続プレビューです。シナリオ題名は「${scenario.title}」、現在地は「${location.name}」です。状態や手掛かりを推測せず、短いGM応答を返してください。` }];
  root.querySelector("#chat")!.addEventListener("submit", async event => {
    event.preventDefault(); const input = root.querySelector<HTMLTextAreaElement>("#input")!; const raw = input.value.trim(); if (!raw) return;
    appendTextMessage(history, "あなた", raw); messages.push({ role: "user", content: raw }); input.value = "";
    const status = root.querySelector<HTMLElement>("#play-status")!; status.textContent = "GM応答を待っています…";
    try { const result = await new OpenAiCompatibleChatClient(config!).complete(messages); messages.push({ role: "assistant", content: result.content }); appendTextMessage(history, "GM", result.content); status.textContent = ""; }
    catch (e) { status.textContent = safeError(e); }
  });
  root.querySelector("#new")!.addEventListener("click", showPlay);
  root.querySelector("#back")!.addEventListener("click", showSettings);
}

void showSettings();
