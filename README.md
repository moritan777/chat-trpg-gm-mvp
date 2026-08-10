# Chat TTRPG GM MVP

## ローカルWeb UI

Python版をゲームルール、セッション状態、情報境界、LLM/Embedding判定の**唯一の正本**と
します。Web UIは同じプロセスのFastAPIを操作する薄いフロントエンドであり、ゲーム処理を
JavaScriptへ移植していません。CLIとWeb APIはどちらも`GameSession`を通じて既存の`Game`、
`State`、`judge`、`resolve`、`render_table_turn`を使用します。

以前のVite/TypeScript製静的プレビューとGitHub Pages公開構成は廃止しました。現在のWeb UIは
ローカルPython APIと同一originから配信され、llama.cppへ直接接続しません。Node.js、npm、
ブラウザから外部APIへ直接接続する構成は不要です。

Web画面にはPython側の接続設定フォームがありますが、これは同一originの`/api/*`へ保存・
接続テストを依頼するだけです。ブラウザからllama.cppへ直接接続するものではありません。

### 必要環境とインストール

Python 3.10以降を使用してください。Web用の依存関係はFastAPIとUvicornです。`httpx`はAPIの
自動テストに使用します。

```bash
python -m pip install -r requirements-web.txt
```

Windows PowerShellでも同じコマンドを使用できます。

### LLM / EmbeddingとWeb APIの起動

Chat用llama.cppとEmbedding用サーバーは、下記「LLM / Embedding 設定」の既存環境変数と
各サーバーのインストール済みバージョンのヘルプに従って、Web APIより先に起動してください。
Web専用の接続設定はなく、CLIと同じ`LLAMA_CPP_BASE_URL`、`EMBEDDING_BASE_URL`等を使用します。

```bash
python web_api.py
```

ブラウザで <http://127.0.0.1:8000> を開きます。Windowsでは`start_web.bat`でもブラウザと
APIを起動できます。Uvicornを直接使用する場合は次のとおりです。

```bash
python -m uvicorn web_api:app --host 127.0.0.1 --port 8000
```

セッションはPythonプロセスのメモリ内だけに保存され、データベースやブラウザStorageには
保存されません。API停止・再起動時には全セッションが失われます。このサーバーは認証、TLS、
永続化を備えた外部公開用サーバーではありません。`127.0.0.1`でのローカル利用を前提とし、
インターネットへ公開しないでください。

### 初回設定

初回起動時は画面上部の「接続設定」が自動的に開き、短い手順案内を表示します。シナリオ、
Chat、Embeddingを確認し、接続テスト、設定保存、ゲーム開始の順に進みます。一度一般設定を
保存すると、次回からは詳細を折りたたみ、「現在の設定」の要約を優先して表示します。
「接続設定を開く」または「接続設定を閉じる」で任意に開閉でき、開閉状態をブラウザへ保存しません。

* **シナリオ:** プレイする作者シナリオ。前回保存した選択を復元します。
* **Chat Provider:** `llama_cpp`（ローカル）、`openai_compatible`（外部のOpenAI互換
  `/chat/completions`）、`none`（LLMを使用しない）から選べます。
* **Chat Base URL:** 既定値は`http://127.0.0.1:8080/v1`です。
* **Chat Model:** Chatサーバーへ送るOpenAI互換APIのモデル名。既定値は`local-model`です。
* **Embedding Base URL:** 既定値は`http://127.0.0.1:8081/v1`です。
* **Embedding Model:** Embeddingサーバーへ送るモデル名。既定値は`local-embedding`です。
* **API Key:** API提供者が要求する場合だけ入力します。通常のローカルllama.cppでは空欄で
  構いません。Chat用とEmbedding用は別々です。

要約には、選択シナリオ、Chat/Embeddingのホストとポート、Model、APIキー設定状態、一般設定の
保存状態を表示します。接続状態はページを開くたびに**未確認**から始まり、現在の設定に対する
テスト成功後は**接続成功**、失敗後は**接続失敗**になります。色だけでなく状態名も表示します。
URL、Model、APIキーを編集すると、そのサービスは未確認へ戻ります。接続成功状態はJSONや
ブラウザStorageへ保存しないため、以前の成功を現在の接続成功として誤表示しません。

詳細欄の技術的な設定元は確認可能ですが、要約では「環境変数」「設定ファイル」「既定値」に
簡略化します。`environment:`などの内部表記は一般表示へそのまま出しません。

APIキー欄は「APIキーを使用する」をオンにした場合だけ表示します。チェックを外して保存しても、
すでにPythonメモリへ設定されたキーは意図せず削除されません。削除する場合は確認付きの
「APIキーを削除」を使用します。APIキーの実値は画面へ復元されません。

