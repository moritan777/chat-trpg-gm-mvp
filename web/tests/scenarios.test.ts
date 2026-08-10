import { afterEach, describe, expect, it, vi } from "vitest";

import { loadScenario, loadScenarioIndex, validateScenario } from "../src/scenarios";

const scenario = { title: "灯台", opening: ["開始"], opening_scene: "harbor", player: { skills: {} }, locations: [{ id: "harbor", name: "港" }] };
describe("scenario loading", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("loads the index", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ scenarios: [] }) })); expect((await loadScenarioIndex("/base/")).scenarios).toEqual([]); expect(fetch).toHaveBeenCalledWith("/base/scenarios/index.json"); });
  it("loads and validates a scenario", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => scenario })); expect((await loadScenario("scenarios/lighthouse/scenario.json", "/")).title).toBe("灯台"); });
  it("reports a missing required field", () => expect(() => validateScenario({ ...scenario, title: undefined })).toThrow("必須フィールド「title」"));
});
