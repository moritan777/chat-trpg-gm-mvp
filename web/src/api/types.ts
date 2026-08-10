export interface ChatConnectionConfig { baseUrl: string; model: string; apiKey: string }
export interface ChatMessage { role: "system" | "user" | "assistant"; content: string }
export interface ChatCompletionRequest { model: string; messages: ChatMessage[]; max_tokens?: number; temperature?: number }
export interface ChatCompletionResult { content: string; model: string; elapsedMs: number }

/** Reserved for a later phase. Chat and embedding settings intentionally remain independent. */
export interface EmbeddingConnectionConfig {
  mode: "remote" | "browser" | "disabled";
  baseUrl?: string;
  model?: string;
  apiKey?: string;
}