外部OpenAI互換APIでは、利用者が契約しているサービスのBase URL、Model、必要ならAPI Keyを
入力します。特定サービスやモデルの対応を保証するものではありません。接続テスト成功が示すのは
API形式と認証を利用できたことだけで、ゲーム中の会話品質、情報境界、出力形式、指示追従は使用
モデルに依存します。料金は利用者の契約に基づき利用者負担で発生する場合があります。APIキーは
`settings.json`へ保存せずPythonプロセスのメモリだけに置き、プロセス終了時に失われます。
Authorizationヘッダーは指定したChat Base URLへのPython側リクエストにだけ付与され、ブラウザは
外部APIへ接続しません。ChatとEmbeddingのURL、Model、API Keyは独立しているため、たとえば外部
OpenAI互換Chatと`http://127.0.0.1:8081/v1`のローカルEmbeddingを併用できます。

> **更新後の再起動:** Pythonは起動時にProviderの許可値を読み込みます。コード更新前から
> `web_api.py`を起動したままの場合、画面だけが更新されて保存時に
> 「Chat Providerはllama_cppまたはnone」と表示されることがあります。Webサーバーを一度停止し、
> 更新後のコードで起動し直してください。画面はAPIが対応Provider一覧を返さない場合にも再起動を
> 案内し、未対応の外部Providerを選択できないようにします。

「Chat接続テスト」と「Embedding接続テスト」は、画面にある未保存の値をPython APIへ送り、
短いリクエストで確認します。ゲームセッションや履歴は作成・変更しません。接続テストは推奨ですが、
保存済み設定または初期設定があれば省略して開始できます。`LLM_PROVIDER=none`を使う既存CLI・
テスト経路にも接続テストは要求しません。

設定を保存した後の変更は、すでに進行中のゲームへは適用されず、次に開始するゲームから有効です。
「新しいゲーム」で設定欄を再び有効にできます。「初期設定へ戻す」は保存ファイルとメモリ上の
APIキーを削除し、「APIキーを削除」は一般設定を残したままメモリ上のキーだけを削除します。
ゲーム開始時は詳細設定を自動的に閉じ、ゲーム画面へ移動してプレイヤー入力欄へフォーカスします。
会話履歴は独立したスクロール領域です。最新位置から120px以内ならターン追加後も追従しますが、
過去ログを閲覧中は位置を動かしません。その場合は「新しいメッセージがあります」ボタンを表示し、
押すと最新位置へ移動します。手動で下端付近へ戻った場合や新しいゲームでは通知が消えます。
進行中も要約は確認できますが、詳細設定の入力と操作は無効です。接続失敗中はゲームを開始せず、
設定確認へ戻します。保存済み設定の接続状態が未確認の場合は、警告を表示しつつ開始できます。

### 設定ファイルと優先順位

一般設定はUTF-8 JSONとして保存します。Windowsでは
`%LOCALAPPDATA%\ChatTtrpgGm\settings.json`、その他のOSでは`$XDG_CONFIG_HOME/chat-ttrpg-gm/settings.json`
または`~/.config/chat-ttrpg-gm/settings.json`です。実際のパスは画面に表示されます。

```json
{
  "settings_version": 1,
  "selected_scenario": "lighthouse",
  "chat": {
    "provider": "llama_cpp",
    "base_url": "http://127.0.0.1:8080/v1",
    "model": "local-model"
  },
  "embedding": {
    "base_url": "http://127.0.0.1:8081/v1",
    "model": "local-embedding"
  }
}
```

APIキーはこのJSONへ保存しません。Pythonプロセスのメモリだけに保持するため、API停止時に
失われます。ブラウザへキーを再表示せず、設定済みかどうかだけを表示します。OS資格情報ストアは
今回使用していません。空欄で一般設定だけを更新した場合はメモリ上の既存キーを維持し、削除は
専用の「APIキーを削除」操作で行います。設定ファイルが破損している場合は内容を画面へ出さず初期設定へ戻り、警告を
表示します。未知の項目は無視し、保存時には既知の項目だけを書き込みます。保存済みシナリオが
削除されていれば先頭の利用可能なシナリオを一時選択し、ファイルを無断更新せず警告します。

適用優先順位は次のとおりです。

1. 既存CLIの明示引数（ダイス値、debug等）
2. 既存の環境変数
3. WebからPythonプロセスへ渡したメモリ上のAPIキー
4. `settings.json`
5. 既存Pythonエンジンの既定値

