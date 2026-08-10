# Authoring Best Practices

Chat TTRPG GM MVP シナリオ作成の実践ガイドです。

この文書は仕様書ではなく、AIと壁打ちしながら良いシナリオを作るための経験則をまとめたものです。

---

## 1. 基本方針

このエンジンでは、固定ルールを増やすのではなく、シナリオ側に「意味の例」を書きます。

悪い方向:

```text
特定キーワードを見つけたら強制的に処理する
```

良い方向:

```text
プレイヤーが言いそうな自然文を examples として書く
```

例:

```json
"intent_examples": [
  "灯台守を助ける",
  "ユアンを救出する",
  "灯台守を港へ連れ戻す"
]
```

---

## 2. シナリオ規模の目安

最初に作るシナリオは、以下くらいが扱いやすいです。

```text
Location: 4〜8
NPC: 3〜6
Object: 5〜12
Discoverable: 8〜20
Goal: 1
Solution Path: 2〜3
Tests: 3〜5
```

大きくしすぎると、手掛かり条件と移動経路の検証が難しくなります。

---

## 3. Location のベストプラクティス

### 良い Location

```json
{
  "id": "tavern",
  "name": "酒場",
  "aliases": ["酒場", "宿屋"],
  "intro": "嵐明けの漁師たちが集まる酒場。",
  "npcs": ["fisherman"],
  "visible_objects": ["tavern_note"],
  "exits": ["harbor"]
}
```

### ポイント

- `id` は英数字とアンダースコアで安定させる
- `name` は表示用なので日本語でよい
- `aliases` はプレイヤーが言いそうな移動語を入れる
- `exits` は必ず双方向にする必要はないが、意図しない片道に注意する
- `npcs` と `visible_objects` は、その場にいるものだけを書く

### 悪い例

```json
"aliases": ["行く", "見る", "調べる"]
```

これは場所名ではなく動詞なので避けます。

---

## 4. NPC のベストプラクティス

NPCは以下を分けて書きます。

```text
どこにいるか
何を知っているか
何について話せるか
```

### 推奨テンプレート

```json
{
  "id": "fisherman",
  "name": "漁師バロ",
  "aliases": ["漁師", "バロ"],
  "location": "tavern",
  "availability": "available",
  "location_hint": "酒場にいるはずだ。",
  "knows": ["fisherman_blue_light"],
  "does_not_know": ["assistant_secret"],
  "topics": {
    "青い光": ["fisherman_blue_light"],
    "岬の下": ["fisherman_blue_light"]
  },
  "banter_observation": "漁師は昨夜の青い光を気にしている。"
}
```

### knows の書き方

`knows` は、そのNPCが実際に知っている discoverable ID を書きます。

良い例:

```json
"knows": ["fisherman_blue_light"]
```

悪い例:

```json
"knows": ["青い光のこと"]
```

`knows` には文章ではなく、discoverable の `id` を入れます。

### topics の書き方

`topics` は、プレイヤーが聞きそうな話題語と discoverable の対応です。

良い例:

```json
"topics": {
  "青い光": ["fisherman_blue_light"],
  "昨夜の光": ["fisherman_blue_light"],
  "岬の下": ["fisherman_blue_light"]
}
```

悪い例:

```json
"topics": {
  "聞く": ["fisherman_blue_light"],
  "話": ["fisherman_blue_light"]
}
```

「聞く」「話」などの汎用語は、誤認識を増やします。

---

## 5. Object のベストプラクティス

Object は、プレイヤーが調べる対象です。

### 推奨テンプレート

```json
{
  "id": "broken_lantern",
  "name": "割れたランタン",
  "aliases": ["ランタン", "割れたランタン"],
  "surface_text": "崖道に割れたランタンが落ちている。",
  "surface_banter_observation": "割れたランタンとガラス片が崖道に散っている。",
  "banter_observation": "ガラス片は灯台ではなく海岸側へ散っている。"
}
```

### surface_text と banter_observation

`surface_text` は常に見えてよい表面情報です。

`banter_observation` は、発見後に仲間が反応してよい情報にします。

未発見の核心情報を `surface_text` に入れないでください。

---

## 6. Discoverable のベストプラクティス

Discoverable は「プレイヤーが得る手掛かり」です。

### 推奨テンプレート

