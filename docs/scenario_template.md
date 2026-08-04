\# Scenario Template



Chat TTRPG GM MVP シナリオテンプレート



このページは、新しいシナリオを作る際の最小構成テンプレートです。



\---



\# 最小構成



```json

{

&#x20; "title": "シナリオ名",



&#x20; "opening\_scene": "village",



&#x20; "opening": \[

&#x20;   "GM: 物語導入"

&#x20; ],



&#x20; "player": {

&#x20;   "skills": {

&#x20;     "investigation": 2,

&#x20;     "survival": 1,

&#x20;     "persuasion": 1,

&#x20;     "athletics": 1,

&#x20;     "stealth": 1

&#x20;   }

&#x20; },



&#x20; "locations": \[],

&#x20; "npcs": \[],

&#x20; "objects": \[],

&#x20; "discoverables": \[],

&#x20; "action\_checks": \[],

&#x20; "goals": \[],

&#x20; "tests": {}

}

```



\---



\# 1. Location



プレイヤーが移動できる場所です。



```json

{

&#x20; "id": "village",



&#x20; "name": "村",



&#x20; "aliases": \[

&#x20;   "村"

&#x20; ],



&#x20; "intro": "小さな村。",



&#x20; "npcs": \[

&#x20;   "village\_head"

&#x20; ],



&#x20; "visible\_objects": \[

&#x20;   "notice\_board"

&#x20; ],



&#x20; "exits": \[

&#x20;   "forest"

&#x20; ]

}

```



\## 項目



\### id



内部ID



```json

"id": "village"

```



一意であること。



\---



\### name



表示名



```json

"name": "村"

```



\---



\### aliases



移動時に認識する別名



```json

"aliases": \[

&#x20; "村",

&#x20; "村へ"

]

```



\---



\### intro



到着時の説明



```json

"intro": "小さな村。"

```



\---



\### npcs



配置NPC



```json

"npcs": \[

&#x20; "village\_head"

]

```



\---



\### visible\_objects



見えるオブジェクト



```json

"visible\_objects": \[

&#x20; "notice\_board"

]

```



\---



\### exits



移動可能先



```json

"exits": \[

&#x20; "forest"

]

```



\---



\# 2. NPC



NPC は



```text

どこにいる

何を知っている

何について話せる

```



を分離して管理します。



```json

{

&#x20; "id": "village\_head",



&#x20; "name": "村長",



&#x20; "aliases": \[

&#x20;   "村長"

&#x20; ],



&#x20; "location": "village",



&#x20; "availability": "available",



&#x20; "knows": \[

&#x20;   "wolf\_rumor"

&#x20; ],



&#x20; "does\_not\_know": \[],



&#x20; "topics": {

&#x20;   "狼": \[

&#x20;     "wolf\_rumor"

&#x20;   ]

&#x20; }

}

```



\---



\## location



現在地



```json

"location": "village"

```



\---



\## availability



出現状態



```json

"available"

```



通常状態



```json

"hidden"

```



隠し状態



```json

"missing"

```



行方不明状態



\---



\## knows



知っている情報



```json

"knows": \[

&#x20; "wolf\_rumor"

]

```



\---



\## topics



話題と discoverable の対応



```json

"topics": {

&#x20; "狼": \[

&#x20;   "wolf\_rumor"

&#x20; ]

}

```



\---



\# 3. Object



調査対象です。



```json

{

&#x20; "id": "notice\_board",



&#x20; "name": "掲示板",



&#x20; "aliases": \[

&#x20;   "掲示板"

&#x20; ],



&#x20; "surface\_text": "張り紙が貼られている。"

}

```



\---



\# 4. Discoverable



手掛かりです。



```json

{

&#x20; "id": "wolf\_rumor",



&#x20; "source": {

&#x20;   "type": "npc",

&#x20;   "id": "village\_head"

&#x20; },



&#x20; "positive\_examples": \[

&#x20;   "狼",

&#x20;   "森"

&#x20; ],



&#x20; "public\_text":

&#x20;   "最近森で狼が目撃されている。"

}

```