Chat URLは`LLAMA_CPP_BASE_URL`、`LLM_BASE_URL`、`OPENAI_BASE_URL`の順、Chat Modelは
`LLAMA_CPP_MODEL`、`LLM_MODEL`、`OPENAI_MODEL`の順です。Embedding URLは
`EMBEDDING_BASE_URL`、`EMB_BASE_URL`の順、Modelは`EMBEDDING_MODEL`、`EMB_MODEL`の順です。
`TABLE_TURN_TEMPERATURE`（旧互換`GM_LINE_REWRITE_TEMPERATURE`）と`DISCOVERY_DISPLAY`も既存の
環境変数を優先します。各項目の現在値と設定元は設定画面に表示されるため、保存値が環境変数で
上書きされている場合も確認できます。既存実装にはAPIキー用環境変数がなかったため、新しい
APIキー環境変数名は追加していません。

`start_web.bat`は依存関係を確認してAPIとブラウザを起動するランチャー専用です。URL、モデル、
シナリオ、APIキーを保持・変更したり、llama.cppを自動起動・終了したりしません。

### Web/APIテスト

macOS/Linux:

```bash
LLM_PROVIDER=none EMBEDDING_PROVIDER=none python -m unittest discover -s tests -p "test*.py"
```

Windows PowerShell:

```powershell
$env:LLM_PROVIDER="none"
$env:EMBEDDING_PROVIDER="none"
python -m unittest discover -s tests -p "test*.py"
```

APIは`GET /api/health`、`GET /api/scenarios`、セッション作成・取得・コマンド送信・削除を
提供します。レスポンスは現在地、終了状態、公開表示行だけを返し、発見済みID集合などの内部状態、
シナリオの未公開情報、環境変数、APIキーを返しません。

現行版: **v2.30.0 明示的な仲間ルーティング** (`v2.30.0 [explicit-companion-routing]`)

バージョンの正本は `fixed_truth_ai_gm_mvp.py` の `VERSION` です。起動せずに
`python fixed_truth_ai_gm_mvp.py --version` で確認できます。README の現行版表記と
モジュール先頭の版表記も、リリース時にこの値へ揃えます。シナリオにはエンジンとは
独立した作者版があり、サンプルでは本文見出し、`scenario_revision`、
`meta.authoring_revision` を同時に更新します。

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
* クロ（ホラ吹き）とガラン（行動派）を含む4人の仲間アーキタイプ
* Embeddingによる行動判定
* オブジェクトに依存しない汎用技能判定と成功・失敗効果
* 判定結果の5段階ランク（`CriticalSuccess` / `Success` / `PartialSuccess` / `Failure` / `CriticalFailure`）
* 出目、技能・手掛かり補正、最終値、結果ランクを順に伝えるGMダイス演出
* 判定イベントに任意のランク別結果（`on_critical_success` / `on_success` / `on_partial_success` / `on_failure` / `on_critical_failure`）を定義可能
* ランク別結果が未定義の場合は、既存互換のため大成功は成功、部分成功・大失敗は失敗として扱う
* 既存ルートで処理できない自由行動を標準技能へ推定し、5段階の技能判定として解決
* 自由行動の内容・使用技能・判定ランクをGM生成コンテキストへ渡し、判定結果を世界描写へ接続

---

## 仲間キャラクター設計方針

仲間キャラクターは、特定の役割や決まった反応ではなく、何に最初に関心を向けるかという**認知軸**で差別化します。これにより個性を保ちながら、場面に応じて幅広い発言ができるようにします。

* **クロ:** 面白さ・騒ぎ・ホラ話
* **ガラン:** 行動・実行
* **ニコ:** 小さな要素からの妙な連想・話題拡散
* **ピピ:** 人への関心・気遣い

新しい仲間を追加するときも、固定的な「担当」を割り当てるのではなく、**キャラは役割ではなく認知軸で差別化する**ことを設計指針とします。

### 会話連鎖の観測

`--debug-llm`または`--debug-all`を指定すると、仲間の各発言について`[COMPANION_DIAGNOSTICS]`を表示します。これは生成済みの発言を簡易分類する観測機能であり、発言内容や発言機会を変更するものではありません。

* `Character`: 発言者
* `Trigger`: 通常の場面反応か、明示的な会話継続か
* `RespondedTo`: 名前への言及、または継続発言の反応表現から推定した反応先
* `Focus`: 発言内の語から簡易分類した関心対象

セッション終了時には`[CONVERSATION_STATS]`として、仲間発言数、直接反応数、会話連鎖率、テーマ維持率、繰り返し参照されたテーマ、キャラクター別の反応先を集計します。反応先とテーマは軽量な文字列ヒューリスティックによる観測値であり、意味解析による厳密な判定ではありません。

