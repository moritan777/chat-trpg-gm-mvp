# Chat TTRPG GM MVP
## Example Session
<img width="1115" height="628" alt="image" src="https://github.com/user-attachments/assets/f6f2c73c-f0c9-4eac-a6ab-a342f82a51e5" />


LLM を利用したチャット型 TTRPG GM エンジンです。

シナリオは Markdown で記述し、実行用の `scenario.json` に変換してプレイします。

このプロジェクトは、

* ロケーション管理
* NPC管理
* 手掛かり管理
* 条件付き情報開示
* 複数解決ルート

をアプリ側で管理し、

* 描写
* 会話
* 仲間NPCの掛け合い
* 雰囲気表現

を LLM が担当する構成を採用しています。

---

# 特徴

* チャット形式でプレイ可能
* ロケーション移動
* NPC会話
* オブジェクト調査
* 手掛かり管理
* 条件付き手掛かり
* 複数解決ルート
* NPCごとの知識管理
* NPCごとの話題管理
* LLMによるGM描写
* Embeddingによる行動判定

---

# LLM / Embedding 設定

> ⚠️ 本プロジェクトは OpenAI 互換 API を提供する LLM サーバーを前提としています。
>
> 動作確認は **llama.cpp server** と **ローカル Embedding Server** の組み合わせで行っています。

## 必要サービス

実行前に以下を起動してください。

```text
LLM Server
Embedding Server
```

例:

```text
LLM        : http://127.0.0.1:8080/v1
Embedding  : http://127.0.0.1:8081/v1
```

\*\*\*

## 環境変数

### LLM

```powershell
$env:LLM_PROVIDER="llama_cpp"
$env:LLAMA_CPP_BASE_URL="http://127.0.0.1:8080/v1"
```

### Embedding

```powershell
$env:EMBEDDING_BASE_URL="http://127.0.0.1:8081/v1"
```

### 発見表示

通常プレイ:

```powershell
$env:DISCOVERY_DISPLAY="gm"
```

デバッグ表示:

```powershell
$env:DISCOVERY_DISPLAY="both"
```

\*\*\*

## 接続確認

ゲーム起動時に以下のような表示が出れば正常です。

```text
LLM: 有効 provider=llama_cpp
Embedding: http://127.0.0.1:8081/v1
```

\*\*\*

## トラブルシューティング

### LLMが反応しない

確認:

```powershell
echo $env:LLM_PROVIDER
echo $env:LLAMA_CPP_BASE_URL
```

期待値:

```text
llama_cpp
http://127.0.0.1:8080/v1
```

\*\*\*

### Embeddingが反応しない

確認:

```powershell
echo $env:EMBEDDING_BASE_URL
```

期待値:

```text
http://127.0.0.1:8081/v1
```

\*\*\*

### 仲間会話が出ない

デバッグ実行時に以下を確認してください。

```text
TABLE_TURN_STATUS] 200 OK
```

表示されない場合、GMエンジンからLLMサーバーへの接続に失敗しています。

---

また README 冒頭は、GitHub向けなら次のようにするとかなり分かりやすくなります。

```markdown
# Chat TTRPG GM MVP

LLM を利用したチャット型 TTRPG GM エンジンです。

シナリオは Markdown で記述し、実行用の `scenario.json` に変換してプレイします。

> ⚠️ OpenAI 互換 API を提供する LLM サーバーが必要です。
>
> 動作確認環境:
>
> - llama.cpp server
> - ローカル Embedding Server
> - Python 3.10+
```

# 必要ファイル

通常利用に必要なのは以下の5ファイルです。

```text
author_scenario_xxx.md
md_to_scenario.py
scenario_lint.py
run_authoring_pipeline.py
fixed_truth_ai_gm_mvp.py
````

---

# ファイル構成

## author_scenario_xxx.md

シナリオ本体です。

場所・NPC・オブジェクト・手掛かり・ゴール・テストケースを1つのMarkdownで管理します。

\---

## md_to_scenario.py

Markdownから実行用データを生成します。

入力:

```text
author_scenario_xxx.md
```

出力:

```text
scenario.json
test_expectations.json
sample_inputs_*.txt
```

---

## scenario_lint.py

シナリオの整合性を検査します。

検査例:

* 存在しない location
* 存在しない NPC
* 存在しない discoverable
* 不正な参照関係

\---

## run_authoring_pipeline.py

作者向けの一括検証ツールです。

以下を自動実行します。

```text
Markdown変換
↓
Lint
↓
自動テスト
↓
期待結果チェック
```

\---

## fixed_truth_ai_gm_mvp.py

ゲーム本体です。

プレイヤーとの会話を受け取り、シナリオの状態管理と LLM 描写を統合してセッションを進行します。

---

# クイックスタート

## 1\. シナリオ変換

```powershell
python .\md_to_s*enario*py `
.\author_scenario_lighthous*_v2150.md `
.\scenario_lighthous*\scenario.json
```

\---

## 2\. シナリオ検査

```powershell
python .\scenario_lin*.py `
  .\scenario_lighthouse\scen*rio.json
```

期待結果:

```text
Lint result: 0 errors, 0 warnings
```

\---

## 3\. 自動テスト

```powershell
python .\run_authoring_pipeline.py `
 .\author_scenario_lighthouse_v2150.md `
 .\scenario_lighthouse `
 --engine .\fixed_truth_ai_gm_mvp.py
```

---

## 4. プレイ開始

```powershell
$env:DISCOVERY_DISPLAY="gm"

python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir .\scenario_lighthouse
```

\---

# NPC知識システム

NPCごとに、

```json
{
  "location": "tavern",

  "knows": [
    "fisherman_blue_light"
  ],

  "topics": {
    "青い光": [
      "fisherman_blue_light"
    ]
  }
}
```

を設定できます。

意味:

```text
どこにいるか
↓
何を知っているか
↓
何について聞いたら話すか
```

を分離して管理します。

例:

```text
村長に青い光を聞く
↓
知らない

漁師に青い光を聞く
↓
知っている
```

\---

# シナリオ作成の流れ

```text
author_scenario_xxx.md 編集
↓
run_authoring_pipeline.py
↓
手動プレイ
↓
修正
↓
公開
```

\---

# 設計方針

アプリケーションは状態管理に専念します。

```text
location
NPC
手掛かり
条件
```

を管理し、

```text
会話
描写
雰囲気
仲間会話
```

は LLM が担当します。

つまり、

```text
アプリは意味を作らない
アプリは情報を整理する
意味と表現はLLMが担当する
```

という設計思想を採用しています。

```