```json
{
  "id": "fisherman_blue_light",
  "source": {
    "type": "npc",
    "id": "fisherman"
  },
  "positive_examples": [
    "青い光",
    "昨夜の光",
    "岬の下"
  ],
  "negative_examples": [],
  "public_text": "漁師バロは、昨夜の灯台消灯直後、岬の下で低い青い光を見たと証言した。",
  "grants_modifier": {
    "investigation": 1
  }
}
```

### positive_examples の数

目安:

```text
3〜6個
```

良い例:

```json
[
  "青い光",
  "昨夜の光",
  "岬の下"
]
```

悪い例:

```json
[
  "聞く",
  "調べる",
  "見る"
]
```

動詞だけではなく、話題や対象を入れます。

---

## 7. 条件付き Discoverable の書き方

手掛かりの順序を制御したい場合は、`requires_all` または `requires_any` を使います。

### requires_all

```json
"requires_all": [
  "broken_lantern_clue"
]
```

すべての前提が必要です。

### requires_any

```json
"requires_any": [
  "head_report",
  "blood_drag_clue"
]
```

どれか一つあれば開示可能です。

### 注意

条件は discoverable 側に置くのが基本です。

```text
NPCが警戒して話さない
```

という表現も、まずは対象 discoverable に `requires_all` や `requires_any` を置いて表現します。

---

## 8. Goal Intent Examples のベストプラクティス

Goal には `intent_examples` を書きます。

これは、プレイヤーがゴール達成時に言いそうな自然文です。

### 推奨数

```text
5〜10個
```

### 良い例

```json
"intent_examples": [
  "灯台守を助ける",
  "灯台守を助けて",
  "ユアンを救出する",
  "灯台守を港へ連れ戻す",
  "洞窟の奥のユアンを救う"
]
```

### 悪い例

```json
"intent_examples": [
  "助ける",
  "救出",
  "解決",
  "実行",
  "やる"
]
```

短すぎる語や抽象語は避けます。

### 書き方のコツ

以下を混ぜます。

```text
対象名 + 動作
固有名 + 動作
場所 + 対象 + 動作
言い切り形
依頼形
```

例:

```json
[
  "灯台守を助ける",
  "灯台守を助けて",
  "ユアンを救出する",
  "洞窟の奥のユアンを救う",
  "灯台守を港へ連れ戻す"
]
```

---

## 9. Solution Path のベストプラクティス

複数解決ルートを作る場合は、各ルートの必要 discoverable を分けます。

```json
{
  "id": "testimony_route",
  "requires_all": [
    "head_report",
    "fisherman_blue_light",
    "boy_cave_hint"
  ],
  "success_event": {
    "text": "証言をつなぎ合わせると、真相が見えてきます。"
  }
}
```

推奨:

```text
2〜3ルート
1ルートあたり 3〜6 discoverable
```

---

## 10. Tests のベストプラクティス

最低限、以下を用意します。

```text
成功系
失敗系
誤解釈系
```

### 成功系

```json
"testimony_success": {
  "commands": [
    "村長に灯台守のことを聞く",
    "酒場へ行く",
    "漁師に青い光のことを聞く",
    "灯台守を助けて"
  ],
  "expect": [
    "セッション終了。"
  ]
}
```

### 誤解釈系

```json
"topic_resolution": {
  "commands": [
    "村長に青い光のことを聞く",
    "酒場へ行く",
    "漁師に青い光のことを聞く"
  ],
  "expect_not": [
    "港の倉庫で人影を見た"
  ]
}
```

誤解釈系テストはとても重要です。

---

## 11. AIと壁打ちする時の指示例

```text
以下の仕様に従って、Chat TTRPG GM MVP 用の短編シナリオを作ってください。

条件:
- Location 5個
- NPC 4人
- Object 8個
- Discoverable 12個前後
- Goal 1個
- Solution Path 2個
- Tests 3個以上

重要:
- NPCには location, knows, topics を必ず書く
- Goalには intent_examples を必ず書く
- discoverableには positive_examples と public_text を必ず書く
- 固定キーワードルールは書かない
- 出力は author_scenario_xxx.md 形式
```

---

## 12. 最終チェックリスト

### Location

```text
□ id が一意
□ exits が存在する location を指す
□ visible_objects が存在する object を指す
□ npcs が存在する npc を指す
```

### NPC

