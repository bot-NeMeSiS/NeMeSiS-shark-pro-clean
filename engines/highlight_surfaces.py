"""Read-only batch availability for canonical matches across client collections."""
from engines.highlight_read_model import read_highlights_map


def enrich_context(db_path, context, enabled=True):
    rows, visited = [], set()
    def walk(value, depth=0):
        if depth > 10 or len(visited) >= 10000 or id(value) in visited:
            return
        if isinstance(value, (dict,list,tuple)):
            visited.add(id(value))
        if isinstance(value, dict):
            if value.get('id') and value.get('home_team') and value.get('away_team') and value.get('source'):
                rows.append(value)
            for item in value.values():
                if isinstance(item,(dict,list,tuple)):
                    walk(item,depth+1)
        elif isinstance(value,(list,tuple)):
            for item in value:
                walk(item,depth+1)
    walk(context)
    ids = list(dict.fromkeys(str(row['id']) for row in rows))
    mapped = {}
    state = 'DISABLED_BY_ADMIN' if not enabled else 'VERIFIED'
    if enabled:
        for start in range(0,len(ids),500):
            snapshot = read_highlights_map(db_path,ids[start:start+500],limit_per_match=1)
            if snapshot['read_state'] != 'VERIFIED':
                state = snapshot['read_state']
            mapped.update(snapshot['map'])
    for row in rows:
        row['has_highlights'] = bool(mapped.get(str(row['id']))) if state in {'VERIFIED','DISABLED_BY_ADMIN'} else None
        row['highlight_read_state'] = state
        row['client_highlight_label'] = '▶ Resumen disponible' if row['has_highlights'] else ''
    return {mid:bool(mapped.get(mid)) for mid in ids}
