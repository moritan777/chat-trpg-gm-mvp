# LLM / Embedding設定

## Gemini API

Web版で接続と基本プレイを確認できた構成です。

| 項目 | Chat | Embedding |
| --- | --- | --- |
| Provider | `openai_compatible` | ― |
| Base URL | `https://generativelanguage.googleapis.com/v1beta/openai` | 同左 |
| Model | `gemini-3.5-flash` | `gemini-embedding-2` |
| API Key | Google AI Studioなどで取得したGemini APIキー | Chatと同じキー |

Chat接続、Embedding接続、TABLE_TURNによるGM応答、仲間1名への直接会話、仲間4名での会話、
発言者分類、仲間会話履歴への保存を確認済みです。ニコの連想、ピピの気遣い、クロの怪談や誇張、
ガランの行動提案という傾向も概ね反映されました。

> [!NOTE]
> 今回の構成で確認した結果であり、品質や将来の動作を保証しません。モデル名、提供仕様、API制限は
> 変更される可能性があります。

## llama.cpp

ローカルChatモデルの動作確認実績に基づく推奨は**Gemma 3 12B**です。VRAM、RAM、CPUに応じて
量子化とコンテキスト長を選ぶため、特定のGGUFファイル名は固定推奨しません。VRAM 8GBでは、
量子化モデルやコンテキスト長の調整が必要になる可能性があります。

### Chat

```text
Provider: llama_cpp
Base URL: http://127.0.0.1:8080/v1
Model: local-model
API Key: 空欄
```

### Embedding

```text
Base URL: http://127.0.0.1:8081/v1
Model: local-embedding
API Key: 空欄
```

Chat用とEmbedding用は別モデル・別ポートで起動します。モデル名は各llama.cppサーバーが
受け付ける識別子に合わせてください。

## 環境変数と優先順位

Chat URLは`LLAMA_CPP_BASE_URL`、`LLM_BASE_URL`、`OPENAI_BASE_URL`の順、Chat Modelは
`LLAMA_CPP_MODEL`、`LLM_MODEL`、`OPENAI_MODEL`の順に参照します。Embedding URLは
`EMBEDDING_BASE_URL`、`EMB_BASE_URL`の順、モデルは`EMBEDDING_MODEL`、`EMB_MODEL`の順です。

ローカル運用から外部APIへ切り替える場合は、次の変数が残っていないか確認します。

```text
LLAMA_CPP_BASE_URL
LLAMA_CPP_MODEL
LLM_BASE_URL
LLM_MODEL
OPENAI_BASE_URL
OPENAI_MODEL
EMBEDDING_BASE_URL
EMBEDDING_MODEL
EMB_BASE_URL
EMB_MODEL
```

ほかのアプリケーションへの影響を確認し、必要な変数まで無条件に削除しないでください。

## 生成パラメータ

| 環境変数 | 用途 | 既定値・フォールバック |
| --- | --- | --- |
| `TABLE_TURN_MAX_TOKENS` | TABLE_TURNの出力上限 | `2048` |
| `TABLE_TURN_TEMPERATURE` | TABLE_TURNの生成温度 | `GM_LINE_REWRITE_TEMPERATURE`、その後`0.9` |
| `GM_REWRITE_TEMPERATURE` | GM文書き換え | `GM_COMMENTARY_TEMPERATURE`、その後`0.45` |
| `BANTER_TEMPERATURE` | 旧来の独立した仲間会話経路 | `0.75` |
| `DISCOVERY_DISPLAY` | 発見表示（`gm` / `both` / `tag`） | `gm` |

`TABLE_TURN_MAX_TOKENS`には整数文字列を指定します。

```powershell
$env:TABLE_TURN_MAX_TOKENS="3072"
python web_api.py --debug-all
```

既定値へ戻す場合:

```powershell
Remove-Item Env:TABLE_TURN_MAX_TOKENS -ErrorAction SilentlyContinue
python web_api.py --debug-all
```

`TABLE_TURN_TEMPERATURE`の通常利用の目安は`0.8`〜`1.0`、開始値は既定の`0.9`です。結果は
モデル、量子化、サーバー側sampling、シナリオによって変わるため品質を保証する値ではありません。

## Embedding接続テストとゲーム中fallback

接続テストは1件の入力で疎通とレスポンス形状を確認します。ゲーム中はプレイヤー入力と複数の `positive_examples` を一括送信するため、接続テスト成功だけではゲーム中の複数入力リクエスト成功を保証しません。

ゲーム中の全Embedding endpointが失敗すると、そのGameセッションでは追加送信を止めてlexical判定へ移ります。`--debug-embedding`または`--debug-all`では `[EMB_FALLBACK]` の `reason`、`mode=lexical`、`session_disabled`を確認できます。認証情報やレスポンス本文は出力しません。設定変更は新規Webセッション作成時に新しいGameへ取り込まれるため、既存セッションのメモリcacheは新規セッションへ引き継がれません。
