#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat-style TTRPG GM MVP v2.16.0

Current features:
- conditional discoverables: discoverables can now have requires_all / requires_any / required_location
- LLM banter: direct HTTP, observation-only packet
- Embedding judge: direct HTTP, lexical fallback
- Goal routing: requires_all / requires_any retained
"""
import argparse
import http.client
import json
import math
import os
import random
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VERSION = "v2.16.0 [generic-skill-checks]"
STANDARD_SKILLS = {
    "investigation": 0,
    "survival": 0,
    "persuasion": 0,
    "athletics": 0,
    "stealth": 0,
}


class State:
    def __init__(self, loc):
        self.location = loc
        self.discovered = set()
        self.ended = False


class Game:
    MAX_CONVERSATION_CONTINUE_TURNS = 5

    def __init__(self, scenario_dir, debug_judge=False, debug_llm=False, debug_embedding=False, dice_total=None, skill_dice_total=None, dice_seed=None):
        self.scenario_dir = Path(scenario_dir)
        self.sc = json.loads((self.scenario_dir / "scenario.json").read_text(encoding="utf-8"))
        self.debug = debug_judge
        self.debug_llm = debug_llm
        self.debug_embedding = debug_embedding
        self.dice_total = dice_total
        self.skill_dice_total = skill_dice_total
        self.rng = random.Random(dice_seed)
        self.locs = {x["id"]: x for x in self.sc.get("locations", [])}
        self.objects = {x["id"]: x for x in self.sc.get("objects", [])}
        self.npcs = {x["id"]: x for x in self.sc.get("npcs", [])}
        self.disc = {x["id"]: x for x in self.sc.get("discoverables", [])}
        self.action_checks = list(self.sc.get("action_checks", []) or [])
        self.player = dict(self.sc.get("player", {}) or {})
        # Keep the character sheet stable for scenario authors while preserving
        # scenario-defined values and any future custom skills.
        self.player["skills"] = {
            **STANDARD_SKILLS,
            **(self.player.get("skills", {}) or {}),
        }
        self.alias = {}
        self.alias_entries = []
        self.alias_seen = set()
        self.emb_cache = {}
        self.emb_disabled = False
        self.last_banter = {}
        self.last_companion_turn = {}
        self.companion_diagnostics = {
            "companion_turns": 0,
            "direct_responses": 0,
            "response_targets": {},
            "topic_turns": {},
            "topics": {},
            "focus_counts": {},
            "observed_turns": 0,
            "previous_topics": set(),
            "topic_transition_count": 0,
            "topic_branch_count": 0,
            "topic_jump_count": 0,
            "topic_branches": [],
            "nico_branch_count": 0,
            "nico_topics": set(),
            "continue_reset_count": 0,
            "continue_expire_count": 0,
            "character_topic_counts": {},
        }
        self.conversation_continue_count = 0
        self.last_embedding = {}
        for dct in (self.objects, self.npcs, self.locs):
            for key, value in dct.items():
                for alias in [value.get("name", ""), key] + value.get("aliases", []):
                    if alias:
                        self.alias[alias] = key
                        if (alias, key) not in self.alias_seen:
                            self.alias_entries.append((alias, key))
                            self.alias_seen.add((alias, key))

    # ---------- common HTTP ----------
    def debug_for_tag(self, tag):
        if tag == "BANTER":
            return self.debug_llm
        if tag == "EMB":
            return self.debug_embedding
        return self.debug

    def post_json(self, url, body, timeout_sec, tag):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        u = urllib.parse.urlparse(url)
        host = u.hostname or "127.0.0.1"
        port = u.port or (443 if u.scheme == "https" else 80)
        path = (u.path or "/") + (("?" + u.query) if u.query else "")
        if self.debug_for_tag(tag):
            print(f"[{tag}_URL]", url)
            print(f"[{tag}_CONNECT]", host, port, path)
            print(f"[{tag}_BYTES]", len(payload))
        t0 = time.perf_counter()
        conn = http.client.HTTPSConnection(host, port, timeout=timeout_sec) if u.scheme == "https" else http.client.HTTPConnection(host, port, timeout=timeout_sec)
        try:
            conn.request(
                "POST",
                path,
                body=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Content-Length": str(len(payload)),
                },
            )
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", "replace")
        finally:
            conn.close()
        ms = int((time.perf_counter() - t0) * 1000)
        if self.debug_for_tag(tag):
            print(f"[{tag}_STATUS]", resp.status, resp.reason)
            print(f"[{tag}_MS]", ms)
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f"HTTP {resp.status} {resp.reason}: {raw[:500]}")
        return json.loads(raw)

    # ---------- LLM ----------
    def llm_base_url(self):
        return (
            os.getenv("LLAMA_CPP_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "http://127.0.0.1:8080/v1"
        ).rstrip("/")

    def llm_model(self):
        return os.getenv("LLAMA_CPP_MODEL") or os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "local-model"

    def table_turn_temperature(self):
        """Return the effective Table Turn temperature with legacy fallback support."""
        variable = "TABLE_TURN_TEMPERATURE"
        value = os.getenv(variable)
        if value is None:
            variable = "GM_LINE_REWRITE_TEMPERATURE"
            value = os.getenv(variable, "0.9")
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid {variable}: {value}. Expected a numeric value such as 0.9"
            ) from exc



    def llm_desc(self):
        if os.getenv("LLM_PROVIDER", "llama_cpp") == "none":
            return "未設定。標準ライブラリのみのフォールバックで動作します。"
        return "有効 provider=llama_cpp base_url=" + self.llm_base_url() + " model=" + self.llm_model() + " APIキーなし Proxy無効"

    def companion_banter_prompt(self):
        return (
            "【情報境界・必須】\n"
            "事実は現在のGM事実、正式発見、場所・対象・行動、過去の公開情報だけ。"
            "current_observationsは表層情報で、未公開情報、内部情報、正解ルートは知らない。"
            "仮説、冗談、勘違い、過去の仲間台詞を確定事実や攻略情報にしない。\n"
            "\n"
            "【仲間の役割】\n"
            "仲間はGMの補助説明員ではなく、人物関係と卓の空気を作る参加者である。"
            "シナリオ上の重要度と人物の興味は別。事件だけでなく、環境、物、身体感覚、仲間、些細なことも話題にできる。\n"
            "\n"
            "【リュート】\n"
            "実務的な視点を持つ。ただし毎回段取りや安全確認を始める必要はない。"
            "周囲の話題に乗ったり、仲間の案を評価したり、雑談を楽しんだりしてもよい。"
            "状況によっては冒険談や想像話に参加してもよい。"
            "実務的な話題は選択肢の一つであり、常に最優先ではない。"
            "推理役、解説役、安全指導役には固定しない。\n"
            "\n"
            "【ニコ】\n"
            "小さな要素から妙な連想をする。細部、形、音、匂い、小物、違和感などに目が向きやすいが、"
            "観察そのものより「そこから何を思い付くか」を優先する。話題が少し飛んでもよい。"
            "霧から巨大イカ、ロープから海の怪物、匂いから昔話や伝説を思い出すような連想をしてよい。"
            "連想先は有益でも正確でもなくてよい。単なる観察報告で終えるより、"
            "「だから○○を思い出した」「そういえば○○って聞いたことない？」のように連想まで進める。"
            "仲間から「なんでそうなるんだ」と思われる発想も歓迎する。冗談役には固定しない。\n"
            "\n"
            "【ピピ】\n"
            "理屈より人へ意識が向く。\n"
            "状況そのものより、仲間やNPCがどうしているかに関心を持つ。\n"
            "体調、疲れ、不安、無理をしていないか、困っていないかなどによく気付く。\n"
            "自分が怖がるだけでなく、誰かを気遣ったり、人と人の関係や様子について話すことも多い。\n"
            "仲間やNPCへの反応が中心だが、怖がり役や特定人物への依存役には固定しない。\n"
            "\n"
            "【クロ】\n"
            "卓の盛り上げ役。正解でなくてよく、根拠の薄い説や大げさな想像を言ってよい。"
            "事件性、異常事態、騒ぎに興味を示しやすい。"
            "見栄、ホラ話、勘違い、自信満々な推測をしてよい。"
            "知らないことを知っているように話しても、それはホラ話、冗談、勘違いであり、未発見情報や真相を事実として知っているわけではない。\n"
            "ただし『何もしない』『帰ろう』『諦めよう』など進行を止める誘導は禁止。\n"
            "\n"
            "【ガラン】\n"
            "行動役ではなく軽い段取り役。次に何を試すか、どちらを先に見るかという簡単な提案をする。"
            "『行こう』『見よう』だけで終えず、候補を挙げたり順番をPLへ尋ねたりしてよい。"
            "推理を『絶対これだ』と断定せず、推理主導はPLに残す。\n"
            "\n"
            "【おふざけ入力】\n"
            "conversation_diagnostics.playfulInput=trueの時だけ、雑談モードを1ターン許可する。"
            "ツッコミ、妄想、茶化しに2名以上反応。クロは乗り、ピピは止め、ガランはツッコめる。"
            "推理進行を奪わず次ターンへ持ち越さない。falseなら従来どおり真面目に場面へ反応する。\n"
            "\n"
            "【会話・任意】\n"
            "場面へ感想を述べても、最初から仲間へ話しかけてもよい。複数行では、独立コメントより働きかけと短い応答が自然なら選べる。"
            "短い応答で終了してよく、独り言、沈黙、無視も自然なら許可する。掛け合いは必須ではない。\n"
            "【会話継続】conversation_context.mode=continueなら、previous_companion_linesへの返答、ツッコミ、同意、質問、便乗を優先する。"
            "requested_companionsがあればその人物を優先し、全員指定なら自然な範囲で全員参加を優先する。\n"
            "【話題の派生】会話継続では、同じ話題の反復よりも話題の変化・発展を優先する。"
            "巨大イカ→沈没船、沈没船→宝物、宝物→王様、王様→空飛ぶ魚のような自然な連想を歓迎する。"
            "同じ論点を繰り返さない。過去2ターン以内に「安全」「確認」「ルート」「装備」について既に話している場合、"
            "同じ内容を再度出す必要はない。可能なら別の反応や話題へ進む。\n"
            "\n"
            "【履歴と行数・必須】\n"
            "仲間発言は0〜5行。参加者指定がなければ必要な人物だけ話し、全員や5行を埋めない。同じ人物の短い再応答もよい。"
            "過去台詞をコピーまたは言い換え再出力しない。"
        )

    def recent_companion_lines(self, limit=5):
        return list(self.last_companion_turn.get("lines", []))[-limit:]

    def playful_input_diagnostic(self, raw):
        """Return the existing playful classification and an audit reason."""
        text = unicodedata.normalize("NFKC", str(raw or "")).strip().lower()
        if not text:
            return False, "empty_input"
        # These concrete, deliberately absurd actions provide a stable fallback
        # when no separate diagnostic LLM is configured. The table-turn LLM still
        # receives both the original input and this explicit diagnostic.
        playful_markers = (
            "舐め", "なめる", "飛び込", "崖から落と", "全部飲", "一気飲み",
            "宝箱ある", "宝物ある", "秘密基地", "犯人ここ", "食べてみ",
        )
        matched = next((marker for marker in playful_markers if marker in text), None)
        return (True, "matched_marker:" + matched) if matched else (False, "no_marker_match")

    def playful_input(self, raw):
        """Detect an intentionally silly table action without reclassifying normal play."""
        return self.playful_input_diagnostic(raw)[0]

    def recent_companion_topic_summary(self, limit=3):
        """Return frequent surface topics from the latest companion history."""
        counts = {}
        for line in self.recent_companion_lines():
            for topic in self.companion_topics([line]):
                counts[topic] = counts.get(topic, 0) + 1
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [topic for topic, _count in ordered[:limit]]

    def reset_conversation_continuation(self, reason=None, from_location=None, to_location=None):
        """End continuation mode without deleting dialogue history or statistics."""
        turns = self.conversation_continue_count
        self.conversation_continue_count = 0
        if reason == "LocationChanged":
            self.companion_diagnostics["continue_reset_count"] += 1
        elif reason == "ContinueExpired":
            self.companion_diagnostics["continue_expire_count"] += 1
        if reason and (self.debug_llm or self.debug):
            print("[CONVERSATION_RESET]")
            print("Reason=" + reason)
            if reason == "LocationChanged":
                print("From=" + str(from_location or ""))
                print("To=" + str(to_location or ""))
            elif reason == "ContinueExpired":
                print(f"Turns={turns}")
                print("LastTopics=" + "|".join(self.recent_companion_topic_summary()))

    def remember_companion_turn(self, lines, it, st):
        companion_lines = [
            str(line).strip()
            for line in lines
            if str(line).strip().startswith(tuple(self.companion_names()))
        ]
        if not companion_lines:
            self.last_companion_turn = {}
            return
        self.last_companion_turn = {
            "lines": companion_lines[-5:],
            "context": {
                "location_id": st.location,
                "location": self.locs.get(st.location, {}).get("name", st.location),
                "target": it.get("target_id"),
                "action": it.get("action_type"),
            },
        }

    def companion_speaker(self, line):
        """Return the companion name at the start of a rendered dialogue line."""
        text = str(line).strip()
        return next((name for name in self.companion_names() if text.startswith(name)), "")

    def companion_focus(self, speaker, line=None):
        """Classify a line for diagnostics only; never influence generation."""
        if line is None:  # Compatibility for callers using the v2.15.19 signature.
            line = speaker
            speaker = self.companion_speaker(line)
        if speaker == "ニコ" and any(
            word in line
            for word in (
                "連想", "思い出", "そういえば", "聞いたこと", "みたい", "だったり",
                "巨大イカ", "宝物", "空飛ぶ魚", "怪物", "伝説", "昔話",
            )
        ):
            return "妙な連想"
        if speaker == "ピピ":
            npc_terms = []
            for npc in self.npcs.values():
                npc_terms.append(str(npc.get("name", "")))
                npc_terms.extend(str(alias) for alias in npc.get("aliases", []) or [])
            if "NPC" in line or any(term and term in line for term in npc_terms):
                return "NPC"
            if any(word in line for word in ("体調", "疲れ", "休", "怪我", "痛", "顔色")):
                return "体調"
            if any(word in line for word in ("不安", "怖", "心配", "大丈夫")):
                return "不安"
            if any(word in line for word in ("仲間", "みんな", "無理", "困", "様子")):
                return "仲間の様子"
        if speaker == "リュート":
            if any(word in line for word in ("役割", "分担", "誰が", "担当")):
                return "役割分担"
            if any(word in line for word in ("時間", "先に", "後で", "順番")):
                return "時間配分"
            if any(word in line for word in ("装備", "道具", "持って", "荷物")):
                return "装備"
            if any(word in line for word in ("段取り", "準備", "移動", "ルート", "確認", "確保", "点検")):
                return "段取り"
        categories = [
            ("段取り", ("段取り", "準備", "装備", "順番", "役割", "時間", "持って")),
            ("仲間の様子", ("体調", "疲れ", "無理", "大丈夫", "心配", "様子", "休")),
            ("行動", ("やる", "行こう", "試す", "開け", "押す", "壊す", "登る")),
            ("観察", ("違和感", "音", "匂い", "形", "見える", "気になる")),
            ("面白さ", ("面白", "すごい", "騒ぎ", "俺なら", "実は")),
        ]
        return next((label for label, words in categories if any(word in line for word in words)), "その他")

    def companion_topics(self, lines):
        """Extract repeated surface terms as a deliberately lightweight topic signal."""
        ignored = {
            "全員", "仲間", "今回", "自分", "様子", "気持ち", "本当", "一緒", "問題", "話して",
        }
        topics = set()
        for line in lines:
            dialogue = re.sub(r"^[^:：「『]+[:：]?[「『]?", "", str(line))
            compounds = re.findall(r"[一-龠ァ-ヶー]{2,}", dialogue)
            phrases = re.findall(
                r"([一-龠ァ-ヶー][一-龠ァ-ヶーぁ-ん]{1,12}?)(?=の(?:話|影|こと))",
                dialogue,
            )
            phrases = [
                term for term in phrases
                if not any(separator in term for separator in ("と", "や", "または", "そして"))
            ]
            for term in compounds + phrases:
                term = re.sub(r"^(?:それなら|それ|その|じゃあ|でも|確かに|たしかに)", "", term)
                if term not in ignored and not any(name in term for name in self.companion_names()):
                    if len(term) >= 2:
                        topics.add(term)
        return topics

    def companion_character_topics(self, line):
        """Return normalized diagnostic topics without influencing generation."""
        normalized = {
            "安全": ("安全", "危険", "退路"),
            "確認": ("確認", "点検", "チェック"),
            "ルート": ("ルート", "経路", "道順", "移動"),
            "装備": ("装備", "道具", "荷物", "持って"),
            "段取り": ("段取り", "準備", "役割", "分担", "順番", "時間配分"),
        }
        topics = {
            topic for topic, words in normalized.items() if any(word in line for word in words)
        }
        return topics or self.companion_topics([line])

    def observe_companion_turn(self, lines, it):
        """Collect and print non-invasive conversation-chain diagnostics."""
        companion_lines = [str(line).strip() for line in lines if self.companion_speaker(line)]
        if not companion_lines:
            return
        stats = self.companion_diagnostics
        stats["observed_turns"] += 1
        turn_number = stats["observed_turns"]
        prior_speakers = [self.companion_speaker(line) for line in self.recent_companion_lines()]
        seen_speakers = [name for name in prior_speakers if name]
        continuation = self.continues_companion_conversation(it.get("raw", ""))
        reaction_cues = ("それ", "その", "そう", "たしかに", "確かに", "でも", "じゃあ", "なら", "うん", "いや")

        for line in companion_lines:
            speaker = self.companion_speaker(line)
            mentioned = [name for name in seen_speakers if name != speaker and name in line]
            responded_to = mentioned[-1] if mentioned else ""
            if not responded_to and continuation and any(cue in line for cue in reaction_cues):
                responded_to = next((name for name in reversed(seen_speakers) if name != speaker), "")
            stats["companion_turns"] += 1
            focus = self.companion_focus(speaker, line)
            character_focus = stats["focus_counts"].setdefault(speaker, {})
            character_focus[focus] = character_focus.get(focus, 0) + 1
            character_topics = stats["character_topic_counts"].setdefault(speaker, {})
            for topic in sorted(self.companion_character_topics(line)):
                character_topics[topic] = character_topics.get(topic, 0) + 1
                if self.debug_llm or self.debug:
                    print("[COMPANION_TOPIC]")
                    print("Character=" + speaker)
                    print("Topic=" + topic)
            if responded_to:
                stats["direct_responses"] += 1
                key = f"{speaker}->{responded_to}"
                stats["response_targets"][key] = stats["response_targets"].get(key, 0) + 1
            if self.debug_llm or self.debug:
                print("[COMPANION_DIAGNOSTICS]")
                print("Character=" + speaker)
                print("Trigger=" + ("会話継続" if continuation else "場面反応"))
                print("RespondedTo=" + (responded_to or "なし"))
                print("Focus=" + focus)
            seen_speakers.append(speaker)

        current_topics = set()
        topics_by_speaker = {}
        for line in companion_lines:
            speaker = self.companion_speaker(line)
            for topic in self.companion_topics([line]):
                current_topics.add(topic)
                topics_by_speaker.setdefault(speaker, set()).add(topic)
                stats["topic_turns"].setdefault(topic, set()).add(turn_number)
                record = stats["topics"].setdefault(
                    topic,
                    {
                        "origin": speaker,
                        "created_turn": turn_number,
                        "last_referenced": turn_number,
                        "turns": set(),
                        "speakers_by_turn": {},
                    },
                )
                record["last_referenced"] = turn_number
                record["turns"].add(turn_number)
                record["speakers_by_turn"].setdefault(turn_number, set()).add(speaker)

        nico_topics = topics_by_speaker.get("ニコ", set())
        stats["nico_topics"].update(nico_topics)
        previous_topics = stats["previous_topics"]
        if previous_topics and current_topics:
            overlap = previous_topics & current_topics
            new_topics = current_topics - previous_topics
            stats["topic_transition_count"] += 1
            if overlap and new_topics:
                stats["topic_branch_count"] += 1
                if nico_topics & new_topics:
                    stats["nico_branch_count"] += 1
                source = sorted(overlap)[0]
                for destination in sorted(new_topics):
                    stats["topic_branches"].append((source, destination))
            elif not overlap:
                stats["topic_jump_count"] += 1
        stats["previous_topics"] = current_topics

    def print_conversation_stats(self):
        """Print aggregate diagnostics at session end when debugging is enabled."""
        if not (self.debug_llm or self.debug):
            return
        stats = self.companion_diagnostics
        total = stats["companion_turns"]
        direct = stats["direct_responses"]
        rate = (direct / total * 100.0) if total else 0.0
        repeated_topics = {
            topic: len(turns) for topic, turns in stats["topic_turns"].items() if len(turns) >= 2
        }
        maintained_turns = set()
        for topic in repeated_topics:
            maintained_turns.update(stats["topic_turns"][topic])
        observed = stats["observed_turns"]
        topic_rate = (len(maintained_turns) / observed * 100.0) if observed else 0.0
        transitions = stats["topic_transition_count"]
        branch_count = stats["topic_branch_count"]
        branch_rate = (branch_count / transitions * 100.0) if transitions else 0.0
        print("[CONVERSATION_STATS]")
        print(f"CompanionTurns={total}")
        print(f"DirectResponseCount={direct}")
        print(f"ChainRate={rate:.1f}%")
        print(f"TopicMaintenanceRate={topic_rate:.1f}%")
        print(f"TopicBranchRate={branch_rate:.1f}%")
        print(f"TopicBranchCount={branch_count}")
        print(f"ContinueResetCount={stats['continue_reset_count']}")
        print(f"ContinueExpireCount={stats['continue_expire_count']}")
        print(f"ContinueWindow={self.MAX_CONVERSATION_CONTINUE_TURNS}")
        print(
            "ConversationResets="
            + str(stats["continue_reset_count"] + stats["continue_expire_count"])
        )
        for topic, count in sorted(repeated_topics.items(), key=lambda item: (-item[1], item[0])):
            print(f"Topic={topic} TurnsReferenced={count}")
        for pair, count in sorted(stats["response_targets"].items()):
            print(f"ResponseTarget={pair} Count={count}")
        for character in self.companion_names():
            for topic, count in sorted(
                stats["character_topic_counts"].get(character, {}).items(),
                key=lambda item: (-item[1], item[0]),
            ):
                print(f"CharacterTopic={character} Topic={topic} Count={count}")

        print("[TOPIC_BRANCH]")
        for source, destination in stats["topic_branches"][:20]:
            print(f"{source} -> {destination}")

        print("[NICO_DIAGNOSTICS]")
        print(f"BranchCount={stats['nico_branch_count']}")
        print(f"UniqueTopics={len(stats['nico_topics'])}")
        for topic in sorted(stats["nico_topics"]):
            print(topic)

        print("[FOCUS_STATS]")
        for character in self.companion_names():
            counts = stats["focus_counts"].get(character, {})
            total_focus = sum(counts.values())
            if not total_focus:
                continue
            print(f"Character={character}")
            for focus, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
                print(f"{focus}={count / total_focus * 100.0:.1f}% Count={count}")

        print("[TOPIC_ORIGIN]")
        for topic, record in sorted(stats["topics"].items(), key=lambda item: (item[1]["created_turn"], item[0])):
            print(f"Topic={topic} Origin={record['origin']}")

        print("[TOPIC_SURVIVAL]")
        for topic, record in sorted(stats["topics"].items(), key=lambda item: (item[1]["created_turn"], item[0])):
            lifetime = record["last_referenced"] - record["created_turn"]
            print(
                f"Topic={topic} CreatedTurn={record['created_turn']} "
                f"LastReferenced={record['last_referenced']} Lifetime={lifetime}"
            )

        print("[CHARACTER_INFLUENCE]")
        for character in self.companion_names():
            created = sum(1 for record in stats["topics"].values() if record["origin"] == character)
            survived = sum(
                1
                for record in stats["topics"].values()
                if len(record["turns"]) >= 2
                for turn, speakers in record["speakers_by_turn"].items()
                if turn > record["created_turn"] and character in speakers
            )
            print(f"Character={character} TopicsCreated={created} TopicsSurvived={survived}")

    def debug_companion_history(self, heading, history=None, action=None, reason=None):
        if not (self.debug_llm or self.debug):
            return
        history = self.last_companion_turn if history is None else history
        print(f"[{heading}]")
        print("scene=" + json.dumps(history.get("context", {}), ensure_ascii=False, sort_keys=True))
        print("lines=" + json.dumps(history.get("lines", []), ensure_ascii=False))
        if action is not None:
            print("action=" + action)
            print("reason=" + (reason or ""))

    def llm_chat(self, packet):
        if os.getenv("LLM_PROVIDER", "llama_cpp") == "none":
            return ""
        system_prompt = (
            "仲間キャラの短い発言だけを書く。GM文は禁止。"
            + self.companion_banter_prompt()
            + "current_observationsは目に見える表層情報。recent_companion_linesは参考用の過去会話で、現在の事実ではなくコピー禁止。"
        )
        body = {
            "model": self.llm_model(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
            ],
            "temperature": float(os.getenv("BANTER_TEMPERATURE", "0.75")),
            "max_tokens": int(os.getenv("BANTER_MAX_TOKENS", "140")),
        }
        if self.debug_llm:
            print("[BANTER_SYSTEM]\n" + system_prompt)
            print("[BANTER_USER]\n" + body["messages"][1]["content"])
        base = self.llm_base_url()
        urls = [base + "/chat/completions"] if base.endswith("/v1") else [base + "/chat/completions", base + "/v1/chat/completions"]
        for url in urls:
            try:
                data = self.post_json(url, body, int(os.getenv("BANTER_TIMEOUT", "60")), "BANTER")
                choice = data.get("choices", [{}])[0]
                out = choice.get("message", {}).get("content") or choice.get("text", "") or ""
                out = out.strip()
                if self.debug_llm:
                    print("[BANTER_RAW]", repr(out))
                return out
            except Exception as e:
                if self.debug_llm:
                    print("[BANTER_ERROR]", url, repr(e))
        return ""

    # ---------- Embedding ----------
    def emb_base_url(self):
        return (os.getenv("EMBEDDING_BASE_URL") or os.getenv("EMB_BASE_URL") or "http://127.0.0.1:8081/v1").rstrip("/")

    def emb_model(self):
        return os.getenv("EMBEDDING_MODEL") or os.getenv("EMB_MODEL") or "local-embedding"

    def emb_desc(self):
        return self.emb_base_url() + " model=" + self.emb_model()

    def emb_urls(self):
        base = self.emb_base_url()
        return [base + "/embeddings"] if base.endswith("/v1") else [base + "/embeddings", base + "/v1/embeddings"]

    def parse_embeddings(self, data):
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return [x.get("embedding", []) for x in data["data"]]
        if isinstance(data, dict) and isinstance(data.get("embeddings"), list):
            return data["embeddings"]
        if isinstance(data, dict) and isinstance(data.get("embedding"), list):
            return [data["embedding"]]
        raise RuntimeError("unsupported embedding response shape")

    def get_embeddings(self, texts):
        if os.getenv("EMBEDDING_PROVIDER", "local") == "none" or self.emb_disabled:
            return None
        result, missing, missing_idx = [], [], []
        for idx, text in enumerate(texts):
            key = text or ""
            if key in self.emb_cache:
                result.append(self.emb_cache[key])
            else:
                result.append(None)
                missing.append(key)
                missing_idx.append(idx)
        if not missing:
            return result
        body = {"model": self.emb_model(), "input": missing}
        last_error = None
        for url in self.emb_urls():
            try:
                data = self.post_json(url, body, int(os.getenv("EMBEDDING_TIMEOUT", "30")), "EMB")
                vectors = self.parse_embeddings(data)
                if len(vectors) != len(missing):
                    raise RuntimeError(f"embedding count mismatch: got {len(vectors)} expected {len(missing)}")
                for text, vec, idx in zip(missing, vectors, missing_idx):
                    self.emb_cache[text] = vec
                    result[idx] = vec
                return result
            except Exception as e:
                last_error = e
                if self.debug_embedding:
                    print("[EMB_ERROR]", url, repr(e))
        self.emb_disabled = True
        if self.debug_embedding:
            print("[EMB_DISABLED]", repr(last_error))
        return None

    def cosine(self, a, b):
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        na = math.sqrt(sum(float(x) * float(x) for x in a))
        nb = math.sqrt(sum(float(y) * float(y) for y in b))
        return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


    def llm_gm_commentary(self, packet, fallback):
        """Rewrite canonical GM lines into replay-like GM speech.

        v2.11.6 policy:
        - .py decides the factual content and passes it as fallback/canonical_text.
        - LLM rewrites style only.
        - If LLM fails or changes format too much, canonical text is used.
        """
        canonical_text = (fallback or "").strip()
        if not canonical_text:
            return fallback
        if os.getenv("TABLE_TURN_RENDER", "1") == "1":
            return fallback
        if os.getenv("LLM_PROVIDER", "llama_cpp") == "none":
            return fallback
        packet = dict(packet or {})
        packet["canonical_gm_text"] = canonical_text
        packet["rewrite_policy"] = {
            "task": "Rewrite canonical_gm_text into TRPG replay GM tone.",
            "preserve_meaning": True,
            "do_not_add_new_facts": True,
            "do_not_reveal_hidden_clues": True,
            "gm_only": True,
            "companions_forbidden": True,
        }
        system_prompt = (
            "あなたはチャット型TRPGリプレイのGM文リライター。"
            "canonical_gm_textのGM発話だけを、TRPGリプレイの卓でGMが実際に喋っているような口調へ言い換える。"
            "新しい事実は作らない。意味・事実・情報量を増やさない。未発見の手がかり、真相、正解ルートを追加しない。"
            "『発見:』『判定:』『結果:』『補正:』などのログ行は絶対に作らない。"
            "リュート/ニコ/ピピ/クロ/ガランなど仲間発言は禁止。GM発話だけを書く。"
            "出力は必ず『GM:』で始める。JSON、箇条書き、コードブロックは禁止。"
            "\n\n"
            "【GMの口調】"
            "少しくだけた会話口調。説明者ではなく、卓を回しているGMとして話す。"
            "プレイヤーの行動をまず受け止める。『じゃあ』『なるほど』『ふむ』『うーん』『そうだね』などを自然に使ってよい。"
            "ただし毎回同じ相づちを使わない。命令口調や攻略ガイド口調にしない。"
            "『あなたは〜します』『〜してみましょう』『〜へと移動します』のような硬いシステム文は避ける。"
            "代わりに『じゃあ〜へ向かうね』『〜を見てみるんだね』『〜に話を振る感じかな』のようにする。"
            "語ってよいが、canonical_gm_textに無い内容は足さない。"
            "\n\n"
            "【良い変換例】"
            "canonical: GM: あなたは酒場へ向かいます。 GM: 嵐の夜を過ごした漁師たちが集まる酒場。窓は潮で白く曇っている。"
            "rewrite: GM: じゃあ酒場へ向かうんだね。中には、嵐の夜をやり過ごした漁師たちが集まっている。窓は潮で白く曇っていて、空気は少し重い感じかな。"
            "canonical: GM: 村長と会話します。"
            "rewrite: GM: じゃあ村長に話を聞いてみるんだね。村長は少し考え込んでから、重そうに口を開く。"
            "canonical: GM: 港から灯台入口へ直接向かうのは難しそうです。 GM: 今すぐ動けそうなのは、酒場、倉庫、岬の道です。"
            "rewrite: GM: うーん、灯台は見えてるんだけど、港からそのまま登っていく道はなさそうだね。動くなら、酒場や倉庫に寄るか、岬の道へ回る感じかな。"
            "canonical: GM: 潮汐表に注意を向けます。 GM: 港に置かれた潮汐表。昨夜の干潮時刻に赤い印がつけられている。"
            "rewrite: GM: じゃあ潮汐表を見てみるんだね。港に置かれた表を確認すると、昨夜の干潮時刻のところに赤い印がついている。"
            "\n\n"
            "【悪い変換】"
            "『あなたは倉庫へと移動します』『村長に話を聞いてみましょう』のような丁寧すぎる説明文。"
            "『次は〜してください』『〜するのが正解です』のような攻略指示。"
            "canonical_gm_textに無い手がかりや推理を足すこと。"
        )
        body = {
            "model": self.llm_model(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
            ],
            "temperature": float(os.getenv("GM_REWRITE_TEMPERATURE", os.getenv("GM_COMMENTARY_TEMPERATURE", "0.45"))),
            "max_tokens": int(os.getenv("GM_REWRITE_MAX_TOKENS", os.getenv("GM_COMMENTARY_MAX_TOKENS", "220"))),
        }
        base = self.llm_base_url()
        urls = [base + "/chat/completions"] if base.endswith("/v1") else [base + "/chat/completions", base + "/v1/chat/completions"]
        for url in urls:
            try:
                data = self.post_json(url, body, int(os.getenv("GM_REWRITE_TIMEOUT", os.getenv("GM_COMMENTARY_TIMEOUT", "45"))), "GM_REWRITE")
                choice = data.get("choices", [{}])[0]
                out = choice.get("message", {}).get("content") or choice.get("text", "") or ""
                out = out.strip()
                if not out or "```" in out or out.lstrip().startswith("{"):
                    return fallback
                if any(name in out for name in self.companion_names()):
                    return fallback
                if not out.startswith("GM:"):
                    out = "GM: " + out
                if self.debug:
                    print("[GM_REWRITE_RAW]", repr(out))
                self.last_gm_commentary = {"packet": packet, "canonical": canonical_text, "output": out}
                return out
            except Exception as e:
                if self.debug:
                    print("[GM_REWRITE_ERROR]", type(e).__name__, str(e))
        return fallback

    def score_examples(self, raw, examples):
        examples = [x for x in examples if x]
        if not examples:
            return 0.0, "none"
        vectors = self.get_embeddings([raw] + examples)
        if vectors:
            return max(self.cosine(vectors[0], v) for v in vectors[1:]), "embedding"
        return (1.0 if any(x in raw for x in examples) else 0.0), "lexical"

    # ---------- Game mechanics ----------
    def roll(self, skill=False):
        if skill and self.skill_dice_total is not None:
            return self.skill_dice_total
        if self.dice_total is not None:
            return self.dice_total
        return self.rng.randint(1, 6) + self.rng.randint(1, 6)

    def roll_dice(self, notation="2d6", skill=False):
        """Roll an NdM expression while preserving deterministic CLI test overrides."""
        if skill and self.skill_dice_total is not None:
            return self.skill_dice_total
        if self.dice_total is not None:
            return self.dice_total
        match = re.fullmatch(r"([1-9]\d*)d([1-9]\d*)", str(notation).strip().lower())
        if not match:
            raise ValueError(f"unsupported dice notation: {notation}")
        count, sides = map(int, match.groups())
        return sum(self.rng.randint(1, sides) for _ in range(count))

    def entity_kind(self, key):
        if key in self.locs:
            return "location"
        if key in self.npcs:
            return "npc"
        if key in self.objects:
            return "object"
        if isinstance(key, str) and key.startswith("companion:"):
            return "companion"
        if isinstance(key, str) and key.startswith("surface:"):
            return "surface"
        return "unknown"

    def goal_targets(self):
        return {g.get("target") for g in self.sc.get("goals", []) if g.get("target")}


    # ---- v2.15.0 Goal Intent Examples helpers ----
    def goal_by_target(self, target_id):
        for g in self.sc.get("goals", []) or []:
            if g.get("target") == target_id:
                return g
        return None

    def goal_intent_examples_for_target(self, target_id):
        g = self.goal_by_target(target_id)
        if not g:
            return []
        examples = []
        for key in ("intent_examples", "positive_examples", "goal_examples"):
            examples += list(g.get(key, []) or [])
        # Path examples are optional, but useful for scenarios where each route has a distinct ending expression.
        for path in g.get("solution_paths", []) or []:
            if isinstance(path, dict):
                examples += list(path.get("intent_examples", []) or [])
        return [str(x) for x in examples if str(x).strip()]

    def goal_intent_override(self, raw, target_id):
        """Return ('resolve_goal', mode) when the utterance matches goal intent examples.

        This is data-driven. No fixed verb list is used here.
        Scenario authors decide goal expressions through goals[].intent_examples.
        """
        examples = self.goal_intent_examples_for_target(target_id)
        if not examples:
            return None
        score, mode = self.score_examples(raw, examples)
        threshold = float(os.getenv("GOAL_INTENT_THRESHOLD", os.getenv("ACTION_INTENT_THRESHOLD", "0.62")))
        if self.debug:
            print(f"[GoalIntent] input={raw} target={target_id} score={score:.3f} threshold={threshold:.2f} examples={len(examples)}")
        if score >= threshold:
            return "resolve_goal", "goal-intent"
        return None
    # ---- /v2.15.0 Goal Intent Examples helpers ----

    def companion_aliases(self):
        names = []
        for c in self.sc.get("companions", []) or []:
            if isinstance(c, dict):
                names.append(c.get("name", ""))
                names += list(c.get("aliases", []) or [])
            elif isinstance(c, str):
                names.append(c)
        names += self.companion_names()
        return [x for x in dict.fromkeys(names) if x]

    def companion_names(self):
        return ["ニコ", "ピピ", "リュート", "クロ", "ガラン"]

    def action_intent_examples(self):
        return {
            "move": [
                "場所へ移動する", "目的地へ向かう", "そこへ行く", "別の場所へ進む", "元の場所へ戻る", "道を進む",
            ],
            "inspect": [
                "対象を見る", "対象を調べる", "詳しく観察する", "手がかりを確認する", "物を調べる",
            ],
            "area_search": [
                "周辺を調べる", "あたりを見回す", "何かないか探す", "手がかりを探す", "周囲を探索する", "この場所を確認する",
            ],
            "ask": [
                "人物に質問する", "話を聞く", "証言を聞く", "事情を尋ねる", "人に問いかける",
            ],
            "consult": [
                "仲間に相談する", "仲間の意見を聞く", "どう思うか聞く", "気づいたことがないか尋ねる", "助言を求める",
            ],
            "action": [
                "今日はどうする？", "ありがとう", "疲れた", "怖くなってきた", "酒盛りしよう", "踊ろう",
            ],
            "skill_check": [
                "詳しく解析する", "判定する", "技術的に分析する", "知識を使って読み解く", "能力を使って調べる",
            ],
            "resolve_goal": [
                "問題を解決する", "救助する", "犯人を特定する", "扉を開く", "結論を実行する", "目的を達成する",
            ],
        }

    def lexical_action_fallback(self, raw):
        # Fallback only. Primary routing should be embedding-based when embeddings are available.
        if any(x in raw for x in ["行く", "向かう", "移動", "進む", "戻る"]):
            return "move", "lexical"
        if any(x in raw for x in ["解析", "分析", "判定"]):
            return "skill_check", "lexical"
        if any(x in raw for x in ["助けて", "救助", "特定", "解決", "開く", "修復", "協力"]):
            return "resolve_goal", "lexical"
        if any(name in raw for name in self.companion_aliases()) and any(x in raw for x in ["どう思う", "相談", "意見", "気づ"]):
            return "consult", "lexical"
        if any(x in raw for x in ["聞く", "尋ねる", "問い詰める", "追及"]):
            return "ask", "lexical"
        if any(x in raw for x in ["周辺", "周囲", "あたり", "辺り", "この辺"]) and any(x in raw for x in ["調べ", "探", "見回", "見渡"]):
            return "area_search", "lexical"
        return "action", "lexical"

    def embedded_action_intent(self, raw, allowed=None):
        intents = self.action_intent_examples()
        if allowed:
            allowed_set = set(allowed)
            intents = {k: v for k, v in intents.items() if k in allowed_set}
        if not intents:
            return "inspect", "fallback"
        flat = []
        spans = []
        for name, examples in intents.items():
            start = len(flat)
            flat.extend(examples)
            spans.append((name, start, len(flat)))
        vectors = self.get_embeddings([raw] + flat)
        if not vectors:
            action, mode = self.lexical_action_fallback(raw)
            if allowed and action not in allowed:
                action = allowed[0]
            return action, mode
        raw_v = vectors[0]
        scores = []
        for name, start, end in spans:
            sims = [self.cosine(raw_v, vectors[i + 1]) for i in range(start, end)]
            scores.append((max(sims) if sims else 0.0, name))
        scores.sort(reverse=True)
        best_score, best_name = scores[0]
        threshold = float(os.getenv("ACTION_INTENT_THRESHOLD", "0.62"))
        tie_margin = float(os.getenv("ACTION_INTENT_TIE_MARGIN", "0.05"))
        priority = {
            "consult": 100,
            "area_search": 90,
            "move": 80,
            "ask": 70,
            "skill_check": 60,
            "resolve_goal": 50,
            "inspect": 40,
            "action": 30,
        }
        close = [(score, name) for score, name in scores if best_score - score <= tie_margin]
        if best_score >= threshold:
            selected = max(close, key=lambda x: (priority.get(x[1], 0), x[0]))[1]
        else:
            selected = "action" if not allowed else ("inspect" if "inspect" in allowed else allowed[0])
        if self.debug:
            parts = " ".join(f"{name}={score:.3f}" for score, name in scores[:5])
            close_parts = ",".join(f"{name}:{score:.3f}" for score, name in close)
            allow_txt = ",".join(allowed) if allowed else "all"
            print(f"[ActionIntent] input={raw} mode=embedding allowed={allow_txt} selected={selected} score={best_score:.3f} threshold={threshold:.2f} tie_margin={tie_margin:.2f} close={close_parts} candidates={parts}")
        return selected, "embedding"

    def companion_target(self, raw):
        for name in self.companion_aliases():
            if name in raw:
                return "companion:" + name
        if any(group in raw for group in ("全員", "みんな")):
            return "companion:全員"
        return None

    def requested_companions(self, raw):
        """Extract requested participants without generating or assigning dialogue."""
        roster = self.companion_names()
        if any(group in raw for group in ("全員", "みんな")):
            return roster
        positions = [(raw.find(name), name) for name in roster if name in raw]
        return [name for _position, name in sorted(positions)]

    def continues_companion_conversation(self, raw):
        """Recognize explicit conversation-control requests, not dialogue meaning."""
        return any(
            marker in raw
            for marker in ("反応して", "答えて", "続けて", "ツッコんで", "混ざって")
        )



    def surface_phrase_from_raw(self, raw):
        # Extract a likely noun phrase before a Japanese case particle.
        # This is not meant to understand all Japanese. It is only a lightweight bridge
        # for things explicitly mentioned in the current scene text but not registered
        # as formal objects.
        cleaned = raw.strip().replace("？", "").replace("?", "")
        for sep in ["を", "に", "へ", "が", "は"]:
            if sep in cleaned:
                cand = cleaned.split(sep, 1)[0].strip(" 、。,.　")
                if cand:
                    return cand
        return ""

    def surface_target(self, raw, st):
        if st is None:
            return None
        phrase = self.surface_phrase_from_raw(raw)
        if not phrase or len(phrase) < 2:
            return None
        if phrase in self.companion_aliases():
            return None
        loc = self.locs.get(st.location, {})
        configured = loc.get("surface_objects", []) or []
        for x in configured:
            if isinstance(x, dict):
                names = [x.get("name", "")] + list(x.get("aliases", []) or [])
            else:
                names = [str(x)]
            if phrase in [n for n in names if n]:
                return "surface:" + phrase
        scene_text = "。".join([loc.get("intro", ""), loc.get("banter_observation", "")])
        if phrase in scene_text:
            return "surface:" + phrase
        return None

    def surface_sentence(self, surface_name, st):
        loc = self.locs.get(st.location, {})
        configured = loc.get("surface_objects", []) or []
        for x in configured:
            if isinstance(x, dict) and x.get("name") == surface_name:
                return x.get("surface_text") or x.get("text") or ""
        scene_text = "。".join([loc.get("intro", ""), loc.get("banter_observation", "")])
        for part in [p.strip() for p in scene_text.split("。") if p.strip()]:
            if surface_name in part:
                return part + "。"
        return ""

    def inspect_surface_target(self, target_id, st):
        name = str(target_id).split(":", 1)[-1]
        sentence = self.surface_sentence(name, st)
        if sentence:
            fallback = "GM: " + sentence + "\nGM: 特に気になる点は見当たりません。"
            facts = [sentence, "これは正式な手がかり対象ではない。", "新しい手がかりは出ない。"]
        else:
            fallback = "GM: 特に変わった点は見当たりません。"
            facts = ["正式な手がかり対象ではない。", "新しい手がかりは出ない。"]
        packet = {
            "commentary_type": "surface_inspect_no_reveal",
            "target": name,
            "current_location": self.locs.get(st.location, {}).get("name", "現在地"),
            "facts": facts,
            "style_goal": "描写中の小物を軽く確認したが、特に何もない感じをGM口調で返す。含みを持たせない。",
        }
        text = self.llm_gm_commentary(packet, fallback)
        return text.splitlines(), {"status": "fail", "category": "surface_inspect"}, []

    def visible_object_ids(self, st):
        if st is None:
            return set()
        return set(self.locs.get(st.location, {}).get("visible_objects", []) or [])

    def object_visible_here(self, object_id, st):
        return object_id in self.objects and object_id in self.visible_object_ids(st)

    def target(self, raw, action_type="inspect", st=None):
        if action_type == "consult":
            return self.companion_target(raw)
        candidates = []
        goal_targets = self.goal_targets()
        alias_iter = getattr(self, "alias_entries", None)
        if alias_iter is None:
            alias_iter = list(getattr(self, "alias", {}).items())
        object_scoped = st is not None and action_type in {"inspect", "skill_check"}
        visible_objects = self.visible_object_ids(st) if object_scoped else set()
        if self.debug and object_scoped:
            print(f"[ObjectScope] location={st.location} visible={json.dumps(sorted(visible_objects), ensure_ascii=False)}")
        for alias, key in alias_iter:
            if not alias or alias not in raw:
                continue
            kind = self.entity_kind(key)
            if object_scoped and kind == "object" and key not in visible_objects:
                if self.debug:
                    print(f"[TargetRejected] target={key} reason=not_visible_at_current_location")
                continue
            idx = raw.find(alias)
            score = len(alias)
            if st is not None:
                if kind == "object" and key in self.locs[st.location].get("visible_objects", []):
                    score += 30000
                if kind == "npc" and key in self.locs[st.location].get("npcs", []):
                    score += 30000
                if kind == "location" and key in self.locs[st.location].get("exits", []):
                    score += 30000
                if kind == "location" and key == st.location:
                    score += 5000
            if action_type == "move":
                score += 10000 if kind == "location" else -1000
            elif action_type == "ask":
                score += 10000 if kind == "npc" else (1000 if kind == "object" else 0)
            elif action_type == "skill_check":
                score += 10000 if kind == "object" else (5000 if kind == "npc" else 0)
            elif action_type == "resolve_goal":
                score += 20000 if key in goal_targets else 0
                score += 5000 if kind in {"npc", "object"} else 0
            else:
                score += 10000 if kind == "object" else (5000 if kind == "npc" else 0)
            after = raw[idx + len(alias): idx + len(alias) + 1]
            if action_type == "ask" and after in {"に", "へ"}:
                score += 5000
            if action_type in {"inspect", "skill_check", "resolve_goal"} and after in {"を", "に", "へ"}:
                score += 2000
            candidates.append((score, len(alias), -idx, key, alias, kind))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        if self.debug:
            top = candidates[:3]
            print("[TargetCandidates] " + "; ".join(f"{k}/{a}/{kind}/score={score}" for score, _n, _idx, k, a, kind in top))
        return candidates[0][3]

    def refine_action_with_target(self, action_type, target_id):
        kind = self.entity_kind(target_id)
        # Target kind is a strong signal after embedding intent classification.
        # If the selected target is a location, the player most likely wants to move there,
        # even if the intent embedding over-scored resolve_goal or inspect.
        if kind == "location" and action_type not in {"consult"}:
            return "move"
        if action_type == "move" and kind in {"object", "npc"}:
            return "inspect" if kind == "object" else "ask"
        if action_type == "ask" and kind == "object":
            return "inspect"
        return action_type

    def explicit_scene_target(self, raw, st):
        """Return an explicitly named target that is interactable in this scene."""
        if st is None:
            return None
        target_id = self.target(raw, "inspect", st)
        kind = self.entity_kind(target_id)
        if kind == "object" and self.object_visible_here(target_id, st):
            return target_id
        if kind == "npc" and self.npc_present_here(target_id, st):
            return target_id
        if kind == "location" and (
            target_id == st.location
            or target_id in self.locs.get(st.location, {}).get("exits", [])
        ):
            return target_id
        surface = self.surface_target(raw, st)
        return surface if surface else None

    def judge(self, raw, st=None):
        # v2.11.3: target-aware routing plus scene-surface target fallback.
        companion = self.companion_target(raw)
        explicit_target = companion or self.explicit_scene_target(raw, st)
        if explicit_target:
            if self.debug:
                reason_kind = "companion" if str(explicit_target).startswith("companion:") else self.entity_kind(explicit_target)
                print(
                    f"[ActionCheckRoute]\ninput={raw}\ndecision=skipped"
                    f"\nreason=explicit_{reason_kind}_target"
                )
        else:
            action_check = self.match_action_check(raw, st)
            if action_check:
                return {"raw": raw, "action_type": "action_skill_check", "target_id": action_check.get("id"), "intent_mode": "action-check"}
        if companion:
            action_type, mode = self.embedded_action_intent(raw, allowed=["consult", "ask"])
            action_type = "consult" if action_type not in {"consult", "ask"} else action_type
            target_id = companion
        else:
            preliminary_target = explicit_target or self.target(raw, "inspect", st)
            if preliminary_target is None:
                preliminary_target = self.surface_target(raw, st)
            kind = self.entity_kind(preliminary_target)
            if kind == "location" and st is not None and preliminary_target != st.location:
                action_type, mode = "move", "target-kind"
                target_id = preliminary_target
            elif kind == "location":
                action_type, mode = self.embedded_action_intent(raw, allowed=["area_search", "inspect", "move"])
                if action_type == "inspect" and preliminary_target == st.location:
                    action_type = "area_search"
                target_id = None if action_type == "area_search" else preliminary_target
            elif kind == "surface":
                # Scene-surface objects are descriptive objects, not goal targets.
                action_type, mode = self.embedded_action_intent(raw, allowed=["inspect", "area_search"])
                if action_type == "area_search":
                    # If the user named a specific surface thing, inspect it rather than re-search area.
                    action_type = "inspect"
                target_id = preliminary_target
            elif kind == "object":
                action_type, mode = self.embedded_action_intent(raw, allowed=["inspect", "skill_check"])
                target_id = self.target(raw, action_type, st) or preliminary_target
            elif kind == "npc":
                # GOAL_INTENT_OVERRIDE_v2150
                # If this NPC is also a goal target, goal.intent_examples can resolve the action
                # before generic ask/inspect routing. This is data-driven, not a keyword rule.
                goal_hit = self.goal_intent_override(raw, preliminary_target) if preliminary_target in self.goal_targets() else None
                if goal_hit:
                    action_type, mode = goal_hit
                    target_id = preliminary_target
                else:
                    if preliminary_target in self.goal_targets():
                        allowed = ["ask", "resolve_goal", "inspect"]
                    else:
                        allowed = ["ask", "inspect"]
                    action_type, mode = self.embedded_action_intent(raw, allowed=allowed)
                    target_id = self.target(raw, action_type, st) or preliminary_target
            else:
                action_type, mode = self.embedded_action_intent(raw)
                target_id = self.target(raw, action_type, st)
                # A consult requires an explicit companion target. Preserve
                # targetless input as a generic action instead of inventing a search.
                if action_type == "consult" and target_id is None:
                    action_type = "action"
                if action_type == "area_search":
                    target_id = None
                action_type = self.refine_action_with_target(action_type, target_id)
        if self.debug:
            if explicit_target:
                explicit_kind = "companion" if str(explicit_target).startswith("companion:") else self.entity_kind(explicit_target)
                print(
                    f"[ExplicitTargetRoute]\ninput={raw}\ntarget={explicit_target}"
                    f"\nkind={explicit_kind}\naction={action_type}\ndecision=selected"
                )
            print(f"[ActionRoute] input={raw} route={mode} action={action_type} target={target_id}")
        return {"raw": raw, "action_type": action_type, "target_id": target_id, "intent_mode": mode}

    def match_action_check(self, raw, st=None):
        """Find a scenario-defined, non-object action that matches the utterance."""
        location = st.location if st is not None else None
        eligible = []
        for check in self.action_checks:
            required_location = check.get("required_location")
            if not required_location or required_location == location:
                eligible.append(check)

        if self.debug:
            print(f"[ActionChecks]\nlocation={location}\ntotal={len(self.action_checks)}\neligible={len(eligible)}")

        normalized_raw = self.normalize_action_example(raw)
        candidates = []
        for index, check in enumerate(eligible):
            examples = [str(x) for x in check.get("positive_examples", []) if str(x).strip()]
            exact_match = normalized_raw in {self.normalize_action_example(x) for x in examples}
            if exact_match:
                score, score_mode = 1.0, "exact"
            else:
                score, score_mode = self.score_examples(raw, examples)
            threshold = 1.0 if score_mode == "lexical" else float(os.getenv("ACTION_CHECK_EMB_THRESHOLD", "0.78"))
            if self.debug:
                print(
                    f"[ActionCheckCandidate]\nid={check.get('id')}"
                    f"\nrequired_location={check.get('required_location')}"
                    f"\nlocation_match=True\nexact_match={exact_match}"
                    f"\nscore={score:.3f}\nmode={score_mode}"
                )
            if exact_match or score >= threshold:
                candidates.append((score, exact_match, -index, check))

        if candidates:
            selected = max(candidates, key=lambda item: item[:3])[3]
            if self.debug:
                print(f"[ActionCheckRoute]\ninput={raw}\nid={selected.get('id')}\ndecision=selected")
            return selected

        if self.debug:
            location_blocked = bool(self.action_checks) and not eligible
            reason = "location_mismatch" if location_blocked else "no_similarity_match"
            print(f"[ActionCheckRoute]\ninput={raw}\ndecision=no_match\nreason={reason}")
        return None

    @staticmethod
    def normalize_action_example(text):
        """Normalize author-provided examples without adding game-specific words."""
        normalized = unicodedata.normalize("NFKC", str(text)).casefold()
        return re.sub(r"[\s\u3000、。,.!?！？]+", "", normalized)

    def move(self, target_id, st):
        if target_id in self.locs and target_id in self.locs[st.location].get("exits", []):
            st.location = target_id
            return [f"GM: あなたは{self.locs[target_id]['name']}へ向かいます。", "GM: " + self.locs[target_id]["intro"]], {"status": "ok", "category": "move"}, []
        target_name = self.locs.get(target_id, {}).get("name", "そこ")
        cur_name = self.locs.get(st.location, {}).get("name", "ここ")
        exits = [self.locs[e]["name"] for e in self.locs.get(st.location, {}).get("exits", []) if e in self.locs]
        fallback_lines = [f"GM: うーん、{cur_name}から{target_name}へ直接向かうのは難しそうだなぁ。"]
        if exits:
            fallback_lines.append("GM: 今すぐ動けそうなのは、" + "、".join(exits) + "あたりだね。")
        packet = {
            "commentary_type": "move_failed",
            "player_input_kind": "move",
            "current_location": cur_name,
            "target_location": target_name,
            "available_exits": exits,
            "facts": [
                f"現在地は{cur_name}。",
                f"{target_name}へは現在地から直接移動できない。",
            ],
            "style_goal": "TRPGリプレイのGM口調。移動できない理由と、見える範囲の行き先を自然に伝える。",
        }
        text = self.llm_gm_commentary(packet, "\n".join(fallback_lines))
        return text.splitlines(), {"status": "fail", "category": "move"}, []

    def npc_location_ids(self, npc_id):
        """Return possible current/public locations for an NPC.

        Priority:
        1. npc.location / npc.start_location fields, if scenario JSON has them.
        2. locations[].npcs membership, for existing scenarios.
        """
        npc = self.npcs.get(npc_id, {})
        locs = []
        for k in ("location", "start_location", "current_location"):
            v = npc.get(k)
            if isinstance(v, str) and v in self.locs:
                locs.append(v)
        for lid, loc in self.locs.items():
            if npc_id in loc.get("npcs", []) and lid not in locs:
                locs.append(lid)
        return locs

    def npc_is_available_by_state(self, npc_id, st):
        """Return whether an NPC is available at all in the current state.

        This is intentionally fact-based, not semantic.
        Scenario authors may use availability values such as:
        - available / present: normal
        - missing / hidden / unavailable: not directly interactable
        Optional requires_all can later unlock an NPC.
        """
        npc = self.npcs.get(npc_id, {})
        availability = str(npc.get("availability", npc.get("state", "available"))).lower()
        req_all = list(npc.get("requires_all", []) or [])
        if req_all and any(x not in st.discovered for x in req_all):
            return False
        if availability in {"missing", "hidden", "unavailable", "absent"}:
            return False
        return True

    def npc_present_here(self, npc_id, st):
        if npc_id not in self.npcs:
            return True
        if not self.npc_is_available_by_state(npc_id, st):
            return False
        return st.location in self.npc_location_ids(npc_id)

    def npc_absent_notes(self, npc_id, st):
        npc = self.npcs.get(npc_id, {})
        name = npc.get("name", npc_id)
        cur_name = self.locs.get(st.location, {}).get("name", "ここ")
        # Do not automatically reveal hidden locations. Scenario authors can provide a public hint.
        hint = npc.get("location_hint") or npc.get("absent_text") or ""
        if hint:
            return [f"GM: {name}は{cur_name}にはいないみたいだね。{hint}"]
        return [f"GM: {name}は{cur_name}にはいないみたいだね。今ここで直接話を聞くことはできない。"]

    def available(self, did, st):
        d = self.disc[did]
        src = d.get("source", {})
        if src.get("type") == "npc":
            npc_id = src.get("id")
            return self.npc_present_here(npc_id, st)
        if src.get("type") == "object":
            return src.get("id") in self.locs[st.location].get("visible_objects", [])
        return False

    def discoverable_conditions(self, d, st):
        missing_all = []
        if d.get("required_location") and st.location != d.get("required_location"):
            return False, ["location:" + d.get("required_location")], list(d.get("requires_any", [])), False
        req_all = list(d.get("requires_all", d.get("required_discoverables", [])) or [])
        missing_all = sorted(set(req_all) - st.discovered)
        req_any = list(d.get("requires_any", []) or [])
        any_ok = (not req_any) or any(x in st.discovered for x in req_any)
        return (not missing_all and any_ok), missing_all, req_any, any_ok

    def literal_focus_hit(self, raw, examples):
        # v2.10.3: suppress over-reveal for vague ask commands.
        # A generic ask such as "世間話" may still be embedding-close to an NPC clue.
        # If no positive focus phrase is literally present, ask requires a higher score.
        for ex in examples or []:
            ex = str(ex).strip()
            if len(ex) >= 2 and ex in raw:
                return True
        return False

    def gm_comment_for_blocked_discoverable(self, d, it, st, missing_all=None):
        src = d.get("source", {})
        target_id = src.get("id")
        raw = it.get("raw", "")
        cur_name = self.locs.get(st.location, {}).get("name", "現在地")
        if src.get("type") == "npc":
            name = self.npcs.get(target_id, {}).get("name", "相手")
            observation = self.npcs.get(target_id, {}).get("banter_observation", "")
            fallback = f"GM: {name}は少し口をつぐむね。何か知っていそうなんだけど、今の聞き方では話してくれそうにない。"
            packet = {
                "commentary_type": "ask_blocked_or_no_reveal",
                "player_input": raw,
                "current_location": cur_name,
                "npc": name,
                "visible_observation": observation,
                "facts": [f"{name}と会話している。", "この問いでは新しい手がかりは出ない。"],
                "style_goal": "NPCが答えを避ける・言い淀む感じをGM口調で語る。答えや次の正解質問は教えない。",
            }
            return self.llm_gm_commentary(packet, fallback)
        if src.get("type") == "object":
            name = self.objects.get(target_id, {}).get("name", "それ")
            observation = self.objects.get(target_id, {}).get("banter_observation", "")
            if missing_all:
                fallback = f"GM: {name}を確認した。今の確認では、それ以上のことは分からない。"
                facts = [f"{name}を調べている。", "確認できる範囲では追加の観察結果はない。"]
            else:
                fallback = f"GM: {name}を確認した。今の確認では、それ以上のことは分からない。"
                facts = [f"{name}を調べている。", "確認できる範囲では追加の観察結果はない。"]
            packet = {
                "commentary_type": "inspect_blocked_or_no_reveal",
                "player_input": raw,
                "current_location": cur_name,
                "object": name,
                "visible_observation": observation,
                "facts": facts,
                "style_goal": "行動と観察結果だけを中立的なGM口調で語る。情報の重要度や攻略上の価値を評価しない。",
            }
            return self.llm_gm_commentary(packet, fallback)
        fallback = "GM: うーん、今のところはまだ分からないね。"
        return self.llm_gm_commentary({"commentary_type": "no_reveal", "player_input": raw, "facts": ["新しい手がかりは出ない。"]}, fallback)

    def gm_comment_for_no_reveal(self, it, st):
        target_id = it.get("target_id")

        if target_id in self.npcs and it.get("action_type") in {"ask", "inspect", "skill_check"}:
            if not self.npc_present_here(target_id, st):
                return self.npc_absent_notes(target_id, st), {"status": "fail", "category": "npc_absent"}, []
        raw = it.get("raw", "")
        cur_name = self.locs.get(st.location, {}).get("name", "現在地")
        if it.get("action_type") == "ask" and target_id in self.npcs:
            name = self.npcs[target_id].get("name", "相手")
            observation = self.npcs[target_id].get("banter_observation", "")
            fallback = f"GM: {name}は答えてくれるけど、核心には触れようとしないね。"
            packet = {
                "commentary_type": "ask_no_reveal",
                "player_input": raw,
                "current_location": cur_name,
                "npc": name,
                "visible_observation": observation,
                "facts": [f"{name}に話を聞いた。", "新しい手がかりは出ない。"],
                "style_goal": "会話は成立するが核心には触れない感じをGM口調で語る。",
            }
            return self.llm_gm_commentary(packet, fallback)
        if target_id in self.objects:
            name = self.objects[target_id].get("name", "それ")
            observation = self.objects[target_id].get("banter_observation", "")
            fallback = f"GM: {name}を確認した。今の確認では、それ以上のことは分からない。"
            packet = {
                "commentary_type": "inspect_no_reveal",
                "player_input": raw,
                "current_location": cur_name,
                "object": name,
                "visible_observation": observation,
                "facts": [f"{name}を確認した。", "確認できる範囲では追加の観察結果はない。"],
                "style_goal": "行動と観察結果だけを中立的なGM口調で語る。情報価値を評価しない。",
            }
            return self.llm_gm_commentary(packet, fallback)
        fallback = "GM: 今の確認では、それ以上のことは分からない。"
        return self.llm_gm_commentary({"commentary_type": "no_reveal", "player_input": raw, "current_location": cur_name, "facts": ["確認できる範囲では追加の観察結果はない。"]}, fallback)

    def object_not_present_response(self, it, st):
        cur_name = self.locs.get(st.location, {}).get("name", "現在地")
        packet = {
            "commentary_type": "object_not_present",
            "player_input": it.get("raw", ""),
            "current_location": cur_name,
            "facts": ["指定された対象は現在地で調査できない。", "対象の所在地は案内しない。", "新しい手がかりは出ない。"],
            "style_goal": "対象がここでは見当たらないことだけを、簡潔なGM口調で伝える。別の場所や未発見情報は示さない。",
        }
        text = self.llm_gm_commentary(packet, "GM: ここでは、その対象は見当たらないようです。")
        return text.splitlines(), {"status": "fail", "category": "object_not_present"}, []



    def retrieve(self, it, st):
        out = []
        raw = it.get("raw", "")
        target_id = it.get("target_id")
        for d in self.disc.values():
            did = d["id"]

            # NPC_KNOWLEDGE_GUARD_v2130
            try:
                _act = getattr(it, "action", None) if not isinstance(it, dict) else it.get("action")
                _target = getattr(it, "target", None) if not isinstance(it, dict) else it.get("target")
                _cid = did if "did" in locals() else (d.get("id") if "d" in locals() and isinstance(d, dict) else None)
                if _act == "ask" and _target and _cid and not self.npc_can_reveal_topic_aware(_target, _cid, raw if "raw" in locals() else getattr(it, "raw", "")):
                    if getattr(self, "debug_judge", False):
                        print(f"[NpcKnowledge] target={_target} candidate={_cid} decision=blocked")
                    continue
            except Exception:
                pass
            if did in st.discovered:
                continue
            if not self.available(did, st):
                continue
            if d.get("source", {}).get("id") != target_id:
                continue
            cond_ok, missing_all, req_any, any_ok = self.discoverable_conditions(d, st)
            if not cond_ok:
                if self.debug:
                    print(f"[DiscoverableCondition] candidate={did} missing_all={json.dumps(missing_all, ensure_ascii=False)} requires_any={json.dumps(req_any, ensure_ascii=False)} any_ok={any_ok} decision=blocked")
                out.append((d, "blocked_condition", self.gm_comment_for_blocked_discoverable(d, it, st, missing_all)))
                continue
            target_name = self.objects.get(target_id, {}).get("name", "")
            pos_examples = list(d.get("positive_examples", [])) + ([target_name] if target_name else [])
            neg_examples = list(d.get("negative_examples", []))
            pos, pos_mode = self.score_examples(raw, pos_examples)
            neg, neg_mode = self.score_examples(raw, neg_examples) if neg_examples else (0.0, "none")
            mode = "embedding" if pos_mode == "embedding" or neg_mode == "embedding" else "lexical"
            threshold = float(os.getenv("EMB_REVEAL_THRESHOLD", "0.70")) if mode == "embedding" else 1.0
            margin = float(os.getenv("EMB_NEG_MARGIN", "0.02"))
            focus_hit = self.literal_focus_hit(raw, d.get("positive_examples", [])) if hasattr(self, "literal_focus_hit") else True
            blocked = neg > 0 and neg >= (pos - margin)
            if it.get("action_type") == "ask" and mode == "embedding" and not focus_hit:
                ask_threshold = float(os.getenv("ASK_EMB_REVEAL_THRESHOLD", "0.82"))
                if pos < ask_threshold:
                    blocked = True
            decision = "reveal" if pos >= threshold and not blocked else "none"
            if self.debug:
                print(f"[EmbeddingJudge] input: {raw}\n  candidate={did} mode={mode} pos={pos:.3f} neg={neg:.3f} focus={focus_hit} adj={pos:.3f} blocked={blocked} decision={decision}")
            self.last_embedding = {"candidate": did, "pos": pos, "neg": neg, "mode": mode, "decision": decision}
            comment = None if decision == "reveal" else self.gm_comment_for_blocked_discoverable(d, it, st)
            out.append((d, decision, comment))
        return out

    def skill_value(self, skill):
        return int(self.player.get("skills", {}).get(skill, 0))

    def clue_mod(self, skill, st):
        total, parts = 0, []
        for did in sorted(st.discovered):
            v = int(self.disc[did].get("grants_modifier", {}).get(skill, 0))
            if v:
                total += v
                parts.append((did, v))
        return total, parts


    def condition_status(self, cond, st):
        req_all = list(cond.get("requires_all", cond.get("required_discoverables", [])) or [])
        missing = sorted(set(req_all) - st.discovered)
        req_any = list(cond.get("requires_any", []) or [])
        any_ok = (not req_any) or any(x in st.discovered for x in req_any)
        return (not missing and any_ok), missing, req_any, any_ok

    def select_goal_path(self, goal, st):
        paths = goal.get("solution_paths") or []
        if not paths:
            ok, missing, req_any, any_ok = self.condition_status(goal, st)
            return ({"id": goal.get("id", "default")}, ok, missing, req_any, any_ok)
        first_missing, first_req_any, first_any_ok = [], [], True
        for path in paths:
            ok, missing, req_any, any_ok = self.condition_status(path, st)
            if self.debug:
                print("[GoalPath] candidate=" + str(path.get("id", "<unnamed>")) + " missing_all=" + json.dumps(missing, ensure_ascii=False) + " requires_any=" + json.dumps(req_any, ensure_ascii=False) + " any_ok=" + str(any_ok) + " decision=" + ("selected" if ok else "blocked"))
            if ok:
                return path, True, missing, req_any, any_ok
            if not first_missing and not first_req_any:
                first_missing, first_req_any, first_any_ok = missing, req_any, any_ok
        return None, False, first_missing, first_req_any, first_any_ok

    def resolve_goal(self, it, st):
        for g in self.sc.get("goals", []):
            if it.get("target_id") != g.get("target"):
                continue
            if g.get("required_location") and st.location != g.get("required_location"):
                return ["GM: " + g.get("required_location_failure_text", "この方法はここでは実行できません。")], {"status": "fail", "category": "goal_location"}, []
            selected_path, path_ok, missing, req_any, any_ok = self.select_goal_path(g, st)
            if not path_ok:
                lines = []
                if self.debug:
                    lines.append("[GoalCondition] missing_all=" + json.dumps(missing, ensure_ascii=False) + " requires_any=" + json.dumps(req_any, ensure_ascii=False) + " any_ok=" + str(any_ok))
                return lines + ["GM: " + g.get("failure_text", "まだ判断材料が足りません。")], {"status": "fail", "category": "goal"}, []
            lines = []
            if self.debug and selected_path and selected_path.get("id"):
                lines.append("[GoalPath] selected=" + str(selected_path.get("id")))
            chk = g.get("check")
            if chk:
                base = self.roll_dice(chk.get("dice", "2d6"), skill=False)
                skill = chk.get("skill")
                sm = self.skill_value(skill)
                cm, parts = self.clue_mod(skill, st)
                fixed = int(chk.get("modifier", 0))
                total = base + sm + cm + fixed
                diff = int(chk.get("difficulty", 0))
                clue = f" + clue({cm})" if cm else ""
                expression = f"{chk.get('dice','2d6')} + {skill}({sm}){clue}"
                if fixed:
                    expression += f" + modifier({fixed})"
                lines += self.format_skill_check(skill, expression, total, diff)
                if parts:
                    lines.append("補正: " + ", ".join(f"{i}+{v}" for i, v in parts))
                if total < diff:
                    return lines + ["GM: " + chk.get("failure_text", "判定に失敗しました。")], {"status": "fail", "category": "check"}, []
                lines.append("成功")
            ev = (selected_path or {}).get("success_event") or g.get("success_event", {})
            st.location = ev.get("moves_to", st.location)
            st.ended = True
            return lines + ["GM: 条件を満たし、あなたは結論を実行します。", "GM: " + ev.get("text", "目標を達成しました。")], {"status": "success", "category": "goal", "path": (selected_path or {}).get("id")}, [{"type": "goal_success", "path": (selected_path or {}).get("id")}]
        return ["GM: まだその結論に進むには、状況が整っていません。"], {"status": "fail", "category": "goal"}, []

    def run_skill(self, it, st, notes):
        for d in self.disc.values():
            if d["id"] in st.discovered or not self.available(d["id"], st) or d.get("source", {}).get("id") != it.get("target_id") or not d.get("skill_check"):
                continue
            ok, missing_all, req_any, any_ok = self.discoverable_conditions(d, st)
            if not ok:
                if self.debug:
                    print(f"[DiscoverableCondition] candidate={d['id']} missing_all={json.dumps(missing_all, ensure_ascii=False)} requires_any={json.dumps(req_any, ensure_ascii=False)} any_ok={any_ok} decision=blocked")
                notes.append("GM: ここからは、まだ読み取れません。")
                return notes, {"status": "fail", "category": "skill_check"}, []
            chk = d["skill_check"]
            base = self.roll_dice(chk.get("dice", "2d6"), skill=True)
            skill = chk["skill"]
            sm = self.skill_value(skill)
            total = base + sm
            diff = int(chk["difficulty"])
            notes += self.format_skill_check(skill, f"{chk.get('dice','2d6')} + {skill}({sm})", total, diff)
            if total >= diff:
                st.discovered.add(d["id"])
                notes += ["成功", "発見: " + d["public_text"]]
                return notes, {"status": "ok", "category": "skill_check"}, [{"type": "discoverable_revealed", "id": d["id"]}]
            notes += ["失敗", "GM: " + chk.get("failure_text", "まだ読み取れません。")]
            return notes, {"status": "fail", "category": "skill_check"}, []
        notes.append("GM: ここからは、これ以上読み取れません。")
        return notes, {"status": "fail", "category": "skill_check"}, []

    def skill_display_name(self, skill):
        return {
            "investigation": "調査",
            "survival": "生存",
            "persuasion": "説得",
            "athletics": "運動",
            "stealth": "隠密",
        }.get(skill, skill)

    def format_skill_check(self, skill, expression, total, difficulty):
        return [
            f"【{self.skill_display_name(skill)}判定】",
            expression,
            "結果:",
            str(total),
            "難易度:",
            str(difficulty),
        ]

    def apply_action_check_effect(self, effect, st):
        events = []
        destination = effect.get("move_to", effect.get("moves_to"))
        if destination:
            st.location = destination
            events.append({"type": "location_changed", "id": destination})
        if effect.get("delay"):
            events.append({"type": "action_delayed"})
        return events

    def run_action_skill_check(self, it, st):
        check_event = next((x for x in self.action_checks if x.get("id") == it.get("target_id")), None)
        if not check_event:
            return ["GM: その判定は定義されていません。"], {"status": "fail", "category": "action_skill_check"}, []
        check = check_event.get("skill_check", {})
        skill = check.get("skill", "")
        notation = check.get("dice", "2d6")
        base = self.roll_dice(notation, skill=True)
        modifier = self.skill_value(skill)
        total = base + modifier
        difficulty = int(check.get("difficulty", 0))
        success = total >= difficulty
        check_prompt = check_event.get("check_prompt")
        if not isinstance(check_prompt, str) or not check_prompt.strip():
            check_prompt = "この行動が成功するか判定します。"
        lines = ["GM: " + check_prompt.strip()]
        lines += self.format_skill_check(skill, f"{notation} + {skill}({modifier})", total, difficulty)
        lines.append("成功" if success else "失敗")
        text_key = "success_text" if success else "failure_text"
        fallback = "行動に成功しました。" if success else "行動に失敗し、先へ進めません。"
        lines.append("GM: " + check_event.get(text_key, check.get(text_key, fallback)))
        effect_key = "success_effect" if success else "failure_effect"
        events = self.apply_action_check_effect(check_event.get(effect_key, {}) or {}, st)
        return lines, {"status": "ok" if success else "fail", "category": "action_skill_check", "check_id": check_event.get("id")}, events


    def first_revealable_in_area(self, st):
        visible = list(self.locs[st.location].get("visible_objects", []))
        visible += list(self.locs[st.location].get("npcs", []))
        for target_id in visible:
            for d in self.disc.values():
                did = d.get("id")
                if not did or did in st.discovered:
                    continue
                if d.get("skill_check_only"):
                    continue
                if d.get("source", {}).get("id") != target_id:
                    continue
                if not self.available(did, st):
                    continue
                ok, missing_all, req_any, any_ok = self.discoverable_conditions(d, st)
                if ok:
                    return target_id, d
                if self.debug:
                    print(f"[AreaSearchCondition] candidate={did} missing_all={json.dumps(missing_all, ensure_ascii=False)} requires_any={json.dumps(req_any, ensure_ascii=False)} any_ok={any_ok} decision=blocked")
        return None, None

    def area_search(self, it, st):
        loc = self.locs[st.location]
        notes = ["GM: 周囲を見渡し、目につくものを確認します。"]
        names = []
        for oid in loc.get("visible_objects", []):
            if oid in self.objects:
                names.append(self.objects[oid].get("name", oid))
        for nid in loc.get("npcs", []):
            if nid in self.npcs:
                names.append(self.npcs[nid].get("name", nid))
        for x in loc.get("surface_objects", []) or []:
            if isinstance(x, dict):
                n = x.get("name")
            else:
                n = str(x)
            if n:
                names.append(n)
        if names:
            notes.append("GM: 目につくもの: " + "、".join(dict.fromkeys(names)))
        else:
            notes.append("GM: すぐ目につくものはありません。")
        notes.append("GM: 詳しく調べたいものがあれば、対象を指定してください。")
        return notes, {"status": "ok", "category": "area_search"}, []


    def consult_companion(self, it, st):
        name = str(it.get("target_id", "companion:仲間")).split(":", 1)[-1]
        notes = [f"GM: {name}に意見を求めます。"]
        return notes, {"status": "ok", "category": "consult"}, [{"type": "consult", "name": name}]


    # ---- v2.13.0 NPC Knowledge helpers ----
    def npc_by_id(self, npc_id):
        if not npc_id:
            return {}
        # v2.14.1: support both self.scenario and self.sc, and fall back to self.npcs.
        data = getattr(self, "scenario", None) or getattr(self, "sc", {}) or {}
        npcs = data.get("npcs", {}) if isinstance(data, dict) else {}
        if isinstance(npcs, dict):
            item = npcs.get(npc_id) or {}
            return item if isinstance(item, dict) else {}
        if isinstance(npcs, list):
            for n in npcs:
                if isinstance(n, dict) and n.get("id") == npc_id:
                    return n
        # self.npcs may be the normalized NPC dict used by the engine.
        fallback = getattr(self, "npcs", {}) or {}
        if isinstance(fallback, dict):
            item = fallback.get(npc_id) or {}
            return item if isinstance(item, dict) else {}
        return {}

    def npc_display_name(self, npc_id):
        npc = self.npc_by_id(npc_id)
        return npc.get("name") or npc.get("display_name") or npc_id or "その人物"

    def _as_id_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            out = []
            for x in value:
                if isinstance(x, dict):
                    out.append(str(x.get("id") or x.get("clue") or ""))
                else:
                    out.append(str(x))
            return [x for x in out if x]
        if isinstance(value, dict):
            return [str(k) for k, v in value.items() if v]
        return [str(value)]

    def npc_known_clue_ids(self, npc_id):
        npc = self.npc_by_id(npc_id)
        ids = []
        for key in ("knows", "knowledge", "known_clues"):
            ids.extend(self._as_id_list(npc.get(key)))
        topics = npc.get("topics") or npc.get("topic_hints") or {}
        if isinstance(topics, dict):
            for val in topics.values():
                ids.extend(self._as_id_list(val))
        return set(ids)

    def npc_unknown_clue_ids(self, npc_id):
        npc = self.npc_by_id(npc_id)
        ids = []
        for key in ("does_not_know", "unknown_clues"):
            ids.extend(self._as_id_list(npc.get(key)))
        return set(ids)

    def npc_knowledge_declared(self, npc_id):
        npc = self.npc_by_id(npc_id)
        return any(k in npc for k in ("knows", "knowledge", "known_clues", "topics", "topic_hints", "does_not_know", "unknown_clues"))

    def npc_can_reveal(self, npc_id, clue_id):
        if not npc_id or not clue_id:
            return True
        if clue_id in self.npc_unknown_clue_ids(npc_id):
            return False
        if not self.npc_knowledge_declared(npc_id):
            return True
        return clue_id in self.npc_known_clue_ids(npc_id)
    # ---- /v2.13.0 NPC Knowledge helpers ----


    # ---- v2.13.1 NPC Topic Resolution helpers ----
    def npc_topic_hits_all(self, raw):
        """Return topic labels mentioned in raw across all NPC topic maps."""
        raw_s = str(raw or "")
        hits = []
        npcs = self.scenario.get("npcs", {}) if hasattr(self, "scenario") else {}
        vals = npcs.values() if isinstance(npcs, dict) else npcs if isinstance(npcs, list) else []
        for npc in vals:
            if not isinstance(npc, dict):
                continue
            topics = npc.get("topics") or npc.get("topic_hints") or {}
            if isinstance(topics, dict):
                for topic in topics.keys():
                    if topic and str(topic) in raw_s:
                        hits.append(str(topic))
        return sorted(set(hits), key=len, reverse=True)

    def npc_topic_candidate_ids(self, npc_id, raw):
        """Return clue ids allowed by this NPC's matched explicit topics."""
        raw_s = str(raw or "")
        npc = self.npc_by_id(npc_id) if hasattr(self, "npc_by_id") else {}
        topics = npc.get("topics") or npc.get("topic_hints") or {}
        ids = []
        if isinstance(topics, dict):
            for topic, val in topics.items():
                if topic and str(topic) in raw_s:
                    ids.extend(self._as_id_list(val) if hasattr(self, "_as_id_list") else ([val] if isinstance(val, str) else val or []))
        return set(str(x) for x in ids if x)

    def npc_can_reveal_topic_aware(self, npc_id, clue_id, raw):
        """Knowledge guard with explicit topic resolution.

        If the player's utterance contains a known topic label anywhere in the scenario,
        the target NPC may only reveal clues mapped from its own matching topic labels.

        Example:
          村長に青い光のことを聞く
          global topic hit = 青い光
          village_head topics do not map 青い光
          => head_report must not reveal just because village_head knows it.
        """
        if not self.npc_can_reveal(npc_id, clue_id):
            return False
        global_hits = self.npc_topic_hits_all(raw)
        if not global_hits:
            return True
        allowed = self.npc_topic_candidate_ids(npc_id, raw)
        if not allowed:
            return False
        return str(clue_id) in allowed
    # ---- /v2.13.1 NPC Topic Resolution helpers ----


    # ---- v2.14.0 Ask Topic Resolver helpers ----
    def ask_topic_hits_all(self, raw):
        """Return topic labels mentioned in raw across all NPC topic maps.
        This is a GM-note check, not a semantic judgment.
        """
        raw_s = str(raw or "")
        hits = []
        npcs = self.scenario.get("npcs", {}) if hasattr(self, "scenario") else self.sc.get("npcs", {})
        vals = npcs.values() if isinstance(npcs, dict) else npcs if isinstance(npcs, list) else []
        for npc in vals:
            if not isinstance(npc, dict):
                continue
            topics = npc.get("topics") or npc.get("topic_hints") or {}
            if isinstance(topics, dict):
                for topic in topics.keys():
                    if topic and str(topic) in raw_s:
                        hits.append(str(topic))
        return sorted(set(hits), key=len, reverse=True)

    def ask_topic_ids_for_npc(self, npc_id, raw):
        """Return clue ids mapped from topics explicitly mentioned in raw for this NPC."""
        raw_s = str(raw or "")
        npc = self.npc_by_id(npc_id) if hasattr(self, "npc_by_id") else (self.npcs.get(npc_id, {}) if hasattr(self, "npcs") else {})
        topics = npc.get("topics") or npc.get("topic_hints") or {}
        ids = []
        if isinstance(topics, dict):
            for topic, val in topics.items():
                if topic and str(topic) in raw_s:
                    if hasattr(self, "_as_id_list"):
                        ids.extend(self._as_id_list(val))
                    elif isinstance(val, list):
                        ids.extend(str(x) for x in val)
                    elif val:
                        ids.append(str(val))
        return [x for x in ids if x]

    def ask_topic_no_knowledge_lines(self, npc_id, raw):
        name = self.npc_display_name(npc_id) if hasattr(self, "npc_display_name") else self.npcs.get(npc_id, {}).get("name", npc_id)
        hits = self.ask_topic_hits_all(raw)
        topic = hits[0] if hits else "その話"
        return [
            f"GM: {name}に{topic}のことを聞いてみるんだね。",
            f"GM: ただ、{name}はその件については詳しいことを知らないみたいだ。",
        ]

    def resolve_ask_by_topic(self, it, st):
        """Resolve explicit ask topic before embedding candidate retrieval.

        Return (notes, res, ev) if handled, otherwise None.
        If the utterance contains a known topic label somewhere in the scenario,
        the target NPC's topic map becomes authoritative for reveal selection.
        """
        if it.get("action_type") != "ask":
            return None
        npc_id = it.get("target_id")
        if not npc_id or npc_id not in self.npcs:
            return None
        raw = it.get("raw", "")
        global_hits = self.ask_topic_hits_all(raw)
        if not global_hits:
            return None
        topic_ids = self.ask_topic_ids_for_npc(npc_id, raw)
        if not topic_ids:
            return self.ask_topic_no_knowledge_lines(npc_id, raw), {"status": "ok", "category": "no_reveal", "reason": "npc_topic_unknown"}, []

        notes = []
        ev = []
        name = self.npc_display_name(npc_id) if hasattr(self, "npc_display_name") else self.npcs.get(npc_id, {}).get("name", npc_id)
        notes.append(f"GM: {name}に話を聞いてみるんだね。")
        revealed = False
        for cid in topic_ids:
            d = self.disc.get(cid)
            if not d:
                continue
            if cid in st.discovered:
                continue
            if not self.available(cid, st):
                continue
            cond_ok, missing_all, req_any, any_ok = self.discoverable_conditions(d, st)
            if not cond_ok:
                if self.debug:
                    print(f"[AskTopic] candidate={cid} missing_all={json.dumps(missing_all, ensure_ascii=False)} requires_any={json.dumps(req_any, ensure_ascii=False)} any_ok={any_ok} decision=blocked")
                continue
            st.discovered.add(cid)
            notes.append("発見: " + d.get("public_text", cid))
            ev.append({"type": "discoverable_revealed", "id": cid})
            revealed = True
        if revealed:
            return notes, {"status": "ok", "category": "discoverable", "resolver": "ask_topic"}, ev
        notes.append("GM: ただ、今の段階ではそこから新しい手がかりまでは出てこないみたいだね。")
        return notes, {"status": "ok", "category": "no_reveal", "reason": "ask_topic_no_new_reveal"}, []
    # ---- /v2.14.0 Ask Topic Resolver helpers ----

    def resolve(self, it, st):
        if it["action_type"] == "action_skill_check":
            return self.run_action_skill_check(it, st)
        if it["action_type"] == "area_search":
            return self.area_search(it, st)
        if it["action_type"] == "consult":
            return self.consult_companion(it, st)
        if it["action_type"] == "move":
            return self.move(it["target_id"], st)
        if it["action_type"] == "resolve_goal":
            return self.resolve_goal(it, st)
        if str(it.get("target_id")).startswith("surface:"):
            return self.inspect_surface_target(it.get("target_id"), st)
        # ASK_TOPIC_RESOLVER_v2140
        handled = self.resolve_ask_by_topic(it, st)
        if handled is not None:
            return handled

        notes, ev = [], []
        res = {"status": "ok", "category": "action"}
        target_id = it.get("target_id")
        if target_id in self.objects and it.get("action_type") in {"inspect", "skill_check"}:
            if not self.object_visible_here(target_id, st):
                if self.debug:
                    print(f"[TargetRejected] target={target_id} reason=not_visible_at_current_location")
                return self.object_not_present_response(it, st)
        if target_id in self.npcs and it.get("action_type") in {"ask", "inspect", "skill_check"}:
            if not self.npc_present_here(target_id, st):
                return self.npc_absent_notes(target_id, st), {"status": "fail", "category": "npc_absent"}, []
        if target_id in self.objects:
            notes += [f"GM: {self.objects[target_id]['name']}に注意を向けます。", "GM: " + self.objects[target_id]["surface_text"]]
        elif target_id in self.npcs:
            notes.append(f"GM: {self.npcs[target_id]['name']}と会話します。")
        else:
            notes.append("GM: あなたは状況を整理します。")
        if it["action_type"] == "skill_check":
            return self.run_skill(it, st, notes)
        comments = []
        for d, decision, comment in self.retrieve(it, st):
            if decision == "reveal":
                st.discovered.add(d["id"])
                notes.append("発見: " + d["public_text"])
                ev.append({"type": "discoverable_revealed", "id": d["id"]})
                res = {"status": "ok", "category": "discoverable"}
            elif comment:
                comments.append(comment)
        if not ev and comments:
            notes.append(comments[0])
            res = {"status": "fail", "category": "no_reveal"}
        elif not ev and it.get("action_type") in {"ask", "inspect"}:
            notes.append(self.gm_comment_for_no_reveal(it, st))
            res = {"status": "fail", "category": "no_reveal"}
        return notes, res, ev

    def event_revealed_discoverables(self, ev):
        return {e.get("id") for e in (ev or []) if isinstance(e, dict) and e.get("type") == "discoverable_revealed"}

    def target_revealed_this_turn(self, target_id, ev):
        revealed = self.event_revealed_discoverables(ev)
        if not revealed or not target_id:
            return False
        for did in revealed:
            d = self.disc.get(did, {})
            if d.get("source", {}).get("id") == target_id:
                return True
        return False

    def public_revelations_for_target(self, target_id, ev):
        observations = []
        for did in self.event_revealed_discoverables(ev):
            discoverable = self.disc.get(did, {})
            if discoverable.get("source", {}).get("id") == target_id and discoverable.get("public_text"):
                observations.append(discoverable["public_text"])
        return observations

    def official_discovery_texts(self, ev):
        """Return authored public_text for this turn's reveal events, in event order."""
        texts = []
        for event in ev or []:
            if not isinstance(event, dict) or event.get("type") != "discoverable_revealed":
                continue
            public_text = self.disc.get(event.get("id"), {}).get("public_text")
            if isinstance(public_text, str) and public_text.strip():
                texts.append(public_text.strip())
        return texts

    def official_discovery_gm_lines(self, ev):
        """Add only the GM prefix; do not rewrite authored discovery content."""
        return [text if text.startswith("GM:") else "GM: " + text for text in self.official_discovery_texts(ev)]

    def companion_surface_observations(self, target_id):
        """Return only pre-authored, visible material for companion context.

        Formal discoveries remain in the GM's canonical/discovery context. The
        unified model can still read that context; this helper merely avoids
        emphasizing the same conclusion again in the companion sub-packet.
        """
        if target_id in self.objects:
            obj = self.objects[target_id]
            surface = obj.get("surface_banter_observation") or obj.get("surface_text", "")
            return [surface] if surface else []
        if target_id in self.npcs:
            npc = self.npcs[target_id]
            surface = npc.get("surface_banter_observation", "")
            return [surface] if surface else []
        if target_id in self.locs:
            surface = self.locs[target_id].get("surface_banter_observation", "")
            return [surface] if surface else []
        if isinstance(target_id, str) and target_id.startswith("surface:"):
            return ["これは正式な手がかり対象ではない。新しい情報を足さない。"]
        return []

    def packet(self, it, ev, st):
        target_id = it.get("target_id")
        obs = self.companion_surface_observations(target_id)
        if not obs and target_id not in self.objects and target_id not in self.npcs and target_id not in self.locs:
            loc_obs = self.locs.get(st.location, {}).get("surface_banter_observation", "")
            if loc_obs:
                obs.append(loc_obs)
        previous = self.last_companion_turn
        previous_context = previous.get("context", {})
        current_location = self.locs.get(st.location, {}).get("name", st.location)
        previous_location = previous_context.get("location_id")
        location_changed = (
            previous_location != st.location
            if previous_location
            else bool(
                previous_context.get("location")
                and previous_context.get("location") != current_location
            )
        )
        if location_changed and self.conversation_continue_count:
            self.reset_conversation_continuation(
                reason="LocationChanged",
                from_location=previous_location or previous_context.get("location"),
                to_location=st.location,
            )
        # A location change or an inspect of a different object starts a distinct
        # conversational scene. Keep metadata for diagnostics, but do not put the
        # previous scene's wording in the model input as a response template.
        different_inspect_target = (
            it.get("action_type") == "inspect"
            and previous_context.get("target")
            and previous_context.get("target") != target_id
            and previous_context.get("action") != "move"
        )
        include_history = not (location_changed or different_inspect_target)
        history_usage = (
            "場所が変わったため前場面の台詞本文は送らない。"
            if location_changed
            else "現在の場面に自然につながる場合だけ参考にする。コピーや言い換え再出力は禁止。"
        )
        playful_value, playful_reason = self.playful_input_diagnostic(it.get("raw", ""))
        if self.debug_llm or self.debug:
            print(
                "[PlayfulInput]\n"
                f"value={str(playful_value).lower()}\n"
                f"reason={playful_reason}"
            )
        packet = {
            "conversation_diagnostics": {
                "playfulInput": playful_value,
            },
            "current_event": {
                "player_input": it.get("raw", ""),
                "action_type": it.get("action_type"),
                "current_location": current_location,
                "target_id": target_id,
                "revealed_this_turn": sorted(self.event_revealed_discoverables(ev)),
            },
            "current_observations": [x for x in obs if x],
            "recent_companion_lines": {
                "label": "reference_only_past_turn",
                "previous_scene": previous_context,
                "lines": self.recent_companion_lines() if include_history else [],
                "usage": history_usage,
            },
            "safety": [
                "current_observationsにない情報を、知っている事実として言わない。",
                "仮説や冗談は許可するが、未発見情報や正解を根拠として使わず、確定させない。",
                "recent_companion_linesは過去の参考会話であり、世界設定や発見済み情報として扱わない。",
            ],
        }
        requested = self.requested_companions(it.get("raw", ""))
        if requested:
            packet["requested_companions"] = requested
        continue_requested = self.continues_companion_conversation(it.get("raw", ""))
        allow_continue = False
        if continue_requested and not location_changed:
            if self.conversation_continue_count < self.MAX_CONVERSATION_CONTINUE_TURNS:
                self.conversation_continue_count += 1
                allow_continue = True
            else:
                self.reset_conversation_continuation(reason="ContinueExpired")
        elif not continue_requested:
            self.conversation_continue_count = 0
        if allow_continue:
            packet["conversation_context"] = {
                "mode": "continue",
                "requested_companions": requested,
                "previous_companion_lines": self.recent_companion_lines() if include_history else [],
            }
        return packet

    def render_table_turn(self, notes, it, res, ev, st):
        """Unified table-turn renderer.

        Generates GM text and companion reactions in one LLM call, using safe packet() context.
        Preserves structured logs according to DISCOVERY_DISPLAY.
        """
        if os.getenv("TABLE_TURN_RENDER", "1") != "1":
            if hasattr(self, "rewrite_gm_notes"):
                notes = self.rewrite_gm_notes(notes, it, res, ev, st)
            return notes, self.banter(it, res, ev, st)
        if not notes:
            return notes, ""

        gm_indexes, gm_lines = [], []
        for i, line in enumerate(notes):
            if isinstance(line, str) and line.startswith("GM:"):
                gm_indexes.append(i)
                gm_lines.append(line)
        if not gm_lines:
            return notes, self.banter(it, res, ev, st)

        canonical_gm = "\n".join(gm_lines).strip()
        if not canonical_gm:
            return notes, self.banter(it, res, ev, st)

        discovery_display = os.getenv("DISCOVERY_DISPLAY", "gm").strip().lower()
        if discovery_display not in {"gm", "tag", "both"}:
            discovery_display = "gm"
        official_gm_lines = self.official_discovery_gm_lines(ev)

        def fallback_notes_with_official_discoveries(current_notes):
            fallback = list(current_notes)
            if discovery_display == "gm":
                fallback = [
                    line for line in fallback
                    if not (isinstance(line, str) and line.startswith("発見:"))
                ]
            if discovery_display in {"gm", "both"} and official_gm_lines:
                gm_positions = [
                    index for index, line in enumerate(fallback)
                    if isinstance(line, str) and line.startswith("GM:")
                ]
                insert_at = (gm_positions[-1] + 1) if gm_positions else 0
                fallback[insert_at:insert_at] = official_gm_lines
            return fallback

        non_gm_logs = [line for line in notes if not (isinstance(line, str) and line.startswith("GM:"))]
        discovery_logs = [line for line in non_gm_logs if isinstance(line, str) and line.startswith("発見:")]
        preserved_logs = []
        for line in non_gm_logs:
            if isinstance(line, str) and line.startswith("発見:"):
                if discovery_display in {"tag", "both"}:
                    preserved_logs.append(line)
            else:
                preserved_logs.append(line)

        safe_packet = self.packet(it, ev, st)
        history_before = dict(self.last_companion_turn)
        self.debug_companion_history("CompanionHistoryBefore", history_before)
        target_id = it.get("target_id")
        target_name = ""
        if target_id in self.objects:
            target_name = self.objects[target_id].get("name", "")
        elif target_id in self.npcs:
            target_name = self.npcs[target_id].get("name", "")
        elif target_id in self.locs:
            target_name = self.locs[target_id].get("name", "")
        elif isinstance(target_id, str):
            target_name = target_id

        packet = {
            "render_type": "table_turn",
            "player_input": it.get("raw", ""),
            "action_type": it.get("action_type"),
            "result_status": res.get("status"),
            "result_category": res.get("category"),
            "current_location": self.locs.get(st.location, {}).get("name", "現在地"),
            "target": target_name,
            "canonical_gm_text": canonical_gm,
            "discovery_display": discovery_display,
            "discovery_log_lines_for_context": discovery_logs,
            "preserved_log_lines_not_to_generate": preserved_logs,
            "safe_banter_packet": safe_packet,
            "event_types": [e.get("type") for e in ev],
            "instructions": [
                "canonical_gm_textの意味と情報量を保ってGM口調に整える。",
                "preserved_log_lines_not_to_generate は既に別途表示されるので、絶対に出力しない。",
                "未発見の手がかり・真相・正解ルートを追加しない。",
                "current_observationsは仲間が目にしている表層情報であり、発言対象にする義務はない。",
                "仲間発言は0〜5行。場面への独立コメントだけでなく、自然なら仲間への働きかけと短い応答を選べる。",
                "仲間はsafe_banter_packet.safetyを最優先し、GMが出していない新情報を言わない。",
                "GM本文は確定事実と中立的な観察だけを扱い、未定義の重要度評価や攻略評価を加えない。",
            ],
        }

        system_prompt = (
            "あなたはチャット型TRPGリプレイの1ターン描写を整えるレンダラー。\n"
            "【出力契約・必須】GM行と仲間行だけを出力し、最初は必ず『GM:』。"
            "発見・判定・結果・補正・debug、JSON、箇条書き、コードブロックは禁止。仲間発言は0〜5行。\n\n"
            "【GMの責務・必須】canonical_gm_textに沿い、行動、観察可能な状態、場面を自然な卓上GM口調で描写する。"
            "正式発見は後続のGM行で原文表示されるため詳しく反復しない。"
            "Canonical外の犯人、動機、意図、背景事情、重要度評価、攻略上の価値、正解行動を追加しない。"
            "仲間への直接の依頼では本人の反応をGM本文で先回りしない。\n\n"
            "【仲間への入力・必須】safe_banter_packetを情報境界とする。"
            "result_category が no_reveal / surface_inspect / object_not_present / npc_absent / move なら重要な手掛かりがあるふりをしない。\n\n"
            + self.companion_banter_prompt()
        )
        body = {
            "model": self.llm_model(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
            ],
            "temperature": self.table_turn_temperature(),
            "max_tokens": int(os.getenv("TABLE_TURN_MAX_TOKENS", "360")),
        }
        if self.debug_llm:
            print("[TABLE_TURN_TEMPERATURE]", body["temperature"])
            print("[TABLE_PROMPT_USER_INPUT]\n" + str(it.get("raw", "")))
            print("[TABLE_PROMPT_ACTION]\n" + str(it.get("action_type", "")))
            print("[TABLE_TURN_SYSTEM]\n" + system_prompt)
            print("[TABLE_TURN_USER]\n" + body["messages"][1]["content"])

        if os.getenv("LLM_PROVIDER", "llama_cpp") == "none":
            if hasattr(self, "rewrite_gm_notes"):
                notes = self.rewrite_gm_notes(notes, it, res, ev, st)
            self.last_companion_turn = {}
            return fallback_notes_with_official_discoveries(notes), ""

        base = self.llm_base_url()
        urls = [base + "/chat/completions"] if base.endswith("/v1") else [base + "/chat/completions", base + "/v1/chat/completions"]
        out = ""
        for url in urls:
            try:
                data = self.post_json(url, body, int(os.getenv("TABLE_TURN_TIMEOUT", os.getenv("GM_LINE_REWRITE_TIMEOUT", "60"))), "TABLE_TURN")
                choice = data.get("choices", [{}])[0]
                out = choice.get("message", {}).get("content") or choice.get("text", "") or ""
                out = out.strip()
                break
            except Exception as e:
                if self.debug_llm or self.debug:
                    print("[TABLE_TURN_ERROR]", type(e).__name__, str(e))

        if not out or "```" in out or out.lstrip().startswith("{"):
            if hasattr(self, "rewrite_gm_notes"):
                notes = self.rewrite_gm_notes(notes, it, res, ev, st)
            self.last_companion_turn = {}
            self.debug_companion_history("CompanionHistoryAfter")
            self.debug_companion_history("CompanionHistoryAction", action="clear", reason="table renderer returned empty or invalid output")
            return fallback_notes_with_official_discoveries(notes), ""
        if "発見:" in out or "判定:" in out or "結果:" in out or "補正:" in out or "[" in out:
            if hasattr(self, "rewrite_gm_notes"):
                notes = self.rewrite_gm_notes(notes, it, res, ev, st)
            self.last_companion_turn = {}
            self.debug_companion_history("CompanionHistoryAfter")
            self.debug_companion_history("CompanionHistoryAction", action="clear", reason="table renderer returned forbidden labels")
            return fallback_notes_with_official_discoveries(notes), ""
        if not out.startswith("GM:"):
            out = "GM: " + out
        if self.debug:
            print("[TABLE_TURN_RAW]", repr(out))

        rendered_lines = [x.strip() for x in out.splitlines() if x.strip()]
        companion_prefixes = tuple(self.companion_names())
        gm_rendered, companion_rendered = [], []
        for line in rendered_lines:
            if line.startswith(companion_prefixes):
                companion_rendered.append(line)
            else:
                gm_rendered.append(line)
        if not gm_rendered:
            gm_rendered = [rendered_lines[0]] if rendered_lines else gm_lines
            companion_rendered = rendered_lines[1:] if len(rendered_lines) > 1 else []

        new_notes = list(notes)
        first = gm_indexes[0]
        for idx in reversed(gm_indexes[1:]):
            new_notes.pop(idx)
        new_notes[first:first + 1] = gm_rendered

        if discovery_display == "gm":
            new_notes = [line for line in new_notes if not (isinstance(line, str) and line.startswith("発見:"))]

        insert_at = first + len(gm_rendered)
        if discovery_display in {"gm", "both"} and official_gm_lines:
            new_notes[insert_at:insert_at] = official_gm_lines
            insert_at += len(official_gm_lines)
        while insert_at < len(new_notes):
            line = new_notes[insert_at]
            if isinstance(line, str) and line.startswith(("発見:", "判定:", "結果:", "補正:", "[")):
                insert_at += 1
                continue
            break
        if companion_rendered:
            new_notes[insert_at:insert_at] = companion_rendered

        self.last_table_turn = {"canonical_gm": canonical_gm, "output": out, "packet": packet}
        self.observe_companion_turn(companion_rendered, it)
        self.remember_companion_turn(companion_rendered, it, st)
        self.debug_companion_history("CompanionHistoryAfter")
        self.debug_companion_history(
            "CompanionHistoryAction",
            action="save" if companion_rendered else "clear",
            reason="saved current response companion lines" if companion_rendered else "current response had no companion lines",
        )
        return new_notes, ""

    def banter(self, it, res, ev, st):
        if res.get("status") == "fail" and res.get("category") in {"goal", "goal_location", "check", "skill_check", "move"}:
            self.last_companion_turn = {}
            return ""
        if res.get("status") == "success" and res.get("category") == "goal" and os.getenv("BANTER_ON_GOAL_SUCCESS", "0") != "1":
            self.last_companion_turn = {}
            return ""
        packet = self.packet(it, ev, st)
        out = self.llm_chat(packet)
        self.last_banter = {"output": out, "safe_packet": packet}
        self.observe_companion_turn(out.splitlines(), it)
        self.remember_companion_turn(out.splitlines(), it, st)
        return out if out and "```" not in out else ""


