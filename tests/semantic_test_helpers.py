"""
semantic_test_helpers.py
========================
現行エンジン（今の本体）の振る舞いを正として、テストを「意味検証（behavior-based）」へ
そろえるための共有ヘルパー。

なぜ意味検証にするか:
  - action_type の内部綴りは Intent 階層導入後にゆれる（consult / conversation /
    banter_action / command / reason など）。しかも一部は Embedding プロバイダに
    依存するため、オフライン環境と実 Embedding 環境で異なる綴りになる。
  - よって「単一の綴りへの完全一致」ではなく「同じ意味のファミリに属するか」で
    検証すると、どちらの環境でも安定して通る。
"""

# 仲間へ向けた会話・相談・掛け合い系として現行エンジンが返し得る action_type 群。
# いずれも「シーン内オブジェクト操作ではなく、仲間に向けた発話系」を意味する。
# 実 Embedding 環境で観測された値（command / reason / banter_action）も含む。
COMPANION_CONVERSATION_FAMILY = {
    "consult",
    "conversation",
    "conversation_question",
    "banter_action",
    "command",
    "reason",
}

# 対象を伴わない自由入力（相談・雑談・感情表現など）が落ちる汎用行動ルート。
FREE_ACTION_FAMILY = {"generic_action", "action"}


def assert_companion_directed(test, intent, target_id, *, allow_free=False):
    """仲間宛て入力が『仲間ファミリ』として処理されたことを検証する。

    - target_id は companion_target がキーワードで決めるため決定的。ここは厳密一致。
    - action_type は環境でゆれるため、ファミリ包含で検証する。
    - allow_free=True の場合、相手指定なしで汎用行動へ落ちるケースも許可する。
    """
    test.assertEqual(intent.get("target_id"), target_id)
    allowed = set(COMPANION_CONVERSATION_FAMILY)
    if allow_free:
        allowed |= FREE_ACTION_FAMILY
    test.assertIn(
        intent.get("action_type"),
        allowed,
        f"action_type={intent.get('action_type')!r} は仲間会話ファミリに含まれない",
    )


def assert_no_scenario_reveal(test, events):
    """自由/会話ルートが、シナリオ正式発見（手掛かり開示）を誘発していないことを検証。

    仲間宛ての発話や汎用行動が、到達していない手掛かりを露出させない
    という情報境界の不変条件を守る。
    """
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        test.assertNotIn(
            ev.get("type"),
            {"reveal", "discovery"},
            f"想定外のシナリオ発見が誘発された: {ev}",
        )
        test.assertIsNone(
            ev.get("id"),
            f"想定外の発見IDが露出した: {ev}",
        )


def assert_packet_contains(test, packet, required_keys):
    """packet が必須キーを『含む』ことのみ検証（新規キー増分で壊れないようにする）。"""
    missing = set(required_keys) - set(packet)
    test.assertEqual(missing, set(), f"packet に必須キーが不足: {sorted(missing)}")


def assert_routes_through_intent_gate(test, log_text):
    """入力が Intent ゲートを通過した（＝シナリオ確定ルートで消費されていない）ことを検証。

    reason の綴り（conversation_intent / intent_generic_action など）は Embedding
    依存で環境ごとに変わるため、ゲート通過と matched=true のみを見る。
    """
    test.assertIn("[INTENT_GATE]", log_text)
    test.assertIn("matched=true", log_text)
