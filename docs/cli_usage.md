# CLI版の使い方

通常のプレイにはWeb版を推奨します。CLI版はWeb UIを使わない対話プレイ、入力スクリプトによる
再現確認、シナリオ開発に使用します。

## プレイ開始

```powershell
python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir .\scenario_lighthouse
```

## 主なオプション

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--version` | バージョンを表示して終了 | ― |
| `--scenario-dir DIR` | `scenario.json`を含むディレクトリ | `scenario_lighthouse` |
| `--script PATH` | 1行1コマンドのUTF-8入力 | 対話入力 |
| `--debug-judge` | 行動判定のデバッグ出力 | 無効 |
| `--debug-llm` | LLM・仲間会話のデバッグ出力 | 無効 |
| `--debug-embedding` | Embeddingのデバッグ出力 | 無効 |
| `--debug-all` | すべてのデバッグ出力 | 無効 |
| `--dice-total N` | シナリオ判定の合計値を固定 | ランダム |
| `--skill-dice-total N` | 汎用技能判定の出目を固定 | ランダム |
| `--dice-seed N` | 乱数生成器のシードを固定 | システム乱数 |

出目固定オプションはテスト・再現確認用です。通常プレイでは省略してください。

## 入力スクリプトで確認する

```powershell
python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir .\scenario_lighthouse `
  --script .\scenario_lighthouse\sample_inputs_topic_resolution.txt `
  --debug-llm
```

シナリオ作者用入力は、`md_to_scenario.py`が生成する`sample_inputs_<テスト名>.txt`を利用できます。
LLMとEmbeddingの設定は[LLM / Embedding設定](llm_configuration.md)を参照してください。