def normalize_output_notes(notes):
    """Last-resort output sanitizer.

    Prevent print("\n".join(notes)) from crashing if some branch accidentally
    returns a tuple/list instead of a string.
    """
    out = []
    for x in notes:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, (list, tuple)):
            out.append(" ".join(str(y) for y in x))
        else:
            out.append(str(x))
    return out


def load_script(path):
    return [x.strip() for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario-dir", default="scenario_lighthouse")
    ap.add_argument("--script")
    ap.add_argument("--debug-judge", action="store_true")
    ap.add_argument("--debug-llm", action="store_true")
    ap.add_argument("--debug-embedding", action="store_true")
    ap.add_argument("--debug-all", action="store_true")
    ap.add_argument("--dice-total", type=int)
    ap.add_argument("--skill-dice-total", type=int)
    ap.add_argument("--dice-seed", type=int)
    args = ap.parse_args()
    dbg_judge = args.debug_judge or args.debug_all
    dbg_llm = args.debug_llm or args.debug_all
    dbg_emb = args.debug_embedding or args.debug_all
    game = Game(args.scenario_dir, dbg_judge, dbg_llm, dbg_emb, args.dice_total, args.skill_dice_total, args.dice_seed)
    st = State(game.sc["opening_scene"])
    print("チャット型TTRPG GM MVP " + VERSION)
    print("LLM:", game.llm_desc())
    print("Embedding:", game.emb_desc())
    print("Player Skills:", json.dumps(game.player.get("skills", {}), ensure_ascii=False))
    print()
    print("\n".join(game.sc["opening"]))
    print("\n※ 補助: clues / action / embedding / banter / events / quit")
    script = load_script(args.script) if args.script else None
    idx = 0
    while not st.ended:
        if script is not None:
            if idx >= len(script):
                break
            raw = script[idx]
            idx += 1
            print(f"\nPL> {raw}")
        else:
            raw = input("\nPL> ").strip()
        it = game.judge(raw, st)
        notes, res, ev = game.resolve(it, st)
        game.last_result = res
        notes, b = game.render_table_turn(notes, it, res, ev, st)
        notes = normalize_output_notes(notes)
        print("\n" + "\n".join(notes) + (("\n" + b) if b else ""))
    if st.ended:
        print("\nセッション終了。")
    game.print_conversation_stats()


if __name__ == "__main__":
    main()