さらに、`[FOCUS_STATS]`でキャラクター別の関心分類、`[TOPIC_ORIGIN]`でテーマを最初に発言したキャラクター、`[TOPIC_SURVIVAL]`でテーマの作成・最終参照ターンと寿命、`[CHARACTER_INFLUENCE]`でテーマ作成数と継続テーマへの参加回数を表示します。`TopicsSurvived`は、そのキャラクター自身が作ったテーマ数ではなく、複数ターンに残ったテーマを作成後のターンで参照した回数です。

`TopicBranchRate`は、比較可能な隣接ターンのうち、前ターンのテーマを一つ以上維持しながら新しいテーマも加えたターンの割合です。`[TOPIC_BRANCH]`には`既存テーマ -> 新規テーマ`の遷移を最大20件表示します。共通テーマがなく全面的に切り替わったターンは内部の`TopicJumpCount`として別集計し、派生には含めません。`[NICO_DIAGNOSTICS]`では、ニコが新規テーマを加えた派生回数と、ニコが発言したユニークテーマ数・一覧を確認できます。

明示的な会話継続は同じ場所で最大5ターンまで`conversation_context.mode=continue`を送信します。6回目の継続要求ではモードを期限切れにし、新しい話題へ移れる通常入力として扱います。場所が変わった場合も継続モードだけを解除しますが、仲間の内部会話履歴、テーマ履歴、Conversation Statsは削除しません。期限切れ時の`LastTopics`には直近の仲間履歴から抽出した話題を最大3件表示します。デバッグ集計には`ContinueWindow`と、場所変更・期限切れの合計である`ConversationResets`も表示します。

各発言の正規化した話題は`[COMPANION_TOPIC]`として表示し、セッション末尾では`CharacterTopic=<キャラクター> Topic=<話題> Count=<回数>`形式で集計します。これにより、仲間ごとの発言が特定テーマへ偏っていないかを確認できます。

会話連鎖を観測するときは、1行1コマンドのUTF-8テキストを作成して`--script`へ指定します。
リポジトリには旧来の手動観測用`story_*.txt`を同梱していません。再現可能な自動確認は
`tests/test_companion_banter.py`を使用してください。シナリオ内の作者テスト用入力は、
`md_to_scenario.py`が出力先へ生成する`sample_inputs_<テスト名>.txt`を利用できます。

```powershell
python .\fixed_truth_ai_gm_mvp.py `
  --scenario-dir .\scenario_lighthouse `
  --script .\scenario_lighthouse\sample_inputs_topic_resolution.txt `
  --debug-llm
```

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
  --scenario-dir .\scenario_lighthouse `
  --script .\scenario_lighthouse\sample_inputs_topic_resolution.txt `
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
  --scenario-dir .\scenario_lighthouse `
  --script .\scenario_lighthouse\sample_inputs_topic_resolution.txt `
  --dice-total 3 `
  --debug-judge `
  --debug-llm

$env:TABLE_TURN_TEMPERATURE="0.9"
# 同じpythonコマンドを複数回実行

$env:TABLE_TURN_TEMPERATURE="1.0"
# 同じpythonコマンドを複数回実行
```

同じシナリオ、スクリプト、`dice-total`を使い、他の生成設定を同時に変えないでください。`--debug-llm`の`[TABLE_TURN_TEMPERATURE]`で実際の値を確認します。人間による定性的確認として、仲間行数、発言者順、ニコ・ピピ・クロ・ガランの登場回数、仲間への働きかけ、短い応答、Canonical外情報、内容の薄い短文、正式発見の表示を観察します。

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

引数とオプション:

| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `--version` | エンジンのバージョンを表示して終了 | - |
| `--scenario-dir DIR` | `scenario.json`を含むディレクトリ | `scenario_lighthouse` |
| `--script PATH` | 1行1コマンドのUTF-8入力。省略時は対話プレイ | 対話入力 |
| `--debug-judge` | 行動判定のデバッグ出力を有効化 | 無効 |
| `--debug-llm` | LLM・仲間会話のデバッグ出力を有効化 | 無効 |
| `--debug-embedding` | Embeddingのデバッグ出力を有効化 | 無効 |
| `--debug-all` | 上記すべてのデバッグ出力を有効化 | 無効 |
| `--dice-total N` | シナリオ判定の合計値を固定 | ランダム |
| `--skill-dice-total N` | 汎用技能判定の出目を固定 | ランダム |
| `--dice-seed N` | 乱数生成器のシードを固定 | システム乱数 |

`--dice-total`と`--skill-dice-total`はテスト・再現確認用です。通常プレイでは省略してください。

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
