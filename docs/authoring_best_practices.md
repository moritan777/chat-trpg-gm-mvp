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
