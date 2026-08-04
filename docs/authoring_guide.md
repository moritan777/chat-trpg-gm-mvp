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

判定結果の5段階ランクをシナリオに反映したい場合は、判定イベントに任意で
`on_critical_success`、`on_success`、`on_partial_success`、`on_failure`、
`on_critical_failure` を追加できます。各項目には `text` と `effect` を指定できます。
未指定のランクは既存互換のため、`CriticalSuccess` は通常成功、`PartialSuccess` と
`CriticalFailure` は通常失敗の `text` / `effect` にフォールバックします。

```json
{
  "id": "read_weathered_sign",
  "required_location": "old_road",
  "positive_examples": ["古い標識を読む", "標識を調べる"],
  "skill_check": {
    "skill": "investigation",
    "dice": "2d6",
    "difficulty": 8
  },
  "on_critical_success": {
    "text": "標識の文字だけでなく、裏面の小さな刻印にも気づいた。",
    "effect": {"event": {"type": "rank_outcome", "rank": "CriticalSuccess"}}
  },
  "on_success": {
    "text": "標識の文字を読み取った。",
    "effect": {"event": {"type": "rank_outcome", "rank": "Success"}}
  },
  "on_partial_success": {
    "text": "標識の文字を一部だけ読み取った。",
    "effect": {"event": {"type": "rank_outcome", "rank": "PartialSuccess"}}
  },
  "on_failure": {
    "text": "標識の文字は読み取れなかった。",
    "effect": {"event": {"type": "rank_outcome", "rank": "Failure"}}
  },
  "on_critical_failure": {
    "text": "標識を読み違え、誤った方角に確信を持ってしまった。",
    "effect": {"event": {"type": "rank_outcome", "rank": "CriticalFailure"}}
  }
}
```

標準技能キーは `investigation`、`survival`、`persuasion`、`athletics`、`stealth`
です。今回の汎用判定は移動 (`move_to`) と足止め (`delay`) を扱い、HP、負傷、毒などの
状態異常や戦闘処理は扱いません。

## 自由行動判定

プレイヤーがシナリオ定義済みの移動・調査・聞き込み・`action_checks` に該当しない
自由行動を入力した場合、エンジンは入力文から標準技能を推定し、演出のみの技能判定へ
接続します。新しい技能は増やさず、`investigation`、`survival`、`persuasion`、
`athletics`、`stealth` のみを使用します。

| 入力例 | 推定技能 |
| --- | --- |
| 崖を登る / 走る / 飛び越える / 重い箱を動かす | `athletics` |
| 足跡を追う / ロープ跡をたどる / 海岸を探索する / 酒を飲む | `survival` |
| 説得する / 頼み込む / ごまかす / 聞き出す | `persuasion` |
| 忍び込む / 隠れる / 気付かれないように近づく | `stealth` |
| 詳しく調べる / 痕跡を分析する / 手掛かりを探す / 崖を覗く | `investigation` |

自由行動判定は状態異常、HP、疲労、時間経過、ダメージ、戦闘処理を発生させません。
結果は5段階ランクとGM演出で表現し、`PartialSuccess` は「達成したが代償や不安が残る」
程度の描写に留めます。シナリオ固有の効果が必要な場合は、自由行動ではなく
`action_checks` とランク別結果を定義してください。

自由行動判定の結果はGM生成コンテキストへも渡されます。コンテキストには
`action_text`、`skill`、`rank`、`roll`、`target` が含まれ、LLMはそれを参考情報として
「何が起きたか」を描写します。これは演出用の情報整理であり、HP、疲労、時間経過、
ダメージ、戦闘、状態異常などの新しい状態管理は追加しません。

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
