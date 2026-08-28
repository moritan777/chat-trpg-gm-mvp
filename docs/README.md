# ドキュメント案内

Chat TTRPG GM MVPの利用者・シナリオ作者・開発者向け資料をまとめています。
初めて利用する場合は、ルートの[README](../README.md)にあるクイックスタートから始めてください。

## 利用者向け

| やりたいこと | 参照先 |
| --- | --- |
| Web版をインストールして起動する | [Web版セットアップ](web_setup.md) |
| Geminiやllama.cppを設定する | [LLM / Embedding設定](llm_configuration.md) |
| 起動・接続・応答の問題を調べる | [トラブルシューティング](troubleshooting.md) |
| Web UIを使わずにプレイ・再現確認する | [CLI版の使い方](cli_usage.md) |

最短の流れは「Web版セットアップ → LLM / Embedding設定」です。問題が起きた場合だけ
トラブルシューティングを参照してください。

## シナリオ作者向け

次の順序で読むと、シナリオの作成から検証まで進められます。

1. [シナリオ作成ワークフロー](authoring_workflow.md) — 編集、変換、Lint、自動テスト、手動プレイの全体像
2. [Authoring Guide](authoring_guide.md) — 各要素の記法と情報境界
3. [Authoring Best Practices](authoring_best_practices.md) — シナリオ設計と自然言語導線の推奨事項
4. [Scenario Template](scenario_template.md) — 新規シナリオのひな型
5. [Authoring Prompt](authoring_prompt.md) — LLMとシナリオを作成・レビューするためのプロンプト

作者用Markdownの正本から生成した`scenario_*`ディレクトリは派生物です。編集対象と生成物の
区別や、使用するコマンドはシナリオ作成ワークフローで確認してください。

## 開発・調査資料

| 資料 | 位置づけ |
| --- | --- |
| [自由行動ルーティング競合 調査結果](investigations/free_action_routing_conflict.md) | 特定のルーティング問題に関する原因分析と修正方針の記録 |

`investigations/`以下は調査時点の内部記録です。通常のセットアップやシナリオ作成の手順では
ないため、利用者・作者向け資料と分けて管理しています。

## 文書を更新するときの方針

* 初回導入に必要な最小手順はルートの`README.md`に置き、詳細は`docs/`へリンクします。
* 同じ設定値や手順を複数の文書へ複製せず、詳しく説明する文書を一つ決めて参照します。
* 利用者向け、シナリオ作者向け、内部の調査記録を混在させません。
* ファイルを追加・改名した場合は、この案内とルートREADMEのリンクを確認します。
