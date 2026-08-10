import type { ChatCompletionRequest, ChatCompletionResult, ChatConnectionConfig, ChatMessage } from "./types";

export class ChatClientError extends Error {
  constructor(public readonly kind: "http" | "network" | "response" | "config", public readonly status?: number) {
    super(kind);
  }
}

export function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (!trimmed) throw new ChatClientError("config");
  let url: URL;
  try { url = new URL(trimmed); } catch { throw new ChatClientError("config"); }
  if (url.protocol !== "http:" && url.protocol !== "https:") throw new ChatClientError("config");
  url.pathname = url.pathname.replace(/\/+$/, "").replace(/(?:\/v1)+$/, "/v1");
  return url.toString().replace(/\/$/, "");
}

export function chatCompletionsUrl(baseUrl: string): string {
  return `${normalizeBaseUrl(baseUrl)}/chat/completions`;
}

export function buildHeaders(apiKey: string): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" };
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
  return headers;
}

export class OpenAiCompatibleChatClient {
  constructor(private readonly config: ChatConnectionConfig) {}

  async complete(messages: ChatMessage[], maxTokens = 120): Promise<ChatCompletionResult> {
    const request: ChatCompletionRequest = { model: this.config.model.trim(), messages, max_tokens: maxTokens, temperature: 0.2 };
    if (!request.model) throw new ChatClientError("config");
    const started = performance.now();
    let response: Response;
    try {
      response = await fetch(chatCompletionsUrl(this.config.baseUrl), {
        method: "POST", headers: buildHeaders(this.config.apiKey), body: JSON.stringify(request),
      });
    } catch { throw new ChatClientError("network"); }
    if (!response.ok) throw new ChatClientError("http", response.status);
    let payload: unknown;
    try { payload = await response.json(); } catch { throw new ChatClientError("response", response.status); }
    const data = payload as { model?: unknown; choices?: Array<{ message?: { content?: unknown } }> };
    const content = data.choices?.[0]?.message?.content;
    if (typeof content !== "string") throw new ChatClientError("response", response.status);
    return { content, model: typeof data.model === "string" ? data.model : request.model, elapsedMs: Math.round(performance.now() - started) };
  }
}
