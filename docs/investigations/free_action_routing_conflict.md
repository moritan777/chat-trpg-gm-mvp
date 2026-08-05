# 自由行動ルーティング競合 調査結果

## 1. 原因

問題A（技能判定へ到達できないルーティング競合）の主因は、`judge()` が `match_action_check()` より前に `explicit_scene_target()` を評価し、NPC・オブジェクト・表層対象が見つかっただけで `match_action_check()` を呼ばずにスキップする構造である。

問題B（NPC観察でNPC証言が開示される情報公開競合）の主因は、NPCへの `inspect` でも `retrieve()` が対象NPC由来の Discoverable を通常検索し、`ask` 専用の追加ガードだけが掛かる構造である。`assistant_key_story` は `source.id=assistant` であり、`隠れてレナの様子を見る` が `target_id=assistant` の `inspect` になると検索対象に残る。

## 2. 現行ルーティング順

コード上の `judge()` の実順序は次の通り。

1. `companion_target(raw)` を評価する。
2. `explicit_scene_target(raw, st)` を評価し、対象候補を確定する。
   - 内部で `target(raw, "inspect", st)` により可視オブジェクト、現在地NPC、現在地または出口ロケーションを拾う。
   - 正式対象がなければ `surface_target(raw, st)` で表層対象を拾う。
3. `explicit_target` があれば `[ActionCheckRoute] decision=skipped` を出し、`match_action_check()` は呼ばない。
4. `explicit_target` がなければ `match_action_check(raw, st)` を呼び、該当時は `action_skill_check` を即 return する。
5. 対象種別ごとに許可された intent だけを `embedded_action_intent()` で分類する。
   - location: move / area_search / inspect
   - surface: inspect / area_search（area_search は inspect に戻す）
   - object: inspect / skill_check
   - npc: ask / inspect（ゴール対象なら resolve_goal も）
   - targetless: 全 intent
6. `infer_generic_skill_action(raw)` は最後に呼ばれる。
7. `should_route_generic_skill_action(action_type, target_id)` が `target_id is None` を要求するため、NPC・オブジェクト・表層・移動先がある入力は generic_skill_action に昇格しない。

優先順位を整理すると、現行は「明示対象を伴う移動・既存操作」→「シナリオ定義済み action_check」→「targetless generic_skill_action」である。特に明示対象がある場合は、action_check と generic_skill_action の両方が実質的に抑止される。

## 3. 各再現ケースの分岐経路

### ケースA: `岬の道へ行く` → `足跡を追う`

- `足跡` が `cliff_footprints` の alias として `target(raw, "inspect", st)` に拾われる。
- `explicit_scene_target()` が `cliff_footprints` を返す。
- `judge()` は `reason=explicit_object_target` で `match_action_check()` を呼ばない。
- object 分岐で `embedded_action_intent(raw, allowed=["inspect", "skill_check"])` を呼ぶ。
- `target_id` が残るため、後段の `infer_generic_skill_action()` が survival を推定しても `should_route_generic_skill_action()` により不採用。
- 最終結果は `inspect / cliff_footprints`。

### ケースB: `岬の道へ行く` → `崖を登る`

- `崖` が正式オブジェクト・NPC・出口として拾われない構成では `explicit_target` がない。
- `match_action_check()` が呼ばれる。
- `normalize_action_example()` 後の完全一致で `climb_cliff` が候補化される。
- `action_skill_check / climb_cliff` を即 return する。

ケースA/Bの差は、`足跡` は現在地の visible object として明示対象になる一方、`崖` は同じ文脈で操作対象として確定されないため、action_check 評価まで到達する点にある。

### ケースC: `隠れてレナの様子を見る`

- `レナ` が NPC alias として `assistant` に解決される。
- `explicit_scene_target()` が現在地NPCとして `assistant` を返す。
- `match_action_check()` は `explicit_npc_target` でスキップ。
- NPC分岐は allowed を `ask/inspect` に絞るため、stealth は action intent として選べない。
- `infer_generic_skill_action()` は `隠れ` / `様子を見る` から stealth を推定可能だが、`target_id=assistant` のため `should_route_generic_skill_action()` で不採用。
- 最終結果は `inspect / assistant`。

