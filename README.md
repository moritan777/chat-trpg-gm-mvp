# Chat TTRPG GM MVP

現行版: **v2.15.17 仲間アーキタイプ2名追加** (`v2.15.17 [two-more-companion-archetypes]`)

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
* 卓の参加者らしい仲間同士の雑談
* 指定した仲間による同一場面内の会話継続
* クロ（ホラ吹き）とガラン（行動派）を含む5人の仲間アーキタイプ
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

---

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

### LLM / Embeddingパラメータ一覧

READMEを実行設定の正本とします。値はプロセス環境から読み込みます。

| 環境変数 | 役割・主な使用経路 | 既定値・上書き関係 |
| --- | --- | --- |
| `LLM_PROVIDER` | LLM経路の有効化。`none`でローカルLLM呼び出しを無効化 | `llama_cpp` |
| `LLAMA_CPP_BASE_URL` | OpenAI互換LLM APIのベースURL | `http://127.0.0.1:8080/v1`。未設定時は旧互換の`LLM_BASE_URL`、`OPENAI_BASE_URL`の順に参照 |
| `TABLE_TURN_TEMPERATURE` | GM描写と仲間発言を統合生成するTable Turn経路 | `0.9`。未設定時は`GM_LINE_REWRITE_TEMPERATURE`を参照 |
| `GM_LINE_REWRITE_TEMPERATURE` | Table Turn温度の旧互換フォールバック | 単独の既定値なし。両方未設定ならTable Turnは`0.9` |
| `GM_REWRITE_TEMPERATURE` | Table Turnが使えない場合などのGM文書き換え経路 | 未設定時は`GM_COMMENTARY_TEMPERATURE`、さらに未設定なら`0.45` |
| `GM_COMMENTARY_TEMPERATURE` | GM文書き換え温度の旧互換フォールバック | 単独の既定値なし。上記経路の最終既定値は`0.45` |
| `BANTER_TEMPERATURE` | 旧来の独立した仲間会話生成経路。Table Turn温度とは別 | `0.75` |
| `EMBEDDING_BASE_URL` | OpenAI互換Embedding APIのベースURL | `http://127.0.0.1:8081/v1`。未設定時は旧互換の`EMB_BASE_URL`を参照 |
| `DISCOVERY_DISPLAY` | 正式発見の表示方法（`gm` / `both` / `tag`） | `gm` |

### Table Turn生成温度

`TABLE_TURN_TEMPERATURE`は、GM描写と仲間発言を一度に生成するTable Turnレンダリングの`temperature`を指定します。既定値は**0.9**、通常利用の目安は**0.8〜1.0**、推奨開始値は**0.9**です。低温度・高温度の利用を禁止する範囲指定ではありません。

温度の優先順位は実装上、次のとおりです。主設定には`TABLE_TURN_TEMPERATURE`を推奨します。

1. `TABLE_TURN_TEMPERATURE`
2. `GM_LINE_REWRITE_TEMPERATURE`（旧互換）
3. 既定値`0.9`

`BANTER_TEMPERATURE`は旧来の独立した仲間会話経路用であり、統合Table Turnには使われません。`GM_REWRITE_TEMPERATURE`、`GM_COMMENTARY_TEMPERATURE`、Embedding設定、LLMサーバー自体のsampling設定も今回のTable Turn設定とは別です。

PowerShellで現在のセッションに設定し、通常どおり起動する例:

```powershell
$env:TABLE_TURN_TEMPERATURE="0.9"

python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir scenario_lighthouse_from_md_v2150 `
  --script story_banter_v2152.txt `
  --dice-total 3 `
  --debug-judge `
  --debug-llm
```

現在値の確認と、設定を解除して既定値へ戻す方法:

```powershell
echo $env:TABLE_TURN_TEMPERATURE
Remove-Item Env:TABLE_TURN_TEMPERATURE -ErrorAction SilentlyContinue
```

`$env:`による設定は、原則として現在のPowerShellプロセスと、そこから起動した子プロセスにだけ適用されます。永続設定ではありません。`GM_LINE_REWRITE_TEMPERATURE`も設定されている場合、Table Turnを完全に既定値へ戻すには同様に解除してください。

比較試験で観察された目安は次のとおりです。絶対的な品質保証ではありません。

* **0.7（安定寄り）:** 発言者や行数が同じ型へ寄りやすい場合があります。
* **0.9（既定値）:** 安定性を保ちながら、仲間の発言者・順序・行数へ適度な揺れを与えます。
* **1.0（多様性寄り）:** 発言者順の揺れが増える一方、短すぎる発言や描写の振れが増える場合があります。

実際の傾向は、使用モデル、量子化、sampling設定、シナリオ内容によって変わります。高温度では会話の多様性が増える一方、Canonical外の推測、曖昧な発言、内容の薄い短文が増える可能性があります。正式発見はエンジンが原文表示しますが、LLM生成GM文や仲間の仮説には揺れが生じ得ます。

#### 温度の比較試験

同じコマンドを、温度だけを`0.7`、`0.9`、`1.0`へ変えて複数回実行します。

