"""Read-only batch availability for canonical matches across client collections."""
from engines.highlight_read_model import read_highlights_map


def copy_view(value, depth=0, memo=None):
    """Copy presentation containers without copying Flask objects or source rows."""
    memo = {} if memo is None else memo
    if depth > 10 or not isinstance(value, (dict, list, tuple)):
        return value
    if id(value) in memo:
        return memo[id(value)]
    if isinstance(value, dict):
        result = {}
        memo[id(value)] = result
        result.update((key, copy_view(item, depth + 1, memo)) for key, item in value.items())
    else:
        result = []
        memo[id(value)] = result
        result.extend(copy_view(item, depth + 1, memo) for item in value)
        if isinstance(value, tuple):
            result = tuple(result)
            memo[id(value)] = result
    return result


def enrich_context(db_path, context, enabled=True):
    rows, visited = [], set()
    def walk(value, depth=0):
        if depth > 10 or len(visited) >= 10000 or id(value) in visited:
            return
        if isinstance(value, (dict,list,tuple)):
            visited.add(id(value))
        if isinstance(value, dict):
            canonical_id = value.get('match_id') or value.get('id')
            if canonical_id and value.get('home_team') and value.get('away_team') and value.get('source'):
                rows.append((value,str(canonical_id)))
            for item in value.values():
                if isinstance(item,(dict,list,tuple)):
                    walk(item,depth+1)
        elif isinstance(value,(list,tuple)):
            for item in value:
                walk(item,depth+1)
    walk(context)
    ids = list(dict.fromkeys(mid for row,mid in rows))
    mapped = {}
    state = 'DISABLED_BY_ADMIN' if not enabled else 'VERIFIED'
    if enabled:
        for start in range(0,len(ids),500):
            snapshot = read_highlights_map(db_path,ids[start:start+500],limit_per_match=1)
            if snapshot['read_state'] != 'VERIFIED':
                state = snapshot['read_state']
            mapped.update(snapshot['map'])
    for row,mid in rows:
        row['has_highlights'] = bool(mapped.get(mid)) if state in {'VERIFIED','DISABLED_BY_ADMIN'} else None
        row['highlight_read_state'] = state
        row['client_highlight_label'] = '▶ Resumen disponible' if row['has_highlights'] else ''
    return {mid:bool(mapped.get(mid)) for mid in ids}
