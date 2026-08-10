import { appendTextMessage } from "../src/render";

describe("browser security boundaries", () => {
  it("renders an LLM response through textContent, never innerHTML", () => {
    const created: FakeElement[] = [];
    class FakeElement {
      className = ""; textContent = ""; children: FakeElement[] = [];
      append(...nodes: FakeElement[]) { this.children.push(...nodes); }
    }
    vi.stubGlobal("document", { createElement: () => { const node = new FakeElement(); created.push(node); return node; } });
    const container = new FakeElement();
    appendTextMessage(container as unknown as HTMLElement, "GM", '<img src=x onerror="alert(1)">');
    expect(created.some(node => node.textContent.includes("<img"))).toBe(true);
    expect(created.every(node => !("innerHTML" in node))).toBe(true);
    vi.unstubAllGlobals();
  });
  it("does not write an API key to Web Storage", async () => {
    const setItem = vi.fn(); vi.stubGlobal("localStorage", { setItem }); vi.stubGlobal("sessionStorage", { setItem });
    const { OpenAiCompatibleChatClient } = await import("../src/api/openAiCompatibleChatClient");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ choices: [{ message: { content: "OK" } }] }) }));
    await new OpenAiCompatibleChatClient({ baseUrl: "http://localhost:8080/v1", model: "m", apiKey: "secret" }).complete([{ role: "user", content: "x" }]);
    expect(setItem).not.toHaveBeenCalled(); vi.unstubAllGlobals();
  });
});