```powershell
$env:TABLE_TURN_TEMPERATURE="0.7"
python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir scenario_lighthouse_from_md_v2150 `
  --script story_banter_v2152.txt `
  --dice-total 3 `
  --debug-judge `
  --debug-llm

$env:TABLE_TURN_TEMPERATURE="0.9"
# 同じpythonコマンドを複数回実行

$env:TABLE_TURN_TEMPERATURE="1.0"
# 同じpythonコマンドを複数回実行
```

同じシナリオ、スクリプト、`dice-total`を使い、他の生成設定を同時に変えないでください。`--debug-llm`の`[TABLE_TURN_TEMPERATURE]`で実際の値を確認します。人間による定性的確認として、仲間行数、発言者順、ニコ・リュート・ピピの登場回数、仲間への働きかけ、短い応答、Canonical外情報、内容の薄い短文、正式発見の表示を観察します。

温度には数値を指定してください。不正値は暗黙に置換・丸めせず、原因となった環境変数名と値を示すエラーになります。

### 発見表示

通常プレイ:

```powershell
$env:DISCOVERY_DISPLAY="gm"
```

デバッグ表示:

```powershell
$env:DISCOVERY_DISPLAY="both"
```

---

## 接続確認

ゲーム起動時に以下のような表示が出れば正常です。

```text
LLM: 有効 provider=llama_cpp
Embedding: http://127.0.0.1:8081/v1
```

---

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

---

### Embeddingが反応しない

確認:

```powershell
echo $env:EMBEDDING_BASE_URL
```

期待値:

```text
http://127.0.0.1:8081/v1
```

---

### 仲間会話が出ない

デバッグ実行時に以下を確認してください。

```text
TABLE_TURN_STATUS] 200 OK
```

表示されない場合、GMエンジンからLLMサーバーへの接続に失敗しています。

---

# 必要ファイル

通常利用に必要なのは以下の5ファイルです。

```text
author_scenario_xxx.md
md_to_scenario.py
scenario_lint.py
run_authoring_pipeline.py
fixed_truth_ai_gm_mvp.py
```

---

# ファイル構成

## author_scenario_xxx.md

シナリオ本体です。

場所・NPC・オブジェクト・手掛かり・ゴール・テストケースを1つのMarkdownで管理します。

---

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

---

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

引数とオプション:

| 引数 / オプション | 必須 | 説明 | 既定値 |
| --- | --- | --- | --- |
| `author_md` | はい | 変換する作者向けシナリオ Markdown | - |
| `out_dir` | はい | `scenario.json`、テスト期待値、入力スクリプトの出力先 | - |
| `--engine PATH` | いいえ | 自動テストに使う GM エンジン | `fixed_truth_ai_gm_mvp.py` |
| `--test-timeout SECONDS` | いいえ | 各テストに許可する秒数（0 より大きい値） | `120` |
| `--debug-judge` | いいえ | 判定経路のデバッグ出力を有効化。サンプルシナリオの期待結果確認に必要 | 無効 |
| `--debug-llm` | いいえ | LLM のデバッグ出力を有効化 | 無効 |
| `--debug-embedding` | いいえ | Embedding のデバッグ出力を有効化 | 無効 |
| `--debug-all` | いいえ | 上記すべてのデバッグ出力を有効化 | 無効 |

`author_scenario_lighthouse_v2150.md` のテスト期待値には、判定経路を示す
`[GoalPath]` が含まれます。このサンプルを検証するときは `--debug-judge`（または
`--debug-all`）を指定してください。

---

## fixed_truth_ai_gm_mvp.py

ゲーム本体です。

プレイヤーとの会話を受け取り、シナリオの状態管理と LLM 描写を統合してセッションを進行します。

---

# クイックスタート

## 1. シナリオ変換

```powershell
python .\md_to_scenario.py `
  .\author_scenario_lighthouse_v2150.md `
  .\scenario_lighthouse\scenario.json
```

---

## 2. シナリオ検査

```powershell
python .\scenario_lint.py `
  .\scenario_lighthouse\scenario.json
```

期待結果:

```text
Lint result: 0 errors, 0 warnings
```

---

## 3. 自動テスト

```powershell
python .\run_authoring_pipeline.py `
  .\author_scenario_lighthouse_v2150.md `
  .\scenario_lighthouse `
  --engine .\fixed_truth_ai_gm_mvp.py `
  --test-timeout 120 `
  --debug-judge
```

---

## 4. プレイ開始

```powershell
$env:DISCOVERY_DISPLAY="gm"

python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir .\scenario_lighthouse
```

---

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

---

# 調査対象のスコープ

オブジェクトを調査するときは、現在地の `visible_objects` に含まれるものだけが候補になります。
別の場所にある同名・同一 alias のオブジェクトが選ばれることはありません。

NPCは従来どおり全体から対象を解決し、現在地にいない場合はシナリオに設定された所在地ヒントを案内します。

---

# 仲間会話

v2.15.2 では、仲間はGMの説明を繰り返す解説役ではなく、同じ卓の参加者として反応します。
公開済み情報だけを事実として扱いながら、仮説、勘違い、冗談、軽い脱線や仲間同士の掛け合いをLLMが生成します。
仲間の発言はゲーム状態や発見済み情報には反映されません。
直近の会話は現在の場面に自然につながる場合だけ参照し、過去の台詞をそのまま再利用しないよう指示しています。

---

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

---

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
