import { describe, expect, it } from "vitest";

import { buildHeaders, chatCompletionsUrl, normalizeBaseUrl } from "../src/api/openAiCompatibleChatClient";

describe("OpenAI compatible API helpers", () => {
  it("normalizes trailing slashes and repeated v1", () => {
    expect(normalizeBaseUrl(" http://127.0.0.1:8080/v1/ ")).toBe("http://127.0.0.1:8080/v1");
    expect(normalizeBaseUrl("http://localhost:8080/v1/v1/")).toBe("http://localhost:8080/v1");
  });
  it("builds one chat completions segment", () => expect(chatCompletionsUrl("http://localhost:8080/v1/")).toBe("http://localhost:8080/v1/chat/completions"));
  it("omits Authorization for an empty key", () => expect(buildHeaders("")).not.toHaveProperty("Authorization"));
  it("adds Authorization only for a supplied key", () => expect(buildHeaders("secret").Authorization).toBe("Bearer secret"));
});