### ケースD: `小舟の陰に隠れて様子を見る`

- `小舟` が `cave_boat` の alias として visible object に拾われる。
- `explicit_scene_target()` が `cave_boat` を返す。
- `match_action_check()` は `explicit_object_target` でスキップ。
- object分岐は allowed を `inspect/skill_check` に絞る。
- generic skill 推定は stealth になり得るが、`target_id=cave_boat` のため不採用。
- 最終結果は `inspect / cave_boat`。

### ケースE: `漂着物を詳しく調べる`

- 正式 object がなければ `surface_phrase_from_raw()` が `漂着物` を抽出する。
- 現在地の `surface_objects` または scene text に存在すれば `surface:漂着物` になる。
- surface 分岐は `embedded_action_intent(raw, allowed=["inspect", "area_search"])` を使い、area_search でも inspect に戻す。
- `target_id=surface:漂着物` のため generic_skill_action は不採用。
- 現行設計では「描写中の表層物を軽く確認する no-reveal inspect」として扱うのが仕様に近い。

## 4. action_check競合の原因

`track_cliff_footprints` には required_location と positive_examples 完全一致で `足跡を追う` が定義されているため、`match_action_check()` が呼ばれれば exact match で選択可能である。しかし、`judge()` が explicit target を先に判定して `match_action_check()` を呼ばないため、候補ログ自体が出ない。

`崖を登る` は明示オブジェクトに吸われないため、同じ `cliff_path` で `match_action_check()` まで到達し、完全一致で `climb_cliff` が選ばれる。

## 5. generic_skill_action競合の原因

`infer_generic_skill_action()` は現行ファイル内では 1 定義のみで、標準技能は athletics / survival / persuasion / stealth / investigation をキーワード束から推定する。`足跡を追う` は survival、`隠れてレナの様子を見る` と `小舟の陰に隠れて様子を見る` は stealth、`漂着物を詳しく調べる` は investigation になり得る。

ただし generic_skill_action は `judge()` の最終段でしか評価されず、`should_route_generic_skill_action()` が `target_id is not None` を全面除外する。したがって「名詞を含む自由行動」は対象抽出が成功した時点で generic_skill_action に届かない。

## 6. NPC観察で証言が開示される原因

`resolve()` は `ask/inspect` のいずれでも `retrieve()` を呼ぶ。`retrieve()` は Discoverable の `source.id` と `target_id` が一致すれば候補に残し、positive_examples との類似度で reveal を決める。

NPC知識ガードは `_act == "ask"` の場合だけ `npc_can_reveal_topic_aware()` を使うため、NPC `inspect` では「このNPCにこの話題を聞いたか」の topic-aware 制約が掛からない。さらに `ask` の場合だけ `focus_hit=False` かつ embedding 類似度が低い時に高い `ASK_EMB_REVEAL_THRESHOLD` が適用される。`inspect` にはこの ask 専用保護がないため、focus が False でも通常の `EMB_REVEAL_THRESHOLD` を超えれば公開される。

結果として、観察入力が NPC inspect に誤分類されると、会話していないのに `public_text` が「話した」と表示され得る。これは技能判定競合とは別問題で、NPC由来 Discoverable の action_type 制約不足である。

## 7. 既存機能への影響範囲

既存テストは、明示オブジェクト調査が action_check embedding より優先されることを期待している。特に `足跡を見る` / `足跡を調べる` / `ランタンを見る` は従来どおり inspect であるべきである。

既存NPC聞き込みは `ask` を維持する必要がある。NPC観察の保護を入れる場合も、`助手に鍵のことを聞く` のような ask topic resolver と Discoverable 公開を壊さないよう、`ask` と `inspect` を分離するのが影響最小である。

表層対象は正式手がかりではなく no-reveal inspect として実装されているため、`漂着物を詳しく調べる` を generic investigation に寄せると、現行の surface no-reveal 設計と衝突する可能性がある。

## 8. 最小修正案

