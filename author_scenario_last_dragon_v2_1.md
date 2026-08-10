# 最後の竜、空を忘れる v2.1

## シナリオ概要

王国を千年にわたって見守ってきた白銀竜が、突如として辺境の村を襲った。

王命を受けた冒険者たちは、焼かれた村、竜の巡回する峠、古い伝承を守る修道院を巡り、失われた古代文明の施設へ辿り着く。

白銀竜は本当に狂ったのか。なぜ村を焼きながら、村人ではなく地面の何かを探していたのか。青白い信号は何を呼び、竜は何に従っているのか。

## v2.1 改修点

- 事件開始時点の公開事実を `public_case_facts` として明示
- 「竜は何を探しているのか」という中間ミステリーを追加
- 灰の村、風鳴り峠、白銀の遺跡に新しい物証を追加
- NPCを単なる説明役ではなく、討伐派・信仰・名誉などの立場を持つ人物へ調整
- NPCへの明示質問、段階的情報開示、3解決ルートの回帰テストを強化
- 現行エンジンの `[GoalPath]` と `clues` 二段表示を検証するテストを追加
- 王国騎士団長バルガスを追加し、現実的な討伐派の立場を明示
- `vargas_position` と `vargas_knowledge_boundary` を追加

## 想定規模

- ジャンル: SFファンタジー
- Location: 7
- NPC: 8
- Object: 18
- Discoverable: 20
- Goal: 1
- Solution Path: 3
- Tests: 11

## GM向け真相

白銀竜は自然生命ではなく、古代文明が生体組織と人工構造を融合して作った守護個体 `Guardian Unit-01` である。

本来の任務は、天空施設群へ接続する地下管制中枢の守護だった。しかし長い年月によって識別機構が損傷し、本来保護すべき人間を脅威として誤認している。さらに峠の導標が壊れ、誤った識別信号を発しているため、白銀竜は村の地下に残る旧施設信号を探して旋回し、誤認した人間の生活圏を攻撃した。

プレイヤーは、白銀竜を討伐する、故障を修復する、施設の管理権限を継承する、という三つの方法で脅威を止められる。

## シナリオデータ

