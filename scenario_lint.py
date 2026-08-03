#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
from pathlib import Path


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, dict):
                out.append(x.get('id') or x.get('clue'))
            else:
                out.append(x)
        return [str(x) for x in out if x]
    if isinstance(v, dict):
        return [str(k) for k, val in v.items() if val]
    return [str(v)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scenario_json')
    a = ap.parse_args()
    sc = json.loads(Path(a.scenario_json).read_text(encoding='utf-8'))
    errors = []
    warnings = []

    locs = {x['id'] for x in sc.get('locations', [])}
    objs = {x['id'] for x in sc.get('objects', [])}
    npcs = {x['id'] for x in sc.get('npcs', [])}
    supported_skills = {'investigation', 'survival', 'persuasion', 'athletics', 'stealth'}

    def check_skill_check(check, label):
        if not isinstance(check, dict):
            errors.append(f'{label} skill_check must be object/dict')
            return
        if check.get('skill') not in supported_skills:
            errors.append(f'{label} skill_check unknown skill: {check.get("skill")}')
        dice = str(check.get('dice', '2d6'))
        if not re.fullmatch(r'[1-9]\d*d[1-9]\d*', dice, re.IGNORECASE):
            errors.append(f'{label} skill_check invalid dice: {dice}')
        difficulty = check.get('difficulty')
        if not isinstance(difficulty, int) or isinstance(difficulty, bool):
            errors.append(f'{label} skill_check difficulty must be integer')

    ids = []
    for d in sc.get('discoverables', []):
        if not d.get('id'):
            errors.append('discoverable without id')
        if d.get('id') in ids:
            errors.append('duplicate discoverable id: ' + d.get('id', ''))
        ids.append(d.get('id'))
        if not isinstance(d.get('public_text'), str) or not d.get('public_text', '').strip():
            errors.append('discoverable missing non-empty string public_text: ' + d.get('id', '<unknown>'))
    dids = set(ids)

    def check_refs(container, label):
        cid = container.get('id', '<unknown>')
        for key in ('requires_all', 'required_discoverables', 'requires_any'):
            for ref in container.get(key, []) or []:
                if ref not in dids:
                    errors.append(f'{label} {cid} {key} unknown id: {ref}')

    for loc in sc.get('locations', []):
        lid = loc.get('id', '<unknown>')
        for x in loc.get('exits', []):
            if x not in locs:
                errors.append(f'location {lid} exits unknown location: {x}')
        for x in loc.get('visible_objects', []):
            if x not in objs:
                errors.append(f'location {lid} visible_objects unknown object: {x}')
        for x in loc.get('npcs', []):
            if x not in npcs:
                errors.append(f'location {lid} npcs unknown npc: {x}')

    for d in sc.get('discoverables', []):
        did = d.get('id', '<unknown>')
        src = d.get('source', {})
        if src.get('type') == 'object' and src.get('id') not in objs:
            errors.append(f'discoverable {did} source unknown object: {src.get("id")}')
        if src.get('type') == 'npc' and src.get('id') not in npcs:
            errors.append(f'discoverable {did} source unknown npc: {src.get("id")}')
        check_refs(d, 'discoverable')
        if d.get('skill_check') is not None:
            check_skill_check(d.get('skill_check'), f'discoverable {did}')

    action_ids = set()
    for action in sc.get('action_checks', []) or []:
        aid = action.get('id', '<unknown>')
        if aid == '<unknown>':
            errors.append('action_check without id')
        elif aid in action_ids:
            errors.append(f'duplicate action_check id: {aid}')
        action_ids.add(aid)
        if not action.get('positive_examples'):
            errors.append(f'action_check {aid} missing positive_examples')
        check_skill_check(action.get('skill_check'), f'action_check {aid}')
        if action.get('required_location') and action.get('required_location') not in locs:
            errors.append(f'action_check {aid} required_location unknown: {action.get("required_location")}')
        for effect_name in ('success_effect', 'failure_effect'):
            effect = action.get(effect_name, {}) or {}
            destination = effect.get('move_to', effect.get('moves_to'))
            if destination and destination not in locs:
                errors.append(f'action_check {aid} {effect_name} move_to unknown: {destination}')

    for g in sc.get('goals', []):
        gid = g.get('id', '<unknown>')
        target = g.get('target')
        if target not in objs and target not in npcs:
            errors.append(f'goal {gid} target unknown: {target}')
        check_refs(g, 'goal')
        for path in g.get('solution_paths', []) or []:
            check_refs(path, 'goal_path')
        if g.get('required_location') and g.get('required_location') not in locs:
            errors.append(f'goal {gid} required_location unknown: {g.get("required_location")}')

    # v2.14+ NPC GM-note validation
    allowed_availability = {'available', 'missing', 'hidden', 'unavailable', 'absent'}
    for npc in sc.get('npcs', []):
        nid = npc.get('id', '<unknown>')
        if npc.get('location') and npc.get('location') not in locs:
            errors.append(f'npc {nid} location unknown: {npc.get("location")}')
        for key in ('start_location', 'current_location'):
            if npc.get(key) and npc.get(key) not in locs:
                errors.append(f'npc {nid} {key} unknown: {npc.get(key)}')
        if npc.get('availability') and npc.get('availability') not in allowed_availability:
            warnings.append(f'npc {nid} availability unusual: {npc.get("availability")}')

        for key in ('knows', 'knowledge', 'known_clues', 'does_not_know', 'unknown_clues'):
            for ref in as_list(npc.get(key)):
                if ref not in dids:
                    errors.append(f'npc {nid} {key} unknown discoverable: {ref}')

        topics = npc.get('topics') or npc.get('topic_hints') or {}
        if topics and not isinstance(topics, dict):
            errors.append(f'npc {nid} topics must be object/dict')
        if isinstance(topics, dict):
            for topic, refs in topics.items():
                if not str(topic).strip():
                    warnings.append(f'npc {nid} has empty topic label')
                for ref in as_list(refs):
                    if ref not in dids:
                        errors.append(f'npc {nid} topic {topic} unknown discoverable: {ref}')
                    # soft consistency check
                    known = set(as_list(npc.get('knows')) + as_list(npc.get('knowledge')) + as_list(npc.get('known_clues')))
                    if known and ref not in known:
                        warnings.append(f'npc {nid} topic {topic} maps {ref}, but it is not listed in knows/knowledge')

    print(f'Lint result: {len(errors)} errors, {len(warnings)} warnings')
    for e in errors:
        print('[ERROR]', e)
    for w in warnings:
        print('[WARN]', w)
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__':
    main()