1. `judge()` で explicit target による action_check スキップ前に、限定条件付きで `match_action_check()` を評価する。
   - 条件: required_location が一致し、positive_examples の正規化完全一致がある場合のみ。
   - 効果: `足跡を追う` / `足跡をたどる` は `track_cliff_footprints`、`足跡を見る` / `足跡を調べる` は従来 inspect を維持できる。
2. `retrieve()` で `action_type == "inspect"` かつ source.type が npc の Discoverable は原則 reveal しない、または npc側に `inspect_revealable` のような明示許可がある場合だけ許可する。
   - 効果: `隠れてレナの様子を見る` や `レナの表情を見る` だけで証言が出ることを防ぐ。
3. diagnostic log を追加し、generic_skill 推定はあったが `target_id` により抑止されたことを見える化する。

## 9. 恒久修正案

LLM-first 方針に合わせるなら、対象抽出と行動中心の判定を分離する小さな中間表現を導入する。

- extracted_targets: NPC / object / surface / location の候補リスト。
- action_center: inspect target / ask target / move / scenario_check / contested_free_action / cover_or_means など。
- scenario_action_check exact match は author intent として高優先。
- generic_skill_action は「危険・不確実性・対抗・失敗に意味がある」場合にだけ route する。
- LLM は曖昧な action_center 判定の補助に使い、最終ルーティング全体を丸投げしない。

この設計なら、「小舟の陰に隠れる」の小舟を操作対象ではなく手段・遮蔽物として扱える。

## 10. 推奨案

短期は「action_check 完全一致の限定優先」と「NPC inspect でNPC証言を出さない保護」を推奨する。これは既存の見る・調べる・聞くルートの全面的な優先度低下を避けつつ、今回の2問題を分離して解消できる。

中期は action_center と target role の分離を導入し、明示対象がある自由行動を generic_skill_action 候補として評価できるようにする。ただし `漂着物を詳しく調べる` のような通常調査まで技能判定へ流さない条件設計が必要である。

## 11. 必要なテスト

- action_check 完全一致優先:
  - `足跡を追う` → `action_skill_check / track_cliff_footprints`
  - `足跡をたどる` → `action_skill_check / track_cliff_footprints`
  - `足跡を見る` → `inspect / cliff_footprints`
  - `足跡を調べる` → `inspect / cliff_footprints`
- 既存移動:
  - `岩場へ行く`、`灯台入口へ行く` → move
- 既存オブジェクト調査:
  - `ランタンを見る`、`血痕を見る`、`ロープ跡を見る`、`外套を見る`、`荷箱を見る`、`小舟を見る` → inspect
- 既存NPC聞き込み:
  - `村長に灯台守のことを聞く`、`漁師に青い光のことを聞く`、`助手に鍵のことを聞く`、`助手に本当のことを聞く` → ask / topic reveal維持
- 汎用自由行動:
  - targetless: `物陰に隠れて周囲を見る` → generic_skill_action / stealth
  - named target/means: `小舟の陰に隠れて様子を見る` は恒久案で stealth 候補、短期案では現行 inspect のままでも診断ログで抑止理由を出す
- Discoverable保護:
  - `隠れてレナの様子を見る`、`レナの表情を見る` → assistant_key_story / assistant_secret を reveal しない

## 12. 修正対象ファイルと関数

- `fixed_truth_ai_gm_mvp.py`
  - `judge()`：action_check 完全一致の限定先行評価、generic抑止ログ。
  - `match_action_check()`：完全一致だけを問い合わせられるヘルパー分離。
  - `explicit_scene_target()` / `target()`：恒久案では target role の分離。
  - `infer_generic_skill_action()`：現行は1定義のみ。恒久案では推定結果を対象ありでも候補として保持。
  - `should_route_generic_skill_action()`：恒久案では target_id 一律除外を廃止し、action_center / target_role で判断。
  - `retrieve()`：NPC source Discoverable の ask / inspect 分離。
- `tests/test_action_skill_checks.py`、`tests/test_generic_skill_actions.py`、必要なら新規テストファイル：上記回帰確認を追加。

