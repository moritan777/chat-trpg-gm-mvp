# シナリオ作成ワークフロー

シナリオ記法は[Authoring Guide](authoring_guide.md)、設計上の推奨事項は
[Authoring Best Practices](authoring_best_practices.md)を参照してください。

## 使用するファイルとツール

| ファイル | 役割 |
| --- | --- |
| `author_scenario_xxx.md` | fenced `scenario-json`ブロックを正本として、場所、NPC、手掛かり、ゴール、テストを記述 |
| `md_to_scenario.py` | 正本Markdownから派生物の`scenario.json`、`test_expectations.json`、`sample_inputs_*.txt`を生成 |
| `scenario_lint.py` | location、NPC、discoverableなどの参照整合性を検査 |
| `run_authoring_pipeline.py` | 変換、Lint、自動テスト、期待結果確認を一括実行 |
| `fixed_truth_ai_gm_mvp.py` | ゲーム本体。最後の手動プレイにも使用 |

## 推奨手順

### 1. シナリオを編集する

`author_scenario_xxx.md`内の fenced `scenario-json`ブロックだけをランタイム定義の正本として編集します。`scenario.json`、`sample_inputs_*.txt`、`test_expectations.json`は派生生成物なので、派生物だけを直接修正しません。

### 2. 変換する

```powershell
python .\md_to_scenario.py `
  .\author_scenario_lighthouse_v2150.md `
  .\web\public\scenarios\lighthouse\scenario.json
```

### 3. Lintする

```powershell
python .\scenario_lint.py `
  .\scenario_lighthouse\scenario.json
```

期待結果:

```text
Lint result: 0 errors, 0 warnings
```

### 4. パイプラインを実行する

```powershell
python .\run_authoring_pipeline.py `
  .\author_scenario_lighthouse_v2150.md `
  .\scenario_lighthouse `
  --engine .\fixed_truth_ai_gm_mvp.py `
  --test-timeout 120 `
  --debug-judge
```

主なデバッグオプションは`--debug-judge`、`--debug-llm`、`--debug-embedding`、`--debug-all`です。

### 5. 手動プレイする

Web版、またはCLI版で変換後のシナリオを確認します。CLIの詳細は[CLI版の使い方](cli_usage.md)を
参照してください。

```powershell
python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir .\scenario_lighthouse
```

修正後は変換から手動プレイまでを繰り返します。
