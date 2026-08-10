import { defineConfig } from "vitest/config";

export default defineConfig(({ command }) => ({
  // GitHub Actions sets this to /<repository-name>/; local builds use /.
  base: command === "serve" ? "/" : "/chat-trpg-gm-mvp/",
  test: { environment: "node" },
}));
