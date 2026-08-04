# Authoring Guide

Chat TTRPG GM MVP シナリオ作者向けガイド

***

# このガイドの目的

このシステムでは、

```text
ルールを書く
```

のではなく

```text
意味の例を書く
```

ことを重視します。

例えば、

NG

```python
if "助ける" in text:
```

OK

```json
"intent_examples": [
  "灯台守を助ける",
  "ユアンを救出する"
]
```

です。

作者の役割は、プレイヤーが言いそうな表現や手掛かりの意味をシナリオへ記述することです。

LLMサーバーやTable Turn生成温度などの実行設定は、シナリオ定義とは分離しています。`TABLE_TURN_TEMPERATURE`の既定値、優先順位、設定・比較・解除方法については、[READMEの「Table Turn生成温度」](../README.md#table-turn生成温度)を正本として参照してください。

***

# シナリオ全体構造

シナリオは1つの Markdown ファイルで記述します。

主な構成は以下です。

```text
opening
locations
npcs
objects
discoverables
goals
tests
```

`opening`では、必要に応じて開始地点から見た主要ロケーションの接続関係を案内できます。これは移動先を把握するための地理説明に限定し、重要な手掛かりの所在、推奨調査順、正解ルートなどの攻略情報は含めないでください。導入文はシナリオ開始時に一度だけ表示されます。

実行時は

```text
author_scenario_xxx.md
↓
md_to_scenario.py
↓
scenario.json
```

へ変換されます。

***

# Location の作り方

Location はプレイヤーが移動できる場所です。

例:

```json
{
  "id": "harbor",
  "name": "港",
  "intro": "小さな港。",
  "npcs": [
    "village_head"
  ],
  "visible_objects": [
    "tide_log"
  ],
  "exits": [
    "tavern",
    "warehouse"
  ]
}
```

重要項目:

```text
id
name
intro
visible_objects
npcs
exits
```

***

# NPC の作り方

NPC は

```text
どこにいるか
何を知っているか
何について話せるか
```

を分離して管理します。

例:

```json
{
  "id": "fisherman",
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

***

## location

NPC の現在地です。

```json
"location": "tavern"
```

***

## knows

NPC が知っている情報です。

```json
"knows": [
  "fisherman_blue_light"
]
```

***

## does\_not\_know

NPC が知らない情報です。

````json
"does_not_know": [
  "smuggler_route_analysis"
]
```【1-0a164b】

---

## topics

プレイヤーが何を聞いたのかを解決します。

```json
"topics": {
  "青い光": [
    "fisherman_blue_light"
  ]
}
````

***

# Object の作り方

オブジェクトは調査対象です。

例:

````json
{
  "id": "tide_log",
  "name": "潮汐表",
  "surface_text": "...",
  "banter_observation": "..."
}
```【1-0a164b】

---

# Discoverable の作り方

Discoverable は手掛かりです。

例:

```json
{
  "id": "fisherman_blue_light",

  "positive_examples": [
    "青い光",
    "昨夜の光",
    "岬の下"
  ],

  "public_text":
    "漁師バロは..."
}
```【1-0a164b】

---

## positive_examples

発見される話題例です。

良い例:

```json
[
  "青い光",
  "昨夜の光",
  "岬の下"
]
````

悪い例:

```json
[
  "聞く"
]
```

具体的な話題を書くことを推奨します。

***

## public\_text

プレイヤーへ公開される手掛かりです。

```json
"public_text": "..."
```

***

# 条件付き手掛かり

前提条件がある場合は

```json
"requires_all": [
  "head_report",
  "assistant_key_story"
]
```

を使用します。 

***

# Skill Check

技能判定が必要な場合

```json
"skill_check": {
  "skill": "investigation",
  "dice": "2d6",
  "difficulty": 9
}
```

を設定します。

## 汎用行動判定 (`action_checks`)

調査オブジェクトを対象にしない登攀、追跡、説得、隠密などは、トップレベルの
`action_checks` に定義します。`positive_examples` にプレイヤーが入力しそうな表現を、
`skill_check` に技能・ダイス・難易度を指定します。合計値が難易度と同じ場合も成功です。

```json
{
  "action_checks": [
    {
      "id": "climb_rocks",
      "required_location": "lower_cliff",
      "positive_examples": ["崖を登る", "岩を登る", "よじ登る"],
      "skill_check": {
        "skill": "survival",
        "dice": "2d6",
        "difficulty": 8
      },
      "check_prompt": "崖はぬかるみ、足場も不安定です。安全に登れるか、生存判定を行います。",
      "success_text": "崖の上へ登り切った。",
      "failure_text": "足場をつかめず、その場に留まった。",
      "success_effect": {"move_to": "upper_cliff"},
      "failure_effect": {"delay": true}
    }
  ]
}
```

`check_prompt` はダイス表示の直前に `GM:` の説明として表示されます。判定が必要な
理由や周囲の危険を、結果を先取りせずに記述してください。省略した場合は
「この行動が成功するか判定します。」という共通説明が表示されます。

標準技能キーは `investigation`、`survival`、`persuasion`、`athletics`、`stealth`
です。今回の汎用判定は移動 (`move_to`) と足止め (`delay`) を扱い、HP、負傷、毒などの
状態異常や戦闘処理は扱いません。

***

# Goal の作り方

Goal はシナリオの解決条件です。

例:

````json
{
  "id": "rescue_keeper",
  "target": "keeper"
}
```【1-0a164b】

---

## intent_examples

v2.15.0 から追加された項目です。

プレイヤーがゴール達成時に言いそうな文章を書きます。 【1-0a164b】

例:

```json
"intent_examples": [
  "灯台守を助ける",
  "灯台守を助けて",
  "ユアンを救出する",
  "ユアンを連れ戻す"
]
```【1-0a164b】

---

### 良い例

```json
[
  "ユアンを助ける",
  "灯台守を救出する",
  "港へ連れ戻す"
]
````

***

### 悪い例

```json
[
  "実行する",
  "解決する"
]
```

抽象的すぎる表現は避けてください。

***

# Solution Path

複数解決ルートを作れます。

例:

````json
{
  "id": "testimony_route",
  "requires_all": [
    "head_report",
    "fisherman_blue_light",
    "boy_cave_hint",
    "assistant_secret"
  ]
}
```【1-0a164b】

---

# テストの書き方

すべてのシナリオには tests を付けてください。

最低限必要なのは:

```text
成功系
失敗系
誤解釈系
````

です。 

***

# 作者チェックリスト

## Location

```text
□ exits が存在する
□ visible_objects が存在する
□ NPC配置が正しい
```

## NPC

```text
□ location がある
□ knows がある
□ topics がある
```

## Discoverable

```text
□ positive_examples がある
□ public_text がある
```

`public_text` は正式発見時にそのまま `GM:` 行として表示されます。プレイヤーへ単独で提示できる、空でない自然文にしてください。内部ID、著者メモ、GMへの命令、必要以上の正解ルート説明を含めないでください。

## Goal

```text
□ intent_examples がある
□ success_event がある
```

## Tests

```text
□ 成功系
□ 失敗系
□ 誤解釈系
```

***

# 設計思想

このシステムは

```text
アプリは意味を作らない
アプリは情報を整理する
意味と表現はLLMが担当する
```

という考え方で設計されています。

そのため作者も、

```text
細かいルールを書く
```

のではなく、

```text
意味の例を書く
```

ことを優先してください。
