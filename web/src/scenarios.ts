export interface ScenarioIndexEntry { id: string; title: string; path: string }
export interface ScenarioIndex { scenarios: ScenarioIndexEntry[] }
export interface Scenario {
  title: string;
  opening: string | string[];
  opening_scene: string;
  player: { skills: Record<string, number> };
  locations: Array<{ id: string; name: string; intro?: string }>;
}

function required(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`シナリオを読み込めません: 必須フィールド「${message}」がありません。`);
}

export function validateScenario(value: unknown): Scenario {
  required(value && typeof value === "object", "scenario");
  const s = value as Partial<Scenario>;
  required(typeof s.title === "string" && s.title.length > 0, "title");
  required(typeof s.opening === "string" || (Array.isArray(s.opening) && s.opening.every(x => typeof x === "string")), "opening");
  required(typeof s.opening_scene === "string", "opening_scene");
  required(s.player && typeof s.player.skills === "object", "player.skills");
  required(Array.isArray(s.locations), "locations");
  required(s.locations.some(location => location.id === s.opening_scene), "locations/opening_scene");
  return s as Scenario;
}

async function getJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`読み込みに失敗しました (HTTP ${response.status})。`);
  return response.json();
}

export async function loadScenarioIndex(base = import.meta.env.BASE_URL): Promise<ScenarioIndex> {
  const value = await getJson(`${base}scenarios/index.json`) as Partial<ScenarioIndex>;
  required(Array.isArray(value.scenarios), "scenarios");
  return value as ScenarioIndex;
}

export async function loadScenario(path: string, base = import.meta.env.BASE_URL): Promise<Scenario> {
  const safePath = path.replace(/^\.\//, "");
  return validateScenario(await getJson(`${base}${safePath}`));
}
