# Chat TTRPG GM MVP

LLMがGMの描写や仲間NPCの会話を担当し、アプリケーションがシナリオ状態、NPC、手掛かり、
判定結果を管理する、ローカル実行型のチャットTTRPGです。通常のプレイにはWeb版を推奨します。

<img width="1115" height="628" alt="Chat TTRPG GM MVPのプレイ画面" src="https://github.com/user-attachments/assets/f6f2c73c-f0c9-4eac-a6ab-a342f82a51e5" />

## クイックスタート

### 1. インストール

Python 3.10以降を使用してください。

```bash
python -m pip install -r requirements-web.txt
```

### 2. Web版を起動

#### Windowsで簡単に起動する

エクスプローラーから`start_web.bat`をダブルクリックするか、コマンドプロンプトで実行します。
依存関係の確認後、Web APIとブラウザが起動します。

```bat
start_web.bat
```

#### PowerShell・macOS・Linux、または端末から起動する

```bash
python web_api.py
```

ブラウザが自動で開かない場合は、<http://127.0.0.1:8000> を開いてください。
`start_web.bat`と`python web_api.py`を両方実行する必要はありません。

> [!IMPORTANT]
> このWebサーバーは認証やTLSを備えた公開用サーバーではありません。`127.0.0.1`で利用し、
> インターネットへ公開しないでください。

### 起動方法の違い

| 方法 | 対象 | 用途 |
| --- | --- | --- |
| `start_web.bat` | Windows | 通常利用向け。依存関係を確認してWeb APIとブラウザをまとめて起動 |
| `python web_api.py` | Windows / macOS / Linux | Web版の標準的な手動起動 |
| `python web_api.py --debug-all` | 全OS | 詳細ログを表示して問題を調査 |
| `python -m uvicorn web_api:app ...` | 開発者 | ホストやポートを明示してWeb APIを起動 |
| `python fixed_truth_ai_gm_mvp.py ...` | CLI利用者・作者 | Web UIを使わずゲームエンジンを直接実行 |
| `python run_authoring_pipeline.py ...` | シナリオ作者 | シナリオの変換、Lint、テストを一括実行 |

`start_web.bat`はllama.cppを自動起動せず、URL、モデル、シナリオ、APIキーも保持・変更しません。
詳しい起動方法とWeb版の挙動は[Web版セットアップ](docs/web_setup.md)を参照してください。

## 初回設定

初回起動時は画面上部の「接続設定」が開きます。次の順で進めます。

1. シナリオを選択する
2. ChatとEmbeddingを設定する
3. それぞれの接続テストを実行する
4. 設定を保存する
5. ゲームを開始する

### Geminiを使う

| 項目 | Chat | Embedding |
| --- | --- | --- |
| Provider | `openai_compatible` | ― |
| Base URL | `https://generativelanguage.googleapis.com/v1beta/openai` | 同左 |
| Model | `gemini-3.5-flash` | `gemini-embedding-2` |
| API Key | Google AI Studioなどで取得したGemini APIキー | Chatと同じキー |

この構成では、接続テスト、Embedding、TABLE_TURN、仲間会話を確認済みです。ただし、提供側の
仕様変更やAPI制限を含め、将来の動作や生成品質を保証するものではありません。

### llama.cppを使う

ローカルChatモデルの動作確認実績に基づく推奨は**Gemma 3 12B**です。特定のGGUFや量子化方式は
固定推奨しません。Chatは`http://127.0.0.1:8080/v1`、Embeddingは
`http://127.0.0.1:8081/v1`のように、別モデル・別ポートで起動します。

モデル名、APIキー、VRAM 8GB環境での注意を含む詳細は
[LLM / Embedding設定](docs/llm_configuration.md)を参照してください。

## 基本的な使い方

* ChatとEmbeddingの接続テストを実行してから設定を保存します。
* 保存した設定は次に開始するゲームから反映されます。
* ゲーム中のセッションはPythonプロセスのメモリ内だけにあり、APIを停止すると失われます。
* APIキーは`settings.json`へ保存されず、Pythonプロセス終了時に失われます。

## よくある問題

### Web UIで保存したモデルと実ゲームのモデルが違う

環境変数はWeb UIの保存値より優先される場合があります。過去のローカル設定、特に
`LLAMA_CPP_MODEL`、`LLM_MODEL`、`OPENAI_MODEL`が残っていないか確認してください。

### 接続テストは成功するが実ゲームだけ404になる

`--debug-all`で起動し、`TABLE_TURN_CONFIG`と`TABLE_TURN_BODY`のモデル名を確認します。
Gemini利用時に`local-model`が表示される場合は、環境変数による上書きを確認してください。

### 仲間の台詞が途中で切れる

`[TABLE_TURN_TRUNCATED]`または`finish_reason=length`を確認してください。TABLE_TURNの既定の
`max_tokens`は`2048`で、`TABLE_TURN_MAX_TOKENS`により上書きできます。

PowerShellでの環境変数確認・解除方法やログ例は[トラブルシューティング](docs/troubleshooting.md)を
参照してください。

## その他の利用方法

### CLI版を使う

Web UIを使わず直接プレイしたり、入力スクリプトで再現確認したりする場合は
[CLI版の使い方](docs/cli_usage.md)を参照してください。

### シナリオを作成する

シナリオの変換、Lint、自動テスト、手動プレイの流れは
[シナリオ作成ワークフロー](docs/authoring_workflow.md)を参照してください。

## ドキュメント

* [Web版セットアップ](docs/web_setup.md) — `.bat`と`.py`の使い分け、初回設定、保存範囲
* [LLM / Embedding設定](docs/llm_configuration.md) — Gemini、llama.cpp、環境変数、生成パラメータ
* [トラブルシューティング](docs/troubleshooting.md) — 接続、設定上書き、TABLE_TURNの調査
* [CLI版の使い方](docs/cli_usage.md) — `fixed_truth_ai_gm_mvp.py`のオプションとデバッグ
* [シナリオ作成ワークフロー](docs/authoring_workflow.md) — 変換、Lint、テスト
* [Authoring Guide](docs/authoring_guide.md) — シナリオ記法の詳細
* [Authoring Best Practices](docs/authoring_best_practices.md) — シナリオ設計の推奨事項
* [Authoring Prompt](docs/authoring_prompt.md) — LLMを使った作者向けプロンプト

## 特徴

* チャット形式のWeb UIとCLI
* ロケーション、NPC、手掛かり、条件付き情報開示、複数解決ルートの状態管理
* Embeddingによる行動判定と5段階の判定結果
* LLMによるGM描写と仲間NPCの掛け合い
* NPCごとの知識・話題管理と公開済み情報の境界維持
* Markdownで記述する作者向けシナリオと検証パイプライン

現行版: **v2.30.0 明示的な仲間ルーティング** (`v2.30.0 [explicit-companion-routing]`)

バージョンの正本は`fixed_truth_ai_gm_mvp.py`の`VERSION`です。

## 設計の概要

Python版をゲームルール、セッション状態、情報境界、LLM／Embedding判定の唯一の正本とします。
Web UIは同一プロセスのFastAPIを操作するフロントエンドであり、ブラウザから外部LLM APIへ
直接接続しません。正式な発見やゲーム状態はアプリケーションが管理し、LLMは描写、会話、仮説、
雰囲気表現を担当します。