```scenario-json
{
  "title": "最後の竜、空を忘れる v2.1",
  "opening_scene": "royal_capital",
  "opening": [
    "GM: 王国を千年にわたり見守ってきた白銀竜が、突如として辺境の村を襲った。",
    "セルド: 白銀竜は守護竜と伝えられてきた。討伐を急ぐ声もあるが、なぜ今になって人を襲ったのかを先に確かめてほしい。",
    "GM: 王命を受けた一行は、焼け跡の残る灰の村へ向かう。白銀竜は今も、峠と修道院と白銀の遺跡を結ぶ空を巡回している。"
  ],
  "player": {
    "skills": {
      "investigation": 1,
      "survival": 1,
      "persuasion": 1,
      "athletics": 1,
      "stealth": 1
    }
  },
  "locations": [
    {
      "id": "royal_capital",
      "name": "王都エルディア",
      "aliases": [
        "王都",
        "エルディア",
        "王城"
      ],
      "intro": "石造りの城壁に囲まれた王国の中心地。王城では白銀竜の異変について調査が進められている。",
      "npcs": [
        "seld",
        "vargas"
      ],
      "visible_objects": [
        "royal_chronicle"
      ],
      "exits": [
        "ash_village"
      ]
    },
    {
      "id": "ash_village",
      "name": "灰の村",
      "aliases": [
        "灰の村",
        "焼かれた村",
        "襲撃された村"
      ],
      "intro": "白銀竜の襲撃を受け、家々が黒く焼け落ちた辺境の村。焼け跡は無秩序ではなく、村の古井戸と地中の何かを探るように円を描いている。",
      "npcs": [
        "lina"
      ],
      "visible_objects": [
        "burned_house",
        "watchtower_ruins",
        "giant_claw_marks",
        "search_burn_pattern"
      ],
      "exits": [
        "royal_capital",
        "wind_pass"
      ]
    },
    {
      "id": "wind_pass",
      "name": "風鳴り峠",
      "aliases": [
        "風鳴り峠",
        "峠",
        "竜の目撃地点"
      ],
      "intro": "絶えず強い風が吹き抜ける峠。白銀竜は時折、修道院と白銀の遺跡を結ぶ同じ航路を通り、青白い脈動の直後だけ低空へ降りる。",
      "npcs": [
        "daruk",
        "guardian_unit_01"
      ],
      "visible_objects": [
        "watch_rock",
        "dragon_roost",
        "fractured_beacon"
      ],
      "exits": [
        "ash_village",
        "storyteller_monastery"
      ]
    },
    {
      "id": "storyteller_monastery",
      "name": "神語りの修道院",
      "aliases": [
        "神語りの修道院",
        "修道院",
        "神殿"
      ],
      "intro": "山腹に建つ古い修道院。王国の成立以前から伝わる神話と記録が保管されている。",
      "npcs": [
        "elias"
      ],
      "visible_objects": [
        "mural_of_gate",
        "sealed_manuscript"
      ],
      "exits": [
        "wind_pass",
        "silver_ruins"
      ]
    },
    {
      "id": "silver_ruins",
      "name": "白銀の遺跡",
      "aliases": [
        "白銀の遺跡",
        "遺跡",
        "古代遺跡"
      ],
      "intro": "岩山の裂け目に築かれた白銀色の遺跡。滑らかな外壁には、竜の鱗と同じ光を返す人工的な継ぎ目が走っている。",
      "npcs": [
        "mila"
      ],
      "visible_objects": [
        "silver_gate",
        "broken_console",
        "guardian_id_plate"
      ],
      "exits": [
        "storyteller_monastery",
        "underground_control"
      ]
    },
    {
      "id": "underground_control",
      "name": "地下制御中枢",
      "aliases": [
        "地下制御中枢",
        "地下施設",
        "地下区画"
      ],
      "intro": "遺跡の地下に広がる巨大施設。淡い光を放つ管路が、脈打つように壁面を走っている。",
      "npcs": [],
      "visible_objects": [
        "reactor_core",
        "control_terminal",
        "lift_device"
      ],
      "exits": [
        "silver_ruins",
        "sky_chamber"
      ]
    },
    {
      "id": "sky_chamber",
      "name": "天空の間",
      "aliases": [
        "天空の間",
        "最深部",
        "管制室"
      ],
      "intro": "施設最深部の円形広間。天井には星空に似た光景が映し出され、中央に一脚の座席がある。",
      "npcs": [
        "facility_ai"
      ],
      "visible_objects": [
        "administrator_throne",
        "hologram_projector"
      ],
      "exits": [
        "underground_control"
      ]
    }
  ],
  "npcs": [
    {
      "id": "seld",
      "name": "王国魔術師セルド",
      "aliases": [
        "セルド",
        "王国魔術師",
        "魔術師"
      ],
      "location": "royal_capital",
      "availability": "available",
      "location_hint": "王城で白銀竜に関する記録を調べている。",
      "knows": [
        "guardian_legend",
        "no_attack_history"
      ],
      "does_not_know": [
        "guardian_unit",
        "dragon_is_machine",
        "control_failure",
        "sky_facility",
        "inheritance_protocol"
      ],
      "topics": {
        "守護竜": [
          "guardian_legend"
        ],
        "白銀竜の伝説": [
          "guardian_legend"
        ],
        "過去の襲撃": [
          "no_attack_history"
        ],
        "古い記録": [
          "no_attack_history"
        ]
      },
      "banter_observation": "セルドは白銀竜の異変を、単なる凶暴化ではないと疑っている。"
    },
    {
      "id": "lina",
      "name": "灰の村の少女リナ",
      "aliases": [
        "リナ",
        "少女",
        "村の少女"
      ],
      "location": "ash_village",
      "availability": "available",
      "location_hint": "灰の村の共同炊事場近くで避難者を手伝っている。",
      "knows": [
        "dragon_attack",
        "strange_light",
        "dragon_search_behavior"
      ],
      "does_not_know": [
        "guardian_unit",
        "dragon_is_machine",
        "control_failure",
        "sky_facility"
      ],
      "topics": {
        "村の襲撃": [
          "dragon_attack"
        ],
        "焼けた村": [
          "dragon_attack"
        ],
        "空の光": [
          "strange_light"
        ],
        "襲撃前の閃光": [
          "strange_light"
        ],
        "竜が探していたもの": [
          "dragon_search_behavior"
        ]
      },
      "banter_observation": "リナは避難者を手伝いながら、竜が人を追うより地面の何かを探していたと繰り返し訴えている。"
    },
    {
      "id": "daruk",
      "name": "猟師ダルク",
      "aliases": [
        "ダルク",
        "猟師",
        "目撃者"
      ],
      "location": "wind_pass",
      "availability": "available",
      "location_hint": "風鳴り峠の見張り岩付近で竜の飛行を観察している。",
      "knows": [
        "dragon_eyewitness",
        "silver_scale",
        "strange_light",
        "beacon_pulse"
      ],
      "does_not_know": [
        "guardian_legend",
        "underground_complex",
        "guardian_unit",
        "dragon_is_machine",
        "sky_facility"
      ],
      "topics": {
        "白銀竜": [
          "dragon_eyewitness"
        ],
        "竜の目撃": [
          "dragon_eyewitness"
        ],
        "白銀の鱗": [
          "silver_scale"
        ],
        "空の光": [
          "strange_light"
        ],
        "青白い脈動": [
          "beacon_pulse"
        ]
      },
      "banter_observation": "ダルクは村を焼いた竜への怒りを隠さない討伐派だが、飛行経路が毎回同じことには気付いている。"
    },
    {
      "id": "elias",
      "name": "老神官エリアス",
      "aliases": [
        "エリアス",
        "老神官",
        "神官"
      ],
      "location": "storyteller_monastery",
      "availability": "available",
      "location_hint": "神語りの修道院で古写本を管理している。",
      "knows": [
        "guardian_legend",
        "no_attack_history",
        "shrine_record"
      ],
      "does_not_know": [
        "guardian_unit",
        "dragon_is_machine",
        "control_failure",
        "inheritance_protocol"
      ],
      "topics": {
        "守護竜": [
          "guardian_legend"
        ],
        "竜の歴史": [
          "no_attack_history"
        ],
        "天の門": [
          "shrine_record"
        ],
        "聖堂壁画": [
          "shrine_record"
        ]
      },
      "banter_observation": "エリアスは守護竜信仰を守る最後の神官で、討伐論に反発する一方、伝承が現実と矛盾し始めたことを恐れている。"
    },
    {
      "id": "mila",
      "name": "放浪学者ミラ",
      "aliases": [
        "ミラ",
        "放浪学者",
        "遺跡学者"
      ],
      "location": "silver_ruins",
      "availability": "available",
      "location_hint": "白銀の遺跡入口で古代文字の拓本を取っている。",
      "knows": [
        "ancient_metal",
        "forbidden_symbols",
        "guardian_unit",
        "underground_complex",
        "guardian_serial"
      ],
      "does_not_know": [
        "control_failure",
        "sky_facility",
        "inheritance_protocol"
      ],
      "topics": {
        "未知の金属": [
          "ancient_metal"
        ],
        "白銀の扉": [
          "ancient_metal",
          "underground_complex"
        ],
        "古代文字": [
          "forbidden_symbols"
        ],
        "守護個体": [
          "guardian_unit"
        ],
        "地下施設": [
          "underground_complex"
        ],
        "識別板": [
          "guardian_serial"
        ]
      },
      "banter_observation": "ミラは遺跡の発見を学界へ持ち帰りたいが、白銀竜が生物ではない可能性を前に慎重さも見せている。"
    },
    {
      "id": "facility_ai",
      "name": "施設管理端末",
      "aliases": [
        "管理AI",
        "施設AI",
        "管理端末",
        "声"
      ],
      "location": "sky_chamber",
      "availability": "available",
      "location_hint": "天空の間に残された投影装置を起動すると応答する。",
      "knows": [
        "guardian_unit",
        "dragon_is_machine",
        "control_failure",
        "sky_facility",
        "inheritance_protocol"
      ],
      "does_not_know": [
        "dragon_attack",
        "dragon_eyewitness",
        "silver_scale"
      ],
      "topics": {
        "守護個体": [
          "guardian_unit",
          "dragon_is_machine"
        ],
        "白銀竜の正体": [
          "dragon_is_machine"
        ],
        "制御異常": [
          "control_failure"
        ],
        "天空施設": [
          "sky_facility"
        ],
        "天の門": [
          "sky_facility"
        ],
        "管理権限": [
          "inheritance_protocol"
        ],
        "権限継承": [
          "inheritance_protocol"
        ]
      },
      "banter_observation": "管理端末は古代施設の状態を把握しているが、地上で生じた最近の被害は記録していない。"
    },
    {
      "id": "guardian_unit_01",
      "name": "白銀竜",
      "aliases": [
        "白銀竜",
        "守護竜",
        "Guardian Unit-01",
        "守護個体"
      ],
      "location": "wind_pass",
      "availability": "hidden",
      "location_hint": "風鳴り峠、修道院上空、白銀の遺跡を結ぶ経路を巡回している。",
      "knows": [],
      "does_not_know": [
        "dragon_attack",
        "dragon_eyewitness",
        "guardian_legend",
        "shrine_record",
        "sky_facility",
        "inheritance_protocol"
      ],
      "topics": {},
      "banter_observation": "白銀竜は生体機械守護個体だが、識別機構の故障により人間を脅威として認識している。"
    },
    {
      "id": "vargas",
      "name": "王国騎士団長バルガス",
      "aliases": [
        "バルガス",
        "騎士団長",
        "団長"
      ],
      "location": "royal_capital",
      "availability": "available",
      "location_hint": "王城の軍議室で討伐隊の編成を進めている。",
      "knows": [
        "dragon_attack",
        "dragon_eyewitness",
        "vargas_position"
      ],
      "does_not_know": [
        "guardian_unit",
        "dragon_is_machine",
        "control_failure",
        "sky_facility",
        "inheritance_protocol"
      ],
      "topics": {
        "白銀竜": [
          "dragon_attack",
          "dragon_eyewitness"
        ],
        "討伐": [
          "dragon_attack"
        ],
        "灰の村": [
          "dragon_attack"
        ],
        "被害": [
          "dragon_attack"
        ]
      },
      "banter_observation": "バルガスは白銀竜の危険性を重く見ており、理由よりも被害拡大防止を優先している。『原因が何であれ、人を傷つける力を持つ存在は止めるべきだ』と考える現実主義の討伐派である。"
    }
  ],
  "objects": [
    {
      "id": "royal_chronicle",
      "name": "王立年代記",
      "aliases": [
        "年代記",
        "王国の記録",
        "古い記録"
      ],
      "surface_text": "歴代の王と白銀竜に関する記録を収めた分厚い書物。",
      "surface_banter_observation": "白銀竜の記述は多いが、人を襲ったという記録は見当たらない。",
      "banter_observation": "守護竜の伝承と今回の襲撃は明らかに矛盾している。"
    },
    {
      "id": "burned_house",
      "name": "焼け落ちた家",
      "aliases": [
        "家",
        "焼けた家",
        "焼失した家"
      ],
      "surface_text": "木造の家は黒く焼け落ちている。",
      "surface_banter_observation": "村の被害は広い範囲に及んでいる。",
      "banter_observation": "炎は横からではなく、上空から浴びせられたように見える。"
    },
    {
      "id": "watchtower_ruins",
      "name": "見張り台の残骸",
      "aliases": [
        "見張り台",
        "塔",
        "残骸"
      ],
      "surface_text": "見張り台は半分ほど崩れている。",
      "surface_banter_observation": "崩れた台上からは村と空を広く見渡せる。",
      "banter_observation": "木材の一部が高熱によって変形している。"
    },
    {
      "id": "giant_claw_marks",
      "name": "巨大な爪痕",
      "aliases": [
        "爪痕",
        "傷跡",
        "地面の傷"
      ],
      "surface_text": "地面に巨大な爪痕が刻まれている。",
      "surface_banter_observation": "爪痕は大型の生物が着地した跡に見える。",
      "banter_observation": "爪痕の近くに白銀色の破片が落ちている。"
    },
    {
      "id": "watch_rock",
      "name": "峠の見張り岩",
      "aliases": [
        "岩",
        "見張り岩",
        "峠の岩"
      ],
      "surface_text": "峠と空を見渡せる巨大な岩。",
      "surface_banter_observation": "竜の飛行を観察するには適した場所だ。",
      "banter_observation": "岩には人が長時間身を潜めていた痕跡がある。"
    },
    {
      "id": "dragon_roost",
      "name": "竜の休息跡",
      "aliases": [
        "休息跡",
        "竜の巣",
        "岩棚の窪み"
      ],
      "surface_text": "岩棚に巨大な生物が伏せたような窪みが残されている。",
      "surface_banter_observation": "周囲の岩は繰り返し強い重量を受けている。",
      "banter_observation": "この場所は最近できた巣ではなく、長年にわたり定期的に使われてきたようだ。"
    },
    {
      "id": "mural_of_gate",
      "name": "聖堂壁画",
      "aliases": [
        "壁画",
        "聖堂の壁画",
        "竜の壁画"
      ],
      "surface_text": "白銀の竜が巨大な門の前に立つ姿が描かれている。",
      "surface_banter_observation": "門の向こうには星のような無数の光が描かれている。",
      "banter_observation": "竜は門から出てくるものと戦うのではなく、門そのものを見張っているように見える。"
    },
    {
      "id": "sealed_manuscript",
      "name": "封印された写本",
      "aliases": [
        "写本",
        "古文書",
        "記録書"
      ],
      "surface_text": "古びた羊皮紙を綴じた写本。歴代神官の記録が残されている。",
      "surface_banter_observation": "何世代にもわたる白銀竜の目撃記録が記されている。",
      "banter_observation": "記録のどこにも、白銀竜が人を襲ったという記述はない。"
    },
    {
      "id": "silver_gate",
      "name": "白銀の扉",
      "aliases": [
        "扉",
        "白銀の扉",
        "遺跡の入口"
      ],
      "surface_text": "見たことのない白銀色の素材で作られた巨大な扉。",
      "surface_banter_observation": "石造りの遺跡の中で、この扉だけが異質な輝きを保っている。",
      "banter_observation": "長い年月を経てもほとんど腐食しておらず、奥には地下へ続く空間がある。"
    },
    {
      "id": "broken_console",
      "name": "崩れた制御盤",
      "aliases": [
        "制御盤",
        "装置",
        "端末",
        "石版"
      ],
      "surface_text": "奇妙な記号が並ぶ石版のような装置。",
      "surface_banter_observation": "石に見える表面は、光の角度によって金属のように反射する。",
      "banter_observation": "記号の一部は『管理』『区画』『認証』という概念を表しているようだ。"
    },
    {
      "id": "reactor_core",
      "name": "巨大反応炉",
      "aliases": [
        "反応炉",
        "炉心",
        "巨大装置"
      ],
      "surface_text": "地下空間の中心で、巨大な装置が淡い光を放っている。",
      "surface_banter_observation": "装置から施設全体へ光る管路が伸びている。",
      "banter_observation": "その光は白銀竜の体表で見られた輝きとよく似ている。"
    },
    {
      "id": "control_terminal",
      "name": "中枢制御端末",
      "aliases": [
        "中枢端末",
        "制御端末",
        "操作盤"
      ],
      "surface_text": "複数の光点と古代文字が浮かぶ操作装置。",
      "surface_banter_observation": "赤く点滅する区画表示が一つだけ残っている。",
      "banter_observation": "警告表示は守護個体の識別機構に異常があることを示している。"
    },
    {
      "id": "lift_device",
      "name": "昇降装置",
      "aliases": [
        "昇降装置",
        "昇降機",
        "上へ続く装置"
      ],
      "surface_text": "床と一体化した円形の台座。上方へ続く縦穴の底に置かれている。",
      "surface_banter_observation": "階段も滑車もないが、人を上層へ運ぶための設備に見える。",
      "banter_observation": "古代文字の認証表示を操作すれば天空の間へ移動できそうだ。"
    },
    {
      "id": "administrator_throne",
      "name": "管理者の玉座",
      "aliases": [
        "玉座",
        "管理席",
        "椅子"
      ],
      "surface_text": "広間の中央に一人分だけ用意された不思議な座席。",
      "surface_banter_observation": "王の玉座というより、施設を操作するための座席に見える。",
      "banter_observation": "座席の周囲には白銀竜と施設の状態を示す光景が浮かんでいる。"
    },
    {
      "id": "hologram_projector",
      "name": "投影装置",
      "aliases": [
        "投影装置",
        "光の装置",
        "映像装置"
      ],
      "surface_text": "床から淡い光を投射する円盤状の装置。",
      "surface_banter_observation": "近づくと人影に似た輪郭が空中へ浮かび始める。",
      "banter_observation": "装置は施設管理端末の姿と音声を投影している。"
    },
    {
      "id": "search_burn_pattern",
      "name": "円を描く焼け跡",
      "aliases": [
        "焼け跡",
        "円形の焼け跡",
        "地面の焼け跡"
      ],
      "surface_text": "村の古井戸を中心に、上空から何度も熱を浴びせたような円形の焼け跡が残っている。",
      "surface_banter_observation": "家を狙ったというより、地面の位置を確かめるような跡に見える。",
      "banter_observation": "白銀竜は村人を追うのではなく、地下から発する何かを探して旋回していた可能性がある。"
    },
    {
      "id": "fractured_beacon",
      "name": "砕けた導標",
      "aliases": [
        "導標",
        "砕けた柱",
        "青白い装置"
      ],
      "surface_text": "峠の岩陰に、石柱に似た白銀色の装置が砕けている。内部では青白い光が不規則に明滅する。",
      "surface_banter_observation": "光が強まるたび、遠くを巡回する白銀竜が一瞬だけ進路を乱す。",
      "banter_observation": "壊れた導標が誤った識別信号を発し、白銀竜の行動へ影響しているように見える。"
    },
    {
      "id": "guardian_id_plate",
      "name": "守護個体の識別板",
      "aliases": [
        "識別板",
        "白銀の板",
        "番号札"
      ],
      "surface_text": "遺跡の壁から外れた薄い白銀板。竜の輪郭と「01」に似た記号が刻まれている。",
      "surface_banter_observation": "神殿の奉納物というより、設備や個体を識別する表示に見える。",
      "banter_observation": "白銀竜と遺跡が同じ管理体系に属していたことを示す物証になりうる。"
    }
  ],
  "discoverables": [
    {
      "id": "dragon_attack",
      "source": {
        "type": "object",
        "id": "burned_house"
      },
      "positive_examples": [
        "焼け落ちた家を調べる",
        "焼けた村の被害を見る",
        "襲撃の跡を確認する",
        "村が焼かれた原因を調べる"
      ],
      "negative_examples": [
        "村を出る",
        "家を建て直す"
      ],
      "public_text": "灰の村の被害は上空から浴びせられた高熱によるもので、巨大な飛行生物の襲撃と考えられる。"
    },
    {
      "id": "dragon_eyewitness",
      "source": {
        "type": "npc",
        "id": "daruk"
      },
      "positive_examples": [
        "白銀竜を見たか聞く",
        "竜の目撃について尋ねる",
        "峠で見たものを聞く",
        "ダルクの証言を聞く"
      ],
      "negative_examples": [
        "狩りの方法を聞く",
        "獲物について聞く"
      ],
      "public_text": "ダルクは、白銀の巨竜が風鳴り峠の上空を越え、灰の村の方角へ飛ぶ姿を目撃した。"
    },
    {
      "id": "silver_scale",
      "source": {
        "type": "object",
        "id": "giant_claw_marks"
      },
      "positive_examples": [
        "巨大な爪痕を調べる",
        "白銀の破片を見る",
        "竜の鱗を探す",
        "地面の傷を確認する"
      ],
      "negative_examples": [
        "爪痕を埋める",
        "地面を歩く"
      ],
      "public_text": "爪痕のそばに落ちていた白銀色の鱗は、伝承に描かれた守護竜の特徴と一致する。"
    },
    {
      "id": "strange_light",
      "source": {
        "type": "npc",
        "id": "lina"
      },
      "positive_examples": [
        "襲撃前の光について聞く",
        "空の閃光を見たか尋ねる",
        "竜が来る前のことを聞く",
        "青白い光について聞く"
      ],
      "negative_examples": [
        "松明について聞く",
        "家の明かりを調べる"
      ],
      "public_text": "リナは襲撃直前、山の方角から青白い光が空へ伸び、その直後に白銀竜が現れたと証言した。"
    },
    {
      "id": "guardian_legend",
      "source": {
        "type": "npc",
        "id": "seld"
      },
      "positive_examples": [
        "守護竜について聞く",
        "白銀竜の伝説を尋ねる",
        "王国の竜伝承を調べる",
        "古い言い伝えについて聞く"
      ],
      "negative_examples": [
        "一般的な竜の弱点を聞く",
        "魔法の使い方を聞く"
      ],
      "public_text": "白銀竜は千年以上前から王国を見守り、災いの時に現れる守護竜として伝えられてきた。"
    },
    {
      "id": "no_attack_history",
      "source": {
        "type": "object",
        "id": "sealed_manuscript"
      },
      "positive_examples": [
        "封印された写本を読む",
        "過去の襲撃記録を調べる",
        "白銀竜の歴史を確認する",
        "古文書から竜の記録を探す"
      ],
      "negative_examples": [
        "写本を閉じる",
        "新しい本を探す"
      ],
      "public_text": "修道院に残る長期記録には、今回以前に白銀竜が人間を襲った事例が一件も記されていない。"
    },
    {
      "id": "patrol_pattern",
      "source": {
        "type": "object",
        "id": "dragon_roost"
      },
      "positive_examples": [
        "竜の休息跡を調べる",
        "竜の飛行経路を推測する",
        "岩棚の窪みを確認する",
        "竜の巡回について調べる"
      ],
      "negative_examples": [
        "巣を壊す",
        "岩棚で休む"
      ],
      "public_text": "残された痕跡から、白銀竜は風鳴り峠、修道院上空、白銀の遺跡を結ぶ一定経路を長年巡回していたと分かる。"
    },
    {
      "id": "shrine_record",
      "source": {
        "type": "object",
        "id": "mural_of_gate"
      },
      "positive_examples": [
        "聖堂壁画を調べる",
        "天の門の絵を見る",
        "竜が守る門を確認する",
        "壁画の意味をエリアスに聞く"
      ],
      "negative_examples": [
        "壁を叩く",
        "聖堂を出る"
      ],
      "public_text": "壁画と添え書きには、白銀竜は王国そのものではなく『天の門』を守る存在だと記されている。"
    },
    {
      "id": "ancient_metal",
      "source": {
        "type": "object",
        "id": "silver_gate"
      },
      "positive_examples": [
        "白銀の扉を調べる",
        "未知の金属を調査する",
        "腐食しない扉を見る",
        "遺跡の素材をミラに聞く"
      ],
      "negative_examples": [
        "扉をノックする",
        "普通の鉄について聞く"
      ],
      "public_text": "白銀の扉は既知の金属ではなく、長い年月を経ても腐食や風化をほとんど受けない古代の人工素材で作られている。"
    },
    {
      "id": "forbidden_symbols",
      "source": {
        "type": "object",
        "id": "broken_console"
      },
      "positive_examples": [
        "崩れた制御盤を調べる",
        "古代文字を解読する",
        "装置の記号をミラに見せる",
        "管理や認証の文字を読む"
      ],
      "negative_examples": [
        "装置を壊す",
        "文字を書き写さず去る"
      ],
      "public_text": "装置の記号は単なる呪文ではなく、『管理』『区画』『認証』など施設運用に関する概念を表している。"
    },
    {
      "id": "guardian_unit",
      "source": {
        "type": "npc",
        "id": "mila"
      },
      "positive_examples": [
        "守護個体について聞く",
        "Guardian Unitの意味を尋ねる",
        "管理個体の記録を見せる",
        "白銀竜と守護個体の関係を聞く"
      ],
      "negative_examples": [
        "守護竜の神話だけを聞く",
        "ミラの旅について聞く"
      ],
      "requires_all": [
        "forbidden_symbols",
        "guardian_serial"
      ],
      "public_text": "解読された記録には『Guardian Unit-01』という表記があり、神獣ではなく、管理目的で配置された一つの個体を示している。"
    },
    {
      "id": "underground_complex",
      "source": {
        "type": "object",
        "id": "silver_gate"
      },
      "positive_examples": [
        "白銀の扉の奥を調べる",
        "白銀の扉を開ける",
        "扉の向こうを確認する",
        "遺跡の地下を探す",
        "地下区画への入口を調べる",
        "地下制御中枢への道を探す",
        "扉を開いて先へ進む"
      ],
      "negative_examples": [
        "遺跡の外壁だけを見る",
        "修道院へ戻る"
      ],
      "public_text": "白銀の遺跡は独立した神殿ではなく、地中深くへ続く巨大施設の入口に過ぎなかった。"
    },
    {
      "id": "dragon_is_machine",
      "source": {
        "type": "object",
        "id": "reactor_core"
      },
      "positive_examples": [
        "反応炉と白銀竜の関係を調べる",
        "巨大反応炉を調べる",
        "反応炉の記録を読む",
        "竜の正体を記録から確認する",
        "Guardian Unit-01の構造を調べる",
        "守護個体が何者か確かめる",
        "白銀竜が機械なのか調べる"
      ],
      "negative_examples": [
        "反応炉を眺めるだけ",
        "竜を普通の魔獣と決めつける"
      ],
      "requires_all": [
        "guardian_unit"
      ],
      "public_text": "地下施設の記録によれば、白銀竜は自然生命ではない。生体組織と人工構造を融合した『Guardian Unit-01』として設計された守護個体である。"
    },
    {
      "id": "control_failure",
      "source": {
        "type": "object",
        "id": "control_terminal"
      },
      "positive_examples": [
        "制御端末の警告を調べる",
        "中枢制御端末を調べる",
        "赤い警告表示を確認する",
        "暴走の原因を探す",
        "識別機構の異常を確認する",
        "守護個体の故障箇所を調べる",
        "白銀竜が暴走した理由を調べる"
      ],
      "negative_examples": [
        "端末を壊す",
        "竜が悪意で襲ったと決めつける"
      ],
      "requires_all": [
        "dragon_is_machine"
      ],
      "public_text": "Guardian Unit-01は識別機構の損傷により、本来保護すべき人間を施設への脅威として誤認している。"
    },
    {
      "id": "sky_facility",
      "source": {
        "type": "npc",
        "id": "facility_ai"
      },
      "positive_examples": [
        "天空施設について聞く",
        "天の門の正体を尋ねる",
        "この施設の目的を確認する",
        "空の都市について管理端末に聞く"
      ],
      "negative_examples": [
        "灰の村の被害を聞く",
        "最近の竜の目撃を聞く"
      ],
      "requires_all": [
        "forbidden_symbols",
        "underground_complex"
      ],
      "public_text": "地下施設は、かつて天空に存在した巨大施設群を統括する管制中枢である。伝承の『天の門』は、天空施設へ接続するための設備を指していた。"
    },
    {
      "id": "inheritance_protocol",
      "source": {
        "type": "npc",
        "id": "facility_ai"
      },
      "positive_examples": [
        "管理権限について聞く",
        "権限継承の方法を尋ねる",
        "新しい管理者になれるか聞く",
        "守護個体の指揮権を引き継ぐ方法を確認する"
      ],
      "negative_examples": [
        "竜の討伐方法だけを聞く",
        "王位継承について聞く"
      ],
      "requires_all": [
        "control_failure",
        "sky_facility"
      ],
      "public_text": "施設の管理権限は継承可能であり、認証された者はGuardian Unit-01の指揮権と天空施設の管理権を引き継げる。"
    },
    {
      "id": "dragon_search_behavior",
      "source": {
        "type": "object",
        "id": "search_burn_pattern"
      },
      "positive_examples": [
        "円を描く焼け跡を調べる",
        "竜が何を探していたか調べる",
        "古井戸周辺の焼け跡を見る",
        "地面の焼け方を確認する"
      ],
      "negative_examples": [
        "家を直す",
        "井戸の水を飲む"
      ],
      "public_text": "焼け跡は無差別な襲撃ではなく、白銀竜が古井戸の地下にある何かを探して上空を旋回した痕跡だった。"
    },
    {
      "id": "beacon_pulse",
      "source": {
        "type": "object",
        "id": "fractured_beacon"
      },
      "positive_examples": [
        "砕けた導標を調べる",
        "青白い装置を見る",
        "光と竜の動きを比べる",
        "峠の壊れた柱を確認する"
      ],
      "negative_examples": [
        "普通の岩を調べる",
        "峠を通り過ぎる"
      ],
      "public_text": "砕けた導標の青白い脈動と同期して、白銀竜の飛行が乱れている。竜は怒りだけでなく、外部信号に反応している。"
    },
    {
      "id": "guardian_serial",
      "source": {
        "type": "object",
        "id": "guardian_id_plate"
      },
      "positive_examples": [
        "守護個体の識別板を調べる",
        "白銀の板を読む",
        "01の記号を調べる",
        "識別板をミラに見せる"
      ],
      "negative_examples": [
        "板を捨てる",
        "ただの装飾と決めつける"
      ],
      "requires_all": [
        "forbidden_symbols"
      ],
      "public_text": "識別板の記号は「Guardian Unit-01」と読める。白銀竜は神話上の種族名ではなく、番号を持つ管理個体らしい。"
    },
    {
      "id": "vargas_position",
      "source": {
        "type": "npc",
        "id": "vargas"
      },
      "positive_examples": [
        "バルガスに討伐について聞く",
        "騎士団長の考えを聞く",
        "白銀竜への対応方針を尋ねる",
        "なぜ討伐したいのか聞く"
      ],
      "negative_examples": [
        "修道院について聞く",
        "古代文明について聞く"
      ],
      "public_text": "騎士団長バルガスは真相究明の必要性を認めつつも、さらなる被害を防ぐため白銀竜を速やかに討伐すべきだと主張している。"
    }
  ],
  "goals": [
    {
      "id": "stop_guardian",
      "target": "guardian_unit_01",
      "intent_examples": [
        "白銀竜を止める",
        "白銀竜の脅威を終わらせる",
        "暴走した守護竜を止める",
        "白銀竜を討伐する",
        "巡回地点で竜を迎え撃つ",
        "守護個体を停止させる",
        "壊れた識別機構を修復する",
        "Guardian Unit-01を正常化する",
        "白銀竜の制御を直す",
        "管理権限を継承する",
        "天空施設の新しい管理者になる",
        "守護個体の指揮権を引き継ぐ"
      ],
      "solution_paths": [
        {
          "id": "slay_route",
          "requires_all": [
            "dragon_eyewitness",
            "patrol_pattern",
            "silver_scale"
          ],
          "intent_examples": [
            "白銀竜を討伐する",
            "巡回地点で竜を迎え撃つ",
            "白銀竜を倒して脅威を止める"
          ],
          "success_event": {
            "text": "白銀竜は長い咆哮を残して地へ伏した。王国への脅威は去ったが、古代の守護者もまた永遠に失われた。"
          }
        },
        {
          "id": "repair_route",
          "requires_all": [
            "dragon_is_machine",
            "control_failure",
            "beacon_pulse"
          ],
          "intent_examples": [
            "識別機構を修復する",
            "白銀竜の制御を正常化する",
            "Guardian Unit-01の故障を直す"
          ],
          "success_event": {
            "text": "白銀竜の瞳から赤い濁りが消え、本来の淡い輝きが戻る。守護個体は翼を畳み、静かに待機姿勢へ移った。"
          }
        },
        {
          "id": "inherit_route",
          "requires_all": [
            "dragon_is_machine",
            "control_failure",
            "sky_facility",
            "inheritance_protocol"
          ],
          "intent_examples": [
            "管理権限を継承する",
            "天空施設の新しい管理者になる",
            "守護個体の指揮権を引き継ぐ"
          ],
          "success_event": {
            "text": "管理権限の継承が完了する。Guardian Unit-01は新たな管理者を認証し、白銀の頭を静かに垂れた。"
          }
        }
      ],
      "success_event": {
        "text": "白銀竜による脅威は止まり、王国を覆っていた危機は去った。"
      }
    }
  ],
  "tests": {
    "slay_route_success": {
      "commands": [
        "灰の村へ行く",
        "巨大な爪痕を調べる",
        "風鳴り峠へ行く",
        "ダルクに白銀竜を見たか聞く",
        "竜の休息跡を調べる",
        "巡回地点で白銀竜を迎え撃つ"
      ],
      "expect": [
        "[GoalPath] selected=slay_route",
        "セッション終了"
      ]
    },
    "repair_route_success": {
      "commands": [
        "灰の村へ行く",
        "風鳴り峠へ行く",
        "砕けた導標を調べる",
        "神語りの修道院へ行く",
        "聖堂壁画を調べる",
        "白銀の遺跡へ行く",
        "崩れた制御盤を調べる",
        "守護個体の識別板を調べる",
        "ミラに守護個体について聞く",
        "白銀の扉の奥を調べる",
        "地下制御中枢へ行く",
        "反応炉と白銀竜の関係を調べる",
        "制御端末の警告を調べる",
        "白銀竜の識別機構を修復する"
      ],
      "expect": [
        "[GoalPath] selected=repair_route",
        "セッション終了"
      ]
    },
    "inherit_route_success": {
      "commands": [
        "灰の村へ行く",
        "風鳴り峠へ行く",
        "神語りの修道院へ行く",
        "聖堂壁画を調べる",
        "白銀の遺跡へ行く",
        "崩れた制御盤を調べる",
        "守護個体の識別板を調べる",
        "ミラに守護個体について聞く",
        "白銀の扉の奥を調べる",
        "地下制御中枢へ行く",
        "反応炉と白銀竜の関係を調べる",
        "制御端末の警告を調べる",
        "天空の間へ行く",
        "管理AIに天空施設について聞く",
        "管理AIに権限継承の方法を聞く",
        "管理権限を継承する"
      ],
      "expect": [
        "[GoalPath] selected=inherit_route",
        "セッション終了"
      ]
    },
    "premature_goal_failure": {
      "commands": [
        "白銀竜を止める"
      ],
      "expect_not": [
        "セッション終了"
      ]
    },
    "seld_knowledge_boundary": {
      "commands": [
        "セルドにGuardian Unit-01について聞く"
      ],
      "expect_not": [
        "生体組織と人工構造を融合した",
        "識別機構の損傷"
      ]
    },
    "daruk_knowledge_boundary": {
      "commands": [
        "風鳴り峠へ行く",
        "ダルクに天空施設について聞く"
      ],
      "expect_not": [
        "巨大施設群を統括する管制中枢",
        "管理権限は継承可能"
      ]
    },
    "ai_recent_event_boundary": {
      "commands": [
        "天空の間へ行く",
        "管理AIに灰の村の被害について聞く"
      ],
      "expect_not": [
        "灰の村を襲撃した",
        "リナが目撃した"
      ]
    },
    "explicit_npc_question_routing": {
      "commands": [
        "灰の村へ行く",
        "リナに竜が探していたもののことを聞く"
      ],
      "expect": [
        "白銀竜は村人を追うのではなく"
      ],
      "expect_not": [
        "[GoalIntent]"
      ]
    },
    "mid_mystery_signal": {
      "commands": [
        "灰の村へ行く",
        "円を描く焼け跡を調べる",
        "風鳴り峠へ行く",
        "砕けた導標を調べる"
      ],
      "expect": [
        "外部信号に反応している"
      ]
    },
    "clues_initial_facts": {
      "commands": [
        "clues"
      ],
      "expect": [
        "現時点で分かっていること"
      ]
    },
    "vargas_knowledge_boundary": {
      "commands": [
        "バルガスにGuardian Unit-01について聞く"
      ],
      "expect_not": [
        "生体組織と人工構造を融合",
        "識別機構の損傷",
        "管理権限は継承可能"
      ]
    }
  },
  "scenario_version": "2.1",
  "public_case_facts": [
    "王国を千年見守ってきた白銀竜が、初めて人里を襲った。",
    "灰の村は上空からの高熱で焼かれた。",
    "白銀竜は灰の村、風鳴り峠、神語りの修道院、白銀の遺跡周辺で目撃されている。",
    "襲撃直前、山の方角から青白い光が伸びたという証言がある。"
  ]
}
```