```text
□ location がある
□ availability がある
□ knows が discoverable ID を指す
□ topics が discoverable ID を指す
□ topics が汎用語だけになっていない
```

### Object

```text
□ aliases がある
□ surface_text がある
□ banter_observation に未発見核心を入れすぎていない
```

### Discoverable

```text
□ positive_examples が3個以上ある
□ public_text がある
□ source が存在する
□ requires_all / requires_any が存在する discoverable を指す
```

### Goal

```text
□ target が存在する
□ intent_examples が5個以上ある
□ solution_paths がある
□ success_event がある
```

### Tests

```text
□ 成功系がある
□ 失敗系がある
□ 誤解釈系がある
□ run_authoring_pipeline.py が通る
```

---

## 13. 自然言語導線・知識境界の機械的設計規則

### NPC topics

- `topics` は「何について聞いたか」を、そのNPCが公開可能な discoverable へ解決する対応表です。
- topicが参照するIDは `knows` に含め、`does_not_know` には絶対に含めません。
- NPC由来discoverableの `source.id` と、そのtopicを所有するNPCを一致させます。
- 導入・場所説明で公開した人物名と、人物の `name` / `aliases` を質問語彙として監査します。役職名と固有名が同一人物なら、代表的な自然質問が同じ意図へ到達するようにします。
- 人物名だけで複数の重要情報を無条件公開しません。取得条件は discoverable の `requires_all` / `requires_any` に残し、topicで迂回させません。
- `昨夜`、`事件`、`話`、`何か`のような広い語は複数情報への誤発火を招くため避けます。

### positive_examples

`positive_examples` はテスト専用コマンドではなく、自然な入力の代表例です。lexical fallback は形態素解析や同義語展開を行わず、`example in player_input` の文字列部分一致だけで判定します。したがって、Embeddingがなければ成立しない主要導線を作らないでください。

良い例:

```json
"positive_examples": [
  "灯台守のこと",
  "ユアンについて",
  "灯台守ユアンについて",
  "灯台が消えた時のこと"
]
```

悪い例:

```json
"positive_examples": ["話", "昨夜", "事件"]
```

導入で公開した主要語、関連する `name` / `aliases`、代表的な助詞違いを検討します。一方、短すぎる一般語は避け、同じ語が無関係な複数discoverableへ競合しないか確認します。似ているが別情報を指す語には `negative_examples` を検討します。

### NPC presence

NPCへ質問できるのは、NPCが現在地に存在する場合だけです。authored topicが一致してもpresence guardは迂回しません。不在なら `npc_absent` です。`hidden` / `missing` / `unavailable` のNPCは公開条件を満たすまで会話対象にせず、`location_hint` は不在案内にだけ使い、存在判定を上書きしません。

### 最低限必要なシナリオテスト

- 各 `solution_paths` の正規成功ルートを1件以上。
- 同一人物の固有名と役職名による質問。
- `does_not_know` の情報を別NPCから取得できない知識境界。
- 不在NPCへの質問が `npc_absent` になること。
- `requires_all` / `requires_any` の前提不足で公開されないこと。
- 既発見情報の再質問で二重発見・二重modifier付与されないこと。
- `EMBEDDING_PROVIDER=none` でも、導入で明示した主要固有名・役職・物体名による主要ルートが成立すること。

接続テストは通常1入力ですが、ゲーム中の類似度判定はqueryと複数exampleを一括送信します。接続テスト成功だけでゲーム中の複数入力Embedding成功は保証されません。

## シナリオ生成後の自己監査

- [ ] 導入で公開した固有名詞を一覧化した
- [ ] 各固有名詞がname、aliases、topics、positive_examplesのどこで使われるか確認した
- [ ] 各NPCのtopicsがknowsの範囲内にある
- [ ] does_not_knowとtopicsが矛盾していない
- [ ] 各必須discoverableに自然な取得入力がある
- [ ] 各solution pathを自然な入力だけで完走できる
- [ ] NPC不在時にtopic resolverが発火しない
- [ ] Embeddingなしでも正規入力で主要ルートを完走できる
- [ ] 抽象的すぎるtopicやpositive exampleを登録していない
- [ ] 正本Markdownから派生JSONとテストを再生成した
- [ ] 派生JSONを直接編集していない
- [ ] 正本とWeb版JSONの同期テストが成功した
