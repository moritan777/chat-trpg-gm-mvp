# 消えた灯台守 v2.15.0

中規模汎用確認用シナリオです。証言ルート、物証ルート、灯台設備ルートの3系統で、8〜9ロケーション規模の探索を検証します。

この版では v2.14.1 のNPC所在地・知識・話題に加え、v2.15.0 の Goal Intent Examples を追加しています。

```scenario-json
{
  "title": "消えた灯台守",
  "opening_scene": "harbor",
  "opening": [
    "GM: 嵐が去った翌朝、岬の村は重い霧に包まれています。",
    "GM: この村の主な場所は次のようになっています。",
    "GM: 港\n├ 酒場\n├ 倉庫\n└ 岬の道\n      ├ 灯台\n      └ 岩場の海岸\n             └ 海蝕洞（干潮時のみ）",
    "GM: 調査を進める中で、新しい場所や情報が見つかるかもしれません。",
    "GM: 夜明け前に灯台の灯が消え、そのまま灯台守のユアンが行方不明になりました。",
    "村長: 『灯が消えたのは初めてだ。船が一隻、危うく岩礁に乗り上げるところだった』",
    "漁師: 『昨夜、岬の下で妙な明かりを見た。灯台の灯とは違う、低い青い光だった』",
    "GM: 港には濡れたロープと潮の匂いが残っています。さて、どうしますか？"
  ],
  "player": {
    "skills": {
      "investigation": 2,
      "survival": 1,
      "persuasion": 1,
      "athletics": 1,
      "stealth": 1
    }
  },
  "action_checks": [
    {
      "id": "climb_cliff",
      "required_location": "cliff_path",
      "positive_examples": [
        "崖を登る",
        "岩を登る",
        "よじ登る"
      ],
      "skill_check": {
        "skill": "survival",
        "dice": "2d6",
        "difficulty": 8
      },
      "success_text": "安全な足場を見つけ、灯台入口まで登り切りました。",
      "failure_text": "足場が崩れ、岬の道で立ち止まります。",
      "success_effect": {
        "move_to": "lighthouse_entrance"
      },
      "failure_effect": {
        "delay": true
      }
    }
  ],
  "locations": [
    {
      "id": "harbor",
      "name": "港",
      "aliases": [
        "港",
        "港町",
        "村",
        "村へ",
        "村に戻る",
        "港へ戻る"
      ],
      "intro": "小さな港。桟橋には濡れたロープと潮汐表が残されている。",
      "banter_observation": "港の水面はまだ荒れており、霧が低く漂っている。",
      "npcs": [
        "village_head"
      ],
      "visible_objects": [
        "tide_log"
      ],
      "exits": [
        "tavern",
        "warehouse",
        "cliff_path"
      ],
      "surface_banter_observation": "港には霧が低く漂い、桟橋はまだ濡れている。"
    },
    {
      "id": "tavern",
      "name": "酒場",
      "aliases": [
        "酒場"
      ],
      "intro": "嵐の夜を過ごした漁師たちが集まる酒場。窓は潮で白く曇っている。",
      "banter_observation": "酒場の客は、昨夜の灯台の話になると声を落とす。",
      "npcs": [
        "fisherman"
      ],
      "visible_objects": [
        "tavern_note"
      ],
      "exits": [
        "harbor"
      ],
      "surface_banter_observation": "酒場には嵐明けの湿った空気が残り、客たちの声はやや低い。"
    },
    {
      "id": "warehouse",
      "name": "倉庫",
      "aliases": [
        "倉庫",
        "港の倉庫"
      ],
      "intro": "漁具と荷箱が積まれた倉庫。奥に濡れた荷箱と古い航路図が置かれている。",
      "banter_observation": "荷箱の一部だけが新しく濡れている。",
      "npcs": [],
      "visible_objects": [
        "marked_crate",
        "old_chart"
      ],
      "exits": [
        "harbor"
      ],
      "surface_banter_observation": "倉庫には漁具と荷箱が積まれ、床の一部が湿っている。"
    },
    {
      "id": "cliff_path",
      "name": "岬の道",
      "aliases": [
        "岬",
        "岬の道",
        "崖道"
      ],
      "intro": "港から灯台へ続く細い崖道。嵐で崩れた石が散っている。",
      "banter_observation": "崖道には灯台へ向かう足跡と戻る足跡が入り混じっている。",
      "npcs": [],
      "visible_objects": [
        "broken_lantern",
        "cliff_footprints"
      ],
      "exits": [
        "harbor",
        "lighthouse_entrance",
        "rocky_shore"
      ],
      "surface_banter_observation": "崖道には泥が残り、足跡がいくつも入り混じっている。"
    },
    {
      "id": "lighthouse_entrance",
      "name": "灯台入口",
      "aliases": [
        "灯台入口",
        "灯台"
      ],
      "intro": "灯台の重い扉は半開きになっている。床に赤黒い染みがある。",
      "banter_observation": "扉の内側には、急いで閉めようとしたような傷が残っている。",
      "npcs": [
        "assistant"
      ],
      "visible_objects": [
        "blood_stain",
        "rope_marks"
      ],
      "exits": [
        "cliff_path",
        "light_room"
      ],
      "surface_banter_observation": "灯台入口の扉は半開きで、床には赤黒い染みが見える。"
    },
    {
      "id": "light_room",
      "name": "灯火室",
      "aliases": [
        "灯火室",
        "上階",
        "灯台上階"
      ],
      "intro": "灯台の上階。大きなレンズと油の供給弁があるが、光は消えている。",
      "banter_observation": "レンズはわずかにずれ、油の匂いが薄い。",
      "npcs": [],
      "visible_objects": [
        "lighthouse_lens",
        "oil_valve"
      ],
      "exits": [
        "lighthouse_entrance"
      ],
      "surface_banter_observation": "灯火室は薄暗く、大きなレンズと油の供給弁が見える。"
    },
    {
      "id": "rocky_shore",
      "name": "岩場の海岸",
      "aliases": [
        "岩場",
        "海岸",
        "岩場の海岸"
      ],
      "intro": "岬の下の岩場。潮が引き、小さな海蝕洞の入口が見えている。",
      "banter_observation": "岩場には昨夜の高波の跡が残っている。",
      "npcs": [
        "boy"
      ],
      "visible_objects": [
        "torn_coat",
        "signal_whistle"
      ],
      "exits": [
        "cliff_path",
        "fisher_hut",
        "sea_cave"
      ],
      "surface_banter_observation": "岩場には高波の跡が残り、潮の匂いが強い。"
    },
    {
      "id": "fisher_hut",
      "name": "漁師小屋",
      "aliases": [
        "漁師小屋",
        "小屋"
      ],
      "intro": "古い漁師小屋。網と古い浮きが壁にかかっている。",
      "banter_observation": "小屋の窓から海蝕洞の入口が見える。",
      "npcs": [],
      "visible_objects": [
        "old_net"
      ],
      "exits": [
        "rocky_shore"
      ],
      "surface_banter_observation": "漁師小屋には古い網や浮きが掛かっている。"
    },
    {
      "id": "sea_cave",
      "name": "海蝕洞",
      "aliases": [
        "海蝕洞",
        "洞窟",
        "海の洞窟",
        "海食洞",
        "海食洞へ",
        "海食洞に移動する"
      ],
      "intro": "潮が引いた時だけ入れる洞窟。奥には濡れた荷箱と小舟が見えるが、その先は暗く見通せない。",
      "banter_observation": "洞窟の奥からかすかな物音と滴る水音が聞こえる。",
      "npcs": [
        "keeper"
      ],
      "visible_objects": [
        "cave_crates",
        "cave_boat"
      ],
      "exits": [
        "rocky_shore"
      ],
      "surface_banter_observation": "海蝕洞の奥は暗く、水音が反響している。"
    }
  ],
  "npcs": [
    {
      "id": "village_head",
      "name": "村長",
      "aliases": [
        "村長"
      ],
      "banter_observation": "村長は灯台の灯が消えたことを強く恐れている。",
      "location": "harbor",
      "availability": "available",
      "location_hint": "港にいるはずだ。",
      "knows": [
        "head_report"
      ],
      "does_not_know": [
        "fisherman_blue_light",
        "boy_cave_hint",
        "assistant_key_story",
        "assistant_secret",
        "smuggler_route_analysis"
      ],
      "topics": {
        "人影": [
          "head_report"
        ],
        "倉庫": [
          "head_report"
        ],
        "灯台": [
          "head_report"
        ],
        "灯台守": [
          "head_report"
        ],
        "何が起きた": [
          "head_report"
        ]
      }
    },
    {
      "id": "fisherman",
      "name": "漁師バロ",
      "aliases": [
        "漁師",
        "バロ"
      ],
      "banter_observation": "漁師は昨夜の青い光を気にしている。",
      "location": "tavern",
      "availability": "available",
      "location_hint": "酒場にいるはずだ。",
      "knows": [
        "fisherman_blue_light"
      ],
      "does_not_know": [
        "head_report",
        "boy_cave_hint",
        "assistant_key_story",
        "assistant_secret",
        "smuggler_route_analysis"
      ],
      "topics": {
        "青い光": [
          "fisherman_blue_light"
        ],
        "昨夜の光": [
          "fisherman_blue_light"
        ],
        "低い光": [
          "fisherman_blue_light"
        ],
        "岬の下": [
          "fisherman_blue_light"
        ]
      }
    },
    {
      "id": "boy",
      "name": "少年ノア",
      "aliases": [
        "少年",
        "ノア"
      ],
      "banter_observation": "少年は岩場の方をちらちら見ている。",
      "location": "rocky_shore",
      "availability": "available",
      "location_hint": "岩場の海岸にいるはずだ。",
      "knows": [
        "boy_cave_hint"
      ],
      "does_not_know": [
        "head_report",
        "fisherman_blue_light",
        "assistant_key_story",
        "assistant_secret",
        "smuggler_route_analysis"
      ],
      "topics": {
        "洞窟": [
          "boy_cave_hint"
        ],
        "海蝕洞": [
          "boy_cave_hint"
        ],
        "海食洞": [
          "boy_cave_hint"
        ],
        "荷箱": [
          "boy_cave_hint"
        ],
        "岩場": [
          "boy_cave_hint"
        ]
      }
    },
    {
      "id": "assistant",
      "name": "灯台助手レナ",
      "aliases": [
        "助手",
        "レナ",
        "灯台助手"
      ],
      "banter_observation": "助手は鍵束を握りしめている。",
      "location": "lighthouse_entrance",
      "availability": "available",
      "location_hint": "灯台入口にいるはずだ。",
      "knows": [
        "assistant_key_story",
        "assistant_secret"
      ],
      "does_not_know": [
        "fisherman_blue_light",
        "boy_cave_hint",
        "head_report",
        "smuggler_route_analysis"
      ],
      "topics": {
        "鍵": [
          "assistant_key_story"
        ],
        "予備鍵": [
          "assistant_key_story"
        ],
        "灯台の鍵": [
          "assistant_key_story"
        ],
        "昨夜の鍵": [
          "assistant_key_story"
        ],
        "本当のこと": [
          "assistant_secret"
        ],
        "隠していること": [
          "assistant_secret"
        ],
        "誰に渡した": [
          "assistant_secret"
        ],
        "倉庫番": [
          "assistant_secret"
        ]
      }
    },
    {
      "id": "keeper",
      "name": "灯台守ユアン",
      "aliases": [
        "灯台守",
        "ユアン",
        "灯台守ユアン"
      ],
      "banter_observation": "灯台守は洞窟の奥で弱く息をしている。",
      "location": "sea_cave",
      "availability": "hidden",
      "narrative_status": "missing_until_found",
      "location_hint": "まだ居場所は分かっていない。",
      "knows": [],
      "does_not_know": [],
      "topics": {}
    }
  ],
  "objects": [
    {
      "id": "tide_log",
      "name": "潮汐表",
      "aliases": [
        "潮汐表",
        "潮の記録",
        "潮見表",
        "潮汐票",
        "潮汐票を見る"
      ],
      "surface_text": "港に置かれた潮汐表。昨夜の干潮時刻に赤い印がつけられている。",
      "banter_observation": "赤い印は海蝕洞へ入れる時間帯を示しているようだ。",
      "surface_banter_observation": "昨夜の干潮時刻に赤い印がついている。"
    },
    {
      "id": "tavern_note",
      "name": "酒場の覚え書き",
      "aliases": [
        "覚え書き",
        "メモ",
        "酒場のメモ"
      ],
      "surface_text": "酒場の壁に、昨夜の見張り当番を書いた紙が貼られている。",
      "banter_observation": "灯台助手の名前だけが薄く滲んでいる。",
      "surface_banter_observation": "見張り当番らしい紙が壁に貼られている。"
    },
    {
      "id": "marked_crate",
      "name": "印付きの荷箱",
      "aliases": [
        "荷箱",
        "印付きの荷箱",
        "濡れた荷箱"
      ],
      "surface_text": "倉庫の奥に、灯台では使わないはずの青い印がついた荷箱がある。",
      "banter_observation": "荷箱の底に海水が染みている。",
      "surface_banter_observation": "青い印のついた濡れた荷箱がある。"
    },
    {
      "id": "old_chart",
      "name": "古い航路図",
      "aliases": [
        "航路図",
        "古い航路図",
        "地図"
      ],
      "surface_text": "岬周辺の岩礁と潮流を示した古い航路図。海蝕洞の近くに手書きの丸がある。",
      "banter_observation": "丸印は灯台の死角に重なっている。",
      "surface_banter_observation": "海蝕洞の近くに手書きの丸がある。"
    },
    {
      "id": "broken_lantern",
      "name": "割れたランタン",
      "aliases": [
        "ランタン",
        "割れたランタン"
      ],
      "surface_text": "崖道に割れたランタンが落ちている。灯台守が使っていたものに似ている。",
      "banter_observation": "ガラス片は灯台ではなく海岸側へ散っている。",
      "surface_banter_observation": "割れたランタンとガラス片が崖道に散っている。"
    },
    {
      "id": "cliff_footprints",
      "name": "崖道の足跡",
      "aliases": [
        "足跡",
        "崖道の足跡",
        "靴跡"
      ],
      "surface_text": "泥に残る足跡。灯台へ向かうものと海岸へ下るものが混じっている。",
      "banter_observation": "海岸へ下る足跡の一つは深く、誰かを支えたようにも見える。",
      "surface_banter_observation": "足跡が入り混じっていて、まだ判別しづらい。"
    },
    {
      "id": "blood_stain",
      "name": "赤黒い染み",
      "aliases": [
        "血痕",
        "赤黒い染み",
        "染み"
      ],
      "surface_text": "灯台入口の床に赤黒い染みがある。嵐の雨で薄く広がっている。",
      "banter_observation": "染みは入口から外へ引きずられたように続いている。",
      "surface_banter_observation": "赤黒い染みが薄く広がっている。"
    },
    {
      "id": "rope_marks",
      "name": "ロープ跡",
      "aliases": [
        "ロープ跡",
        "ロープ",
        "擦れ跡"
      ],
      "surface_text": "灯台入口の手すりに、新しいロープの擦れ跡が残っている。",
      "banter_observation": "ロープ跡は灯台から海岸側へ向かっている。",
      "surface_banter_observation": "手すりに新しいロープの擦れ跡が残っている。"
    },
    {
      "id": "lighthouse_lens",
      "name": "灯台レンズ",
      "aliases": [
        "レンズ",
        "灯台レンズ",
        "光源"
      ],
      "surface_text": "大きなレンズがわずかにずれている。固定金具が緩んでいる。",
      "banter_observation": "ずれた角度では、海蝕洞側を照らせない。",
      "surface_banter_observation": "大きなレンズがわずかにずれている。"
    },
    {
      "id": "oil_valve",
      "name": "油の供給弁",
      "aliases": [
        "供給弁",
        "油の弁",
        "油の供給弁"
      ],
      "surface_text": "灯火用の油の供給弁が閉じられている。指で拭った新しい跡がある。",
      "banter_observation": "弁の周囲だけ油が新しく拭き取られている。",
      "surface_banter_observation": "油の供給弁が閉じられ、触れられた跡がある。"
    },
    {
      "id": "torn_coat",
      "name": "破れた外套",
      "aliases": [
        "外套",
        "破れた外套",
        "布切れ"
      ],
      "surface_text": "岩場に破れた外套の端が引っかかっている。灯台守のものに似ている。",
      "banter_observation": "布は新しく裂け、海水を含んで重くなっている。",
      "surface_banter_observation": "破れた外套の端が岩場に引っかかっている。"
    },
    {
      "id": "signal_whistle",
      "name": "信号笛",
      "aliases": [
        "笛",
        "信号笛"
      ],
      "surface_text": "岩場の隙間に小さな信号笛が落ちている。灯台守が緊急時に使うものだ。",
      "banter_observation": "笛の中には砂が詰まっているが、まだ使えそうだ。",
      "surface_banter_observation": "小さな信号笛が岩場の隙間に落ちている。"
    },
    {
      "id": "old_net",
      "name": "古い網",
      "aliases": [
        "網",
        "古い網"
      ],
      "surface_text": "漁師小屋の古い網。ほつれ方が海蝕洞の荷箱を縛る縄と似ている。",
      "banter_observation": "網の結び方は港の漁師がよく使うものだ。",
      "surface_banter_observation": "古い網が壁に掛かっている。"
    },
    {
      "id": "cave_crates",
      "name": "洞窟の荷箱",
      "aliases": [
        "洞窟の荷箱",
        "隠し荷箱",
        "荷箱"
      ],
      "surface_text": "洞窟の奥に青い印の荷箱が積まれている。倉庫のものと同じ印だ。",
      "banter_observation": "荷箱は干潮時に運び込まれたように整然と並んでいる。",
      "surface_banter_observation": "青い印の荷箱が洞窟の奥に積まれている。"
    },
    {
      "id": "cave_boat",
      "name": "小舟",
      "aliases": [
        "小舟",
        "舟",
        "隠し舟"
      ],
      "surface_text": "洞窟の奥に小舟が隠されている。船底に新しい擦り傷がある。",
      "banter_observation": "小舟は灯台の死角を通るために使われたようだ。",
      "surface_banter_observation": "小舟が洞窟の奥に隠されている。"
    }
  ],
  "discoverables": [
    {
      "id": "head_report",
      "source": {
        "type": "npc",
        "id": "village_head"
      },
      "positive_examples": [
        "灯台守のこと",
        "灯台が消えた",
        "村長に聞く",
        "何が起きた"
      ],
      "negative_examples": [],
      "public_text": "村長は、灯台の灯が消える直前に港の倉庫で人影を見たと話した。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "fisherman_blue_light",
      "source": {
        "type": "npc",
        "id": "fisherman"
      },
      "positive_examples": [
        "青い光",
        "最後の明かり",
        "昨夜の光",
        "漁師に聞く"
      ],
      "negative_examples": [],
      "public_text": "漁師バロは、昨夜の灯台消灯直後、岬の下で低い青い光を見たと証言した。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "boy_cave_hint",
      "source": {
        "type": "npc",
        "id": "boy"
      },
      "positive_examples": [
        "洞窟",
        "海蝕洞",
        "岩場で見た",
        "少年に聞く"
      ],
      "negative_examples": [],
      "public_text": "少年ノアは、嵐の前に海蝕洞の方へ荷箱を運ぶ影を見たと話した。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "assistant_key_story",
      "source": {
        "type": "npc",
        "id": "assistant"
      },
      "positive_examples": [
        "鍵",
        "灯台の鍵",
        "助手に聞く",
        "昨夜の鍵"
      ],
      "negative_examples": [],
      "public_text": "助手レナは、昨夜だけ灯台の予備鍵が一時的に見当たらなかったと話した。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "assistant_secret",
      "source": {
        "type": "npc",
        "id": "assistant"
      },
      "requires_all": [
        "assistant_key_story",
        "head_report"
      ],
      "positive_examples": [
        "本当のこと",
        "隠していること",
        "誰に渡した",
        "正直に話す"
      ],
      "negative_examples": [],
      "public_text": "レナは、倉庫番に頼まれて短時間だけ予備鍵を貸したと打ち明けた。",
      "grants_modifier": {
        "investigation": 1,
        "persuasion": 1
      }
    },
    {
      "id": "tide_log_cave_time",
      "source": {
        "type": "object",
        "id": "tide_log"
      },
      "positive_examples": [
        "潮汐表を見る",
        "潮の記録を見る",
        "干潮時刻を見る"
      ],
      "negative_examples": [],
      "public_text": "潮汐表の赤印は、昨夜の干潮時に海蝕洞へ入れることを示していた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "tavern_watch_note",
      "source": {
        "type": "object",
        "id": "tavern_note"
      },
      "positive_examples": [
        "メモを見る",
        "覚え書きを見る",
        "見張り当番を見る"
      ],
      "negative_examples": [],
      "public_text": "覚え書きでは、灯台助手レナが昨夜は非番だったはずだと分かった。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "crate_blue_mark",
      "source": {
        "type": "object",
        "id": "marked_crate"
      },
      "positive_examples": [
        "荷箱を見る",
        "印付きの荷箱を見る",
        "青い印を見る"
      ],
      "negative_examples": [],
      "public_text": "倉庫の荷箱には、海蝕洞で使われる密輸印と同じ青い印があった。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "smuggler_route_analysis",
      "source": {
        "type": "object",
        "id": "old_chart"
      },
      "requires_all": [
        "tide_log_cave_time",
        "crate_blue_mark"
      ],
      "positive_examples": [
        "航路図を解析する",
        "航路図を読む",
        "海蝕洞への航路を読む"
      ],
      "negative_examples": [],
      "public_text": "航路図を解析すると、灯台の死角を通って海蝕洞へ小舟を入れる経路が分かった。",
      "grants_modifier": {
        "investigation": 1
      },
      "skill_check_only": true,
      "skill_check": {
        "skill": "investigation",
        "dice": "2d6",
        "difficulty": 9,
        "failure_text": "航路と潮の関係までは、まだ読み取れません。"
      }
    },
    {
      "id": "broken_lantern_clue",
      "source": {
        "type": "object",
        "id": "broken_lantern"
      },
      "positive_examples": [
        "ランタンを見る",
        "割れたランタンを調べる",
        "ガラス片を見る"
      ],
      "negative_examples": [],
      "public_text": "割れたランタンは灯台守のもので、ガラス片は海岸側へ散っていた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "cliff_tracks_to_shore",
      "source": {
        "type": "object",
        "id": "cliff_footprints"
      },
      "requires_all": [
        "broken_lantern_clue"
      ],
      "positive_examples": [
        "足跡を見る",
        "崖道の足跡を見る",
        "靴跡を追う"
      ],
      "negative_examples": [],
      "public_text": "崖道の足跡は灯台から海岸へ向かい、途中で誰かを支えたように深くなっていた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "blood_drag_clue",
      "source": {
        "type": "object",
        "id": "blood_stain"
      },
      "positive_examples": [
        "血痕を見る",
        "赤黒い染みを見る",
        "染みを調べる"
      ],
      "negative_examples": [],
      "public_text": "血痕は灯台入口から外へ引きずられたように続いていた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "rope_to_shore",
      "source": {
        "type": "object",
        "id": "rope_marks"
      },
      "requires_all": [
        "blood_drag_clue"
      ],
      "positive_examples": [
        "ロープ跡を見る",
        "擦れ跡を見る",
        "ロープを調べる"
      ],
      "negative_examples": [],
      "public_text": "ロープ跡は灯台入口から海岸側へ荷を下ろした痕跡だった。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "lens_misaligned",
      "source": {
        "type": "object",
        "id": "lighthouse_lens"
      },
      "positive_examples": [
        "レンズを見る",
        "灯台レンズを見る",
        "光源を見る"
      ],
      "negative_examples": [],
      "public_text": "灯台レンズは、海蝕洞の入口を照らせない角度にずらされていた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "oil_valve_tampered",
      "source": {
        "type": "object",
        "id": "oil_valve"
      },
      "positive_examples": [
        "供給弁を見る",
        "油の弁を見る",
        "油の供給弁を調べる"
      ],
      "negative_examples": [],
      "public_text": "油の供給弁は人為的に閉じられ、灯が消えるよう細工されていた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "coat_match_keeper",
      "source": {
        "type": "object",
        "id": "torn_coat"
      },
      "requires_all": [
        "cliff_tracks_to_shore"
      ],
      "positive_examples": [
        "外套を見る",
        "破れた外套を見る",
        "布切れを見る"
      ],
      "negative_examples": [],
      "public_text": "破れた外套は灯台守ユアンのものと分かり、彼が岩場まで運ばれた可能性が高まった。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "signal_whistle_clue",
      "source": {
        "type": "object",
        "id": "signal_whistle"
      },
      "positive_examples": [
        "笛を見る",
        "信号笛を見る",
        "笛を調べる"
      ],
      "negative_examples": [],
      "public_text": "信号笛は灯台守の緊急用で、洞窟の方向へ転がっていた。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "net_knot_match",
      "source": {
        "type": "object",
        "id": "old_net"
      },
      "positive_examples": [
        "網を見る",
        "結び目を見る",
        "古い網を調べる"
      ],
      "negative_examples": [],
      "public_text": "古い網の結び方は、密輸荷箱を縛る縄の結び方と一致しそうだった。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "cave_crates_found",
      "source": {
        "type": "object",
        "id": "cave_crates"
      },
      "positive_examples": [
        "荷箱を見る",
        "隠し荷箱を見る",
        "洞窟の荷箱を見る"
      ],
      "negative_examples": [],
      "public_text": "洞窟の荷箱は倉庫の青い印と同じ印で、ここが密輸品の一時置き場だと分かった。",
      "grants_modifier": {
        "investigation": 1
      }
    },
    {
      "id": "cave_boat_route",
      "source": {
        "type": "object",
        "id": "cave_boat"
      },
      "requires_all": [
        "smuggler_route_analysis"
      ],
      "positive_examples": [
        "小舟を見る",
        "隠し舟を見る",
        "舟を調べる"
      ],
      "negative_examples": [],
      "public_text": "小舟の擦り傷は、航路図で読んだ灯台の死角を通る経路と一致していた。",
      "grants_modifier": {
        "investigation": 1
      }
    }
  ],
  "goals": [
    {
      "id": "rescue_keeper",
      "target": "keeper",
      "required_location": "sea_cave",
      "required_location_failure_text": "灯台守を助けるには、まず居場所までたどり着く必要があります。",
      "solution_paths": [
        {
          "id": "testimony_route",
          "requires_all": [
            "head_report",
            "fisherman_blue_light",
            "boy_cave_hint",
            "assistant_secret"
          ],
          "success_event": {
            "text": "証言をつなぎ合わせると、灯台守が海蝕洞へ運ばれた経緯が見えてきます。あなたたちは洞窟の奥でユアンを見つけ、無事に港へ連れ戻しました。"
          }
        },
        {
          "id": "physical_route",
          "requires_all": [
            "broken_lantern_clue",
            "cliff_tracks_to_shore",
            "blood_drag_clue",
            "rope_to_shore",
            "coat_match_keeper",
            "cave_crates_found"
          ],
          "success_event": {
            "text": "割れたランタン、血痕、ロープ跡、外套の切れ端が一本につながります。あなたたちは密輸荷箱の奥で倒れていた灯台守を救出しました。"
          }
        },
        {
          "id": "lighthouse_route",
          "requires_all": [
            "tide_log_cave_time",
            "crate_blue_mark",
            "smuggler_route_analysis",
            "lens_misaligned",
            "oil_valve_tampered",
            "cave_boat_route"
          ],
          "success_event": {
            "text": "灯台の灯を消した細工と潮の経路を読み解き、密輸船が使った海蝕洞へたどり着きます。小舟のそばでユアンを発見し、救助に成功しました。"
          }
        }
      ],
      "failure_text": "灯台守の居場所を突き止めるには、まだ手がかりが足りません。",
      "check": {
        "skill": "investigation",
        "dice": "2d6",
        "difficulty": 10,
        "modifier": 0,
        "failure_text": "状況はつながりかけたが、救助に踏み切るにはまだ危険が残ります。"
      },
      "success_event": {
        "text": "灯台守ユアンを救出しました。"
      },
      "intent_examples": [
        "灯台守を助ける",
        "灯台守を助けて",
        "灯台守ユアンを助ける",
        "ユアンを助ける",
        "ユアンを救出する",
        "灯台守を救出する",
        "灯台守を港へ連れ戻す",
        "ユアンを連れ戻す",
        "倒れている灯台守を助ける",
        "洞窟の奥のユアンを救う"
      ]
    }
  ],
  "tests": {
    "testimony_success": {
      "dice_total": 3,
      "commands": [
        "村長に灯台守のことを聞く",
        "酒場へ行く",
        "漁師に青い光のことを聞く",
        "港へ行く",
        "岬の道へ行く",
        "岩場へ行く",
        "少年に洞窟のことを聞く",
        "岬の道へ行く",
        "灯台入口へ行く",
        "助手に鍵のことを聞く",
        "助手に本当のことを聞く",
        "岬の道へ行く",
        "岩場へ行く",
        "海蝕洞へ行く",
        "灯台守を助けて"
      ],
      "expect": [
        "[GoalPath] selected=testimony_route",
        "セッション終了。"
      ]
    },
    "physical_success": {
      "dice_total": 3,
      "commands": [
        "岬の道へ行く",
        "ランタンを見る",
        "足跡を見る",
        "灯台入口へ行く",
        "血痕を見る",
        "ロープ跡を見る",
        "岬の道へ行く",
        "岩場へ行く",
        "外套を見る",
        "海蝕洞へ行く",
        "荷箱を見る",
        "灯台守を助けて"
      ],
      "expect": [
        "[GoalPath] selected=physical_route",
        "セッション終了。"
      ]
    },
    "lighthouse_success": {
      "dice_total": 3,
      "skill_dice_total": 7,
      "commands": [
        "潮汐表を見る",
        "倉庫へ行く",
        "荷箱を見る",
        "航路図を解析する",
        "港へ行く",
        "岬の道へ行く",
        "灯台入口へ行く",
        "灯火室へ行く",
        "レンズを見る",
        "供給弁を見る",
        "灯台入口へ行く",
        "岬の道へ行く",
        "岩場へ行く",
        "海蝕洞へ行く",
        "小舟を見る",
        "灯台守を助けて"
      ],
      "expect": [
        "[GoalPath] selected=lighthouse_route",
        "セッション終了。"
      ]
    },
    "fail": {
      "commands": [
        "酒場へ行く",
        "漁師に世間話を聞く",
        "港へ行く",
        "灯台守を助けて"
      ],
      "expect": [
        "灯台守を助けるには、まず居場所までたどり着く必要があります。"
      ],
      "expect_not": [
        "発見: 漁師バロは、昨夜の灯台消灯直後"
      ]
    },
    "skill_blocked": {
      "commands": [
        "倉庫へ行く",
        "航路図を解析する"
      ],
      "expect": [
        "ここからは、まだ読み取れません。"
      ]
    },
    "topic_resolution": {
      "commands": [
        "村長に青い光のことを聞く",
        "酒場へ行く",
        "漁師に青い光のことを聞く"
      ],
      "expect": [
        "村長",
        "青い光",
        "漁師"
      ],
      "expect_not": [
        "港の倉庫で人影を見たって話してくれた"
      ]
    }
  },
  "scenario_revision": "v2150_goal_intent_examples_state_expect",
  "meta": {
    "authoring_revision": "v2.15.0",
    "engine_requirements": {
      "npc_presence_guard": "v2.12.1a",
      "surface_public_separation": "v2.12.2b",
      "npc_knowledge": "v2.13.0",
      "ask_topic_resolver": "v2.14.1",
      "goal_intent_examples": "v2.15.0"
    },
    "notes": [
      "NPCの所在地、知識、話題をGMノートとして明示する。",
      "発見条件はdiscoverable側に残し、NPC topics は「何について聞いたか」の解決に使う。"
    ],
    "expectation_policy": "state/log anchors only; avoid LLM narrative wording"
  }
}
```