\---



\## positive\_examples



発見トリガーになる意味例



良い例



```json

\[

&#x20; "狼",

&#x20; "森",

&#x20; "夜の遠吠え"

]

```



悪い例



```json

\[

&#x20; "聞く"

]

```



\---



\## public\_text



公開される内容



```json

"public\_text":

&#x20; "最近森で狼が目撃されている。"

```



\---



\# 5. 条件付き Discoverable



前提条件を付けられます。



```json

{

&#x20; "requires\_all": \[

&#x20;   "clue\_a",

&#x20;   "clue\_b"

&#x20; ]

}

```



\---



\## requires\_all



全て必要



```json

"requires\_all": \[

&#x20; "clue\_a",

&#x20; "clue\_b"

]

```



\---



\## requires\_any



どれか一つ必要



```json

"requires\_any": \[

&#x20; "clue\_a",

&#x20; "clue\_b"

]

```



\---



\# 6. Skill Check



判定付き情報



```json

{

&#x20; "skill\_check": {

&#x20;   "skill": "investigation",

&#x20;   "dice": "2d6",

&#x20;   "difficulty": 9

&#x20; }

}

```



\---



\# 7. Goal



シナリオ解決条件です。



```json

{

&#x20; "id": "rescue\_child",



&#x20; "target": "child",



&#x20; "intent\_examples": \[

&#x20;   "子供を助ける",

&#x20;   "救出する"

&#x20; ]

}

```



\---



\## target



解決対象



```json

"target": "child"

```



\---



\## intent\_examples



プレイヤーが言いそうな文章



```json

"intent\_examples": \[

&#x20; "子供を助ける",

&#x20; "救出する",

&#x20; "連れ戻す"

]

```



\### 良い例



```json

\[

&#x20; "ユアンを助ける",

&#x20; "灯台守を救出する",

&#x20; "港へ連れ戻す"

]

```



\### 悪い例



```json

\[

&#x20; "実行する",

&#x20; "解決する"

]

```



抽象的すぎる文章は避ける。



\---



\# 8. Solution Path



複数解決ルート



```json

{

&#x20; "id": "talk\_route",



&#x20; "requires\_all": \[

&#x20;   "clue\_a",

&#x20;   "clue\_b"

&#x20; ],



&#x20; "success\_event": {

&#x20;   "text": "真相へたどり着いた。"

&#x20; }

}

```



\---



\# 9. Goal Check



最終判定



```json

"check": {

&#x20; "skill": "investigation",

&#x20; "dice": "2d6",

&#x20; "difficulty": 10

}

```



\---



\# 10. Tests



必ずテストを書くことを推奨します。



```json

"tests": {

&#x20; "success": {



&#x20;   "commands": \[

&#x20;     "村長に聞く",

&#x20;     "森へ行く",

&#x20;     "子供を助ける"

&#x20;   ],



&#x20;   "expect": \[

&#x20;     "セッション終了"

&#x20;   ]

&#x20; }

}

```



\---



\# 最低限のチェックリスト



\## Location



```text

□ exits が存在する

□ visible\_objects が存在する

□ NPC配置が正しい

```



\## NPC



```text

□ location がある

□ knows がある

□ topics がある

```



\## Object



```text

□ aliases がある

□ surface\_text がある

```



\## Discoverable



```text

□ positive\_examples がある

□ public\_text がある

```



\## Goal



```text

□ target がある

□ intent\_examples がある

□ success\_event がある

```



\## Tests



```text

□ 成功系

□ 失敗系

□ 誤解釈系

```



\---



\# おすすめ作業順



```text

Location

↓

NPC

↓

Object

↓

Discoverable

↓

Goal

↓

Tests

↓

run\_authoring\_pipeline.py

↓

手動プレイ

```



\---



\# 設計思想



```text

アプリは意味を作らない

アプリは情報を整理する

意味と表現はLLMが担当する

```



作者はルールを書くのではなく、



```text

プレイヤーが言いそうな言葉

NPCが知っていること

探索で分かること

```



をシナリオへ記述してください。

``

