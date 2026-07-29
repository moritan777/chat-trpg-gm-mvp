# Authoring Prompt

この文書は、LLMに Chat TTRPG GM MVP 用シナリオを作らせるためのプロンプトテンプレートです。

`authoring_guide.md` と `scenario_template.md` と一緒に渡して使います。

---

## 1. 基本プロンプト

```text
あなたは Chat TTRPG GM MVP 用のシナリオ作者です。

以下の文書に従って、実行可能な author_scenario_xxx.md を作成してください。

参照文書:
- authoring_guide.md
- scenario_template.md
- authoring_best_practices.md

重要方針:
- 固定キーワードルールを書かない
- 意味の例を書く
- NPCには location, knows, topics を必ず書く
- Goalには intent_examples を必ず書く
- discoverableには positive_examples と public_text を必ず書く
- tests を必ず書く
- 出力は Markdown 形式
- scenario-json コードブロックを含める
```

---

## 2. 短編シナリオ作成プロンプト

```text
以下の条件で、Chat TTRPG GM MVP 用の短編シナリオを作ってください。

テーマ:
古い鉱山で作業員が行方不明になるシナリオ

規模:
- Location: 5個
- NPC: 4人
- Object: 8個
- Discoverable: 12個前後
- Goal: 1個
- Solution Path: 2個
- Tests: 3個以上

必須要件:
- NPCには location, availability, knows, does_not_know, topics を書く
- Goalには intent_examples を5〜10個書く
- discoverableの positive_examples は3〜6個書く
- requires_all / requires_any を使って条件付き手掛かりを最低2個作る
- 誤解釈テストを1個作る

出力形式:
- Markdown
- タイトルと短い説明
- ```scenario-json ブロック
- JSONは構文エラーがない形
```

---

## 3. 既存シナリオ改良プロンプト

```text
以下の author_scenario_xxx.md を改善してください。

改善目的:
NPCの所在地、知識、話題、Goal Intent Examples を明確にする。

作業内容:
1. すべてのNPCに location を追加
2. すべてのNPCに knows を追加
3. すべてのNPCに topics を追加
4. Goal に intent_examples を追加
5. discoverable の positive_examples が抽象的すぎる場合は具体化
6. tests に誤解釈系テストを追加

禁止:
- Pythonコードの変更案は出さない
- 固定キーワードルールは書かない
- シナリオ外の独自仕様を追加しない

出力:
修正済みの author_scenario_xxx.md 全文
```

---

## 4. シナリオレビュー用プロンプト

```text
以下の author_scenario_xxx.md をレビューしてください。

観点:
- JSON構文に問題がないか
- location の exits が自然か
- NPCの location が locations[].npcs と矛盾していないか
- NPCの knows と topics が discoverable と整合しているか
- discoverable の positive_examples が具体的か
- Goal の intent_examples が十分か
- requires_all / requires_any が過剰すぎないか
- tests が成功系、失敗系、誤解釈系を含んでいるか

出力形式:
1. 致命的問題
2. 改善推奨
3. 良い点
4. 修正案
```

---

## 5. Goal Intent Examples 生成プロンプト

```text
以下のGoalに対して、intent_examplesを10個作ってください。

Goal:
- id: rescue_keeper
- target: keeper
- 目的: 洞窟で倒れている灯台守ユアンを救出し、港へ連れ戻す

条件:
- 抽象語だけにしない
- 対象名を含める
- 固有名を含める
- 依頼形と宣言形を混ぜる
- 5〜15文字程度の短文だけでなく、自然な文章も混ぜる

悪い例:
- 助ける
- 解決する
- 実行する

良い例:
- 灯台守を助ける
- ユアンを救出する
- 洞窟の奥のユアンを助ける
```

---

## 6. NPC topics 生成プロンプト

```text
以下のNPCに対して topics を作ってください。

NPC:
- id: fisherman
- name: 漁師バロ
- knows: fisherman_blue_light
- 内容: 昨夜、岬の下で低い青い光を見た

条件:
- プレイヤーが聞きそうな話題語を書く
- 動詞だけにしない
- 1つのdiscoverableに対して3〜5個のtopicを作る

悪い例:
- 聞く
- 話
- 質問

良い例:
- 青い光
- 昨夜の光
- 岬の下
- 低い光
```

---

## 7. discoverable positive_examples 生成プロンプト

```text
以下のdiscoverableに対して positive_examples を作ってください。

Discoverable:
- id: broken_lantern_clue
- 内容: 割れたランタンは灯台守のもので、ガラス片は海岸側へ散っていた

条件:
- 3〜6個
- 調査対象、話題、言い換えを含める
- 動詞だけにしない

悪い例:
- 見る
- 調べる

良い例:
- ランタンを見る
- 割れたランタンを調べる
- ガラス片を見る
- 灯台守のランタン
```

---

## 8. LLM出力チェック用プロンプト

```text
次のシナリオJSONを確認してください。

チェック項目:
- 全てのJSONキーがダブルクォートで囲まれているか
- 末尾カンマがないか
- locations[].exits が実在する location を指すか
- locations[].npcs が実在する npc を指すか
- locations[].visible_objects が実在する object を指すか
- npcs[].knows と topics が実在する discoverable を指すか
- goals[].intent_examples が存在するか
- tests が存在するか

出力:
- 問題一覧
- 修正版JSON
```

---

## 9. LLMに守らせる禁止事項

LLMにシナリオを作らせる時は、以下を明示してください。

```text
禁止事項:
- Pythonコードを変更しない
- if文やキーワードルールを書かない
- scenario-json 以外の独自形式を作らない
- discoverable ID と topics の参照を曖昧にしない
- JSONコメントを書かない
- 末尾カンマを付けない
```

---

## 10. 推奨ワークフロー

```text
1. テーマを決める
2. この prompt をLLMへ渡す
3. author_scenario_xxx.md を生成する
4. md_to_scenario.py で変換する
5. scenario_lint.py で検査する
6. run_authoring_pipeline.py でテストする
7. 手動プレイする
8. ログをLLMに渡して改善する
```
