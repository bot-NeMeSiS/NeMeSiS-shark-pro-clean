"""Synthetic fixture/quote observations. No provider requests, bets or real users."""
from datetime import timedelta
import json
import sqlite3
from copy import deepcopy

import pytest
from test_combi_advisor_contract import db, NOW
from engines import client_combi_store as store
from engines.combi_advisor_engine import CombiError
from engines.combi_match_catalogue import choice_id, read_catalogue, resolve_choices
from engines.combi_draft_review import review_draft


def quotes(db, ids=(1,2), **kw):
    with sqlite3.connect(db) as conn:
        for i in ids:
            row={'id':'q'+str(i),'match_id':'m'+str(i),'market':'h2h','bookmaker':'Casa QA',
                 'source':'The Odds API','home_team':'Local '+str(i),'away_team':'Visitante '+str(i),
                 'home_price':'1.80','draw_price':'3.00','away_price':'4.00','created_at':NOW.isoformat()}
            row.update(kw)
            conn.execute('INSERT INTO odds_snapshots VALUES ('+','.join('?' for _ in row)+')',list(row.values()))


def provider_quote_clock(db, ids=(1,2), observed_at=None):
    observed_at = observed_at or NOW.isoformat()
    with sqlite3.connect(db) as conn:
        cols = {row[1] for row in conn.execute('PRAGMA table_info(odds_snapshots)')}
        if 'payload_json' not in cols:
            conn.execute('ALTER TABLE odds_snapshots ADD COLUMN payload_json TEXT')
        for i in ids:
            payload = {'bookmakers': [{'title': 'Casa QA', 'key': 'casa qa', 'last_update': observed_at,
                'markets': [{'key': 'h2h', 'last_update': observed_at}]}]}
            conn.execute('UPDATE odds_snapshots SET payload_json=? WHERE id=?',
                          (json.dumps(payload), 'q'+str(i)))


def catalogue(db, filters=None, user='a'):
    return store.read_center(db,user,now=NOW,catalogue_filters=filters or {})['catalogue']


def ids_for_two(db):
    cat=catalogue(db)
    return [m['groups'][0]['choices'][0]['id'] for m in cat['matches'] if m['groups']][:2]


def test_catalogue_independent_of_picks_and_writes(db):
    quotes(db)
    with sqlite3.connect(db) as conn:conn.execute('DROP TABLE picks')
    before=open(db,'rb').read()
    cat=catalogue(db)
    assert cat['total']==17
    available=[m for m in cat['matches'] if m['groups']]
    assert len(available)==2
    assert [p['selection'] for p in available[0]['groups'][0]['choices']]==['1','X','2']
    assert all(p['selection_origin']=='customer_market_choice' for p in available[0]['groups'][0]['choices'])
    assert not available[0]['groups'][0]['market_reading']['available']
    assert all('market_implied_probability_pct' not in p for p in available[0]['groups'][0]['choices'])
    assert open(db,'rb').read()==before
    assert not any('published' in p for p in cat['matches'])


def test_no_quote_means_no_fake_price_or_selectable_choice(db):
    cat=catalogue(db)
    assert cat['total']==17 and all(not m['groups'] for m in cat['matches'])


def test_provider_aliases_render_as_one_fixture_and_keep_the_quote_record(db):
    from test_combi_advisor_contract import fixture

    alias = fixture(18)
    alias.update(home_team='Local 1', away_team='Visitante 1',
                 competition_name='Spanish La Liga', source='API-Football',
                 kickoff_iso=fixture(1)['kickoff_iso'])
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE matches SET competition_name='La Liga' WHERE id='m1'")
        conn.execute('INSERT INTO matches VALUES ('+','.join('?' for _ in alias)+')', list(alias.values()))
    quotes(db, ids=(18,), home_team='Local 1', away_team='Visitante 1')

    cat = catalogue(db)
    same_fixture = [m for m in cat['matches'] if m['home'] == 'Local 1' and m['away'] == 'Visitante 1']

    assert cat['total'] == 17
    assert len(same_fixture) == 1
    assert same_fixture[0]['groups']
    assert all(choice['id'].startswith('market:q18:') for choice in same_fixture[0]['groups'][0]['choices'])


@pytest.mark.parametrize(('competition','minute_offset'), [
    ('Copa del Rey', 0),
    ('Spanish La Liga', 1),
])
def test_fixture_catalogue_does_not_collapse_different_competition_or_kickoff(db, competition, minute_offset):
    from datetime import datetime, timedelta
    from test_combi_advisor_contract import fixture

    original_kickoff = datetime.fromisoformat(fixture(1)['kickoff_iso'])
    alias = fixture(18)
    alias.update(home_team='Local 1', away_team='Visitante 1',
                 competition_name=competition, source='API-Football',
                 kickoff_iso=(original_kickoff + timedelta(minutes=minute_offset)).isoformat())
    with sqlite3.connect(db) as conn:
        if competition == 'Spanish La Liga':
            conn.execute("UPDATE matches SET competition_name='La Liga' WHERE id='m1'")
        conn.execute('INSERT INTO matches VALUES ('+','.join('?' for _ in alias)+')', list(alias.values()))

    assert catalogue(db)['total'] == 18


def test_known_provider_team_name_variants_render_as_one_fixture(db):
    from test_combi_advisor_contract import fixture

    alias = fixture(18)
    alias.update(home_team='Tottenham Hotspur', away_team='Coventry City',
                 competition_name='Premier League', source='API-Football',
                 kickoff_iso=fixture(1)['kickoff_iso'])
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE matches SET home_team='Tottenham', away_team='Coventry' WHERE id='m1'")
        conn.execute("UPDATE matches SET competition_name='Premier League' WHERE id='m1'")
        conn.execute('INSERT INTO matches VALUES ('+','.join('?' for _ in alias)+')', list(alias.values()))

    cat = catalogue(db)
    variants = [m for m in cat['matches'] if m['home'] in {'Tottenham', 'Tottenham Hotspur'}
                and m['away'] in {'Coventry', 'Coventry City'}]

    assert cat['total'] == 17
    assert len(variants) == 1


@pytest.mark.parametrize('status',['LIVE','HT','FT','PST','CANC','ABD','SUSP'])
def test_other_states_cannot_enter_future_catalogue(db,status):
    with sqlite3.connect(db) as conn:conn.execute('UPDATE matches SET status=? WHERE id=?',(status,'m1'))
    assert 'm1' not in {m['id'] for m in catalogue(db)['matches']}


def test_featured_first_but_search_does_not_return_irrelevant_matches(db):
    with sqlite3.connect(db) as conn:conn.execute("UPDATE matches SET competition_name='UEFA Champions League' WHERE id='m17'")
    assert catalogue(db)['matches'][0]['id']=='m17'
    cat=catalogue(db,{'q':'Local 2'})
    assert [m['id'] for m in cat['matches']]==['m2']


def test_search_is_case_and_accent_insensitive_and_not_like_wildcard(db):
    with sqlite3.connect(db) as conn:conn.execute("UPDATE matches SET home_team='Córdoba FC' WHERE id='m1'")
    assert [m['id'] for m in catalogue(db,{'q':'CORDOBA'})['matches']]==['m1']
    assert catalogue(db,{'q':'%'})['total']==0
    assert catalogue(db,{'q':"' OR 1=1 --"})['total']==0


def test_query_precedes_safety_limit(db,monkeypatch):
    from engines import combi_match_catalogue as mod
    monkeypatch.setattr(mod,'SCAN_LIMIT',2)
    assert catalogue(db)['truncated']
    cat=catalogue(db,{'q':'Local 17'})
    assert cat['total']==1 and not cat['truncated']


def test_date_invalid_and_missing_search_are_explicit(db):
    with pytest.raises(CombiError):catalogue(db,{'day':'2026-99-99'})
    assert catalogue(db,{'q':'No such team'})['state']=='EMPTY'


@pytest.mark.parametrize('price',[None,'0','nan','1','-2'])
def test_bad_prices_not_eligible(db,price):
    quotes(db,ids=(1,),home_price=price)
    group=next(m for m in catalogue(db)['matches'] if m['id']=='m1')['groups'][0]
    assert not group['choices'][0]['eligible']


def test_old_quote_is_visible_as_recorded_but_cannot_be_selected(db):
    quotes(db,ids=(1,),created_at=(NOW-timedelta(hours=1)).isoformat())
    group=next(m for m in catalogue(db)['matches'] if m['id']=='m1')['groups'][0]
    assert all(not p['eligible'] for p in group['choices'])


def test_save_market_choices_without_creating_editorial_picks(db):
    quotes(db)
    with sqlite3.connect(db) as conn:conn.execute('DELETE FROM picks')
    values={'pick_ids':ids_for_two(db),'stake':'0.10'}
    result=store.make_preview(db,'a',values,now=NOW)
    assert result['total_odds']=='3.2400' and result['probability'] is None
    import secrets
    saved=store.save_draft(db,'a',{**values,'request_id':secrets.token_hex(16),'revision':result['revision']},now=NOW)
    reviewed=review_draft(db,'a',saved['id'],now=NOW)
    assert reviewed['can_prepare'] and reviewed['original_unchanged']
    with sqlite3.connect(db) as conn:assert conn.execute('SELECT COUNT(*) FROM picks').fetchone()[0]==0
    assert store.read_center(db,'b',now=NOW)['saved']==[]


def test_quote_change_requires_new_confirmation_and_review(db):
    quotes(db);values={'pick_ids':ids_for_two(db),'stake':'0.10'}
    old=store.make_preview(db,'a',values,now=NOW)
    quotes(db,ids=(1,),id='q1-later',home_price='2.00',created_at=(NOW+timedelta(seconds=1)).isoformat())
    new=store.make_preview(db,'a',values,now=NOW+timedelta(seconds=2))
    assert old['revision']!=new['revision']
    import secrets
    with pytest.raises(CombiError,match='cambiado'):
        store.save_draft(db,'a',{**values,'request_id':secrets.token_hex(16),'revision':old['revision']},now=NOW+timedelta(seconds=2))


def test_anchor_cannot_silently_change_its_fixture_or_book(db):
    quotes(db);ids=ids_for_two(db)
    with sqlite3.connect(db) as conn:conn.execute("UPDATE odds_snapshots SET bookmaker='Otra casa' WHERE id='q1'")
    with pytest.raises(CombiError):store.make_preview(db,'a',{'pick_ids':ids,'stake':'0.10'},now=NOW)


def test_no_same_match_twice_even_with_1x2_options(db):
    quotes(db,ids=(1,))
    m=next(m for m in catalogue(db)['matches'] if m['groups'])
    ids=[p['id'] for p in m['groups'][0]['choices'][:2]]
    with pytest.raises(CombiError,match='mismo partido'):store.make_preview(db,'a',{'pick_ids':ids,'stake':'0.10'},now=NOW)


def test_mixed_bookmaker_and_permission_rules_unchanged(db):
    quotes(db,ids=(1,));quotes(db,ids=(2,),bookmaker='Otra casa')
    with pytest.raises(CombiError,match='misma casa'):store.make_preview(db,'a',{'pick_ids':ids_for_two(db),'stake':'0.10'},now=NOW)
    assert all(not p['eligible'] for m in catalogue(db,user='f')['matches'] for g in m['groups'] for p in g['choices'])


def test_paid_combi_tiers_see_verified_market_reading_but_free_does_not(db):
    quotes(db, ids=(1,))
    provider_quote_clock(db, ids=(1,))

    pro_group = next(m for m in catalogue(db, user='b')['matches'] if m['id']=='m1')['groups'][0]
    elite_group = next(m for m in catalogue(db, user='a')['matches'] if m['id']=='m1')['groups'][0]
    free_group = next(m for m in catalogue(db, user='f')['matches'] if m['id']=='m1')['groups'][0]

    for group in (pro_group, elite_group):
        reading = group['market_reading']
        assert reading['available'] and reading['state']=='CURRENT'
        assert reading['source']=='The Odds API' and reading['bookmaker']=='Casa QA'
        assert sum(reading['probabilities'].values())==100.0
        assert all(p['market_implied_probability_pct'] is not None for p in group['choices'])
        assert all(p['eligible'] for p in group['choices'])
    assert free_group['market_reading']['state']=='PLAN_LOCKED'
    assert all(not p['eligible'] for p in free_group['choices'])


@pytest.mark.parametrize('field,value', [
    ('quote_id', 'another-snapshot'),
    ('observed_at', (NOW + timedelta(seconds=1)).isoformat()),
    ('bookmaker', 'Otra casa'),
])
def test_market_reference_rejects_sides_from_different_quotes(field,value):
    from engines.combi_match_catalogue import _market_reading

    choices = [
        {'selection': selection, 'eligible': True, 'quote_clock_scope': 'PROVIDER_QUOTE_TIME',
         'odds_source': 'The Odds API', 'quote_id': 'snapshot-1', 'observed_at': NOW.isoformat(),
         'bookmaker': 'Casa QA', 'odds': price}
        for selection, price in [('1', '1.80'), ('X', '3.00'), ('2', '4.00')]
    ]
    choices[2][field] = value

    reading = _market_reading(choices, {'membership': 'PRO'})

    assert reading['available'] is False
    assert reading['state'] == 'INCONSISTENT_QUOTES'
    assert reading['probabilities'] == {}


def test_current_market_reference_is_read_only_and_uses_no_provider_calls(db):
    quotes(db, ids=(1,))
    provider_quote_clock(db, ids=(1,))
    before = open(db, 'rb').read()

    center = store.read_center(db, 'b', now=NOW, catalogue_filters={'q': 'Local 1'})
    group = next(match for match in center['catalogue']['matches'] if match['id'] == 'm1')['groups'][0]

    assert group['market_reading']['available'] is True
    assert center['external_calls'] == 0
    assert open(db, 'rb').read() == before


def test_market_reading_explains_when_provider_quote_time_is_not_verified(db):
    quotes(db, ids=(1,))
    group = next(m for m in catalogue(db, user='b')['matches'] if m['id']=='m1')['groups'][0]
    assert group['market_reading']['state']=='PROVIDER_TIME_UNVERIFIED'
    assert 'hora original confirmada' in group['market_reading']['message']


def test_preview_retains_market_probability_from_the_same_provider_quote(db):
    quotes(db)
    provider_quote_clock(db)
    ids=ids_for_two(db)
    result=store.make_preview(db,'b',{'pick_ids':ids,'stake':'0.10'},now=NOW)
    assert all(leg['quote_clock_scope']=='PROVIDER_QUOTE_TIME' for leg in result['legs'])
    assert all(leg['market_implied_probability_pct'] is not None for leg in result['legs'])
    assert result['probability'] is None and result['not_a_bet']


def test_deleted_observation_is_not_replaced_by_an_arbitrary_choice(db):
    quotes(db);ids=ids_for_two(db)
    with sqlite3.connect(db) as conn:conn.execute("DELETE FROM odds_snapshots WHERE id='q1'")
    with pytest.raises(CombiError):store.make_preview(db,'a',{'pick_ids':ids,'stake':'0.10'},now=NOW)


def test_first_search_page_is_not_only_searchable_area(db,monkeypatch):
    from engines import combi_match_catalogue as mod
    monkeypatch.setattr(mod,'PAGE_SIZE',2)
    cat=catalogue(db,{'q':'Local 17'})
    assert len(cat['matches'])==1 and cat['matches'][0]['id']=='m17'


def test_wrong_team_snapshot_cannot_offer_odds(db):
    quotes(db,ids=(1,),home_team='Otro equipo')
    assert not next(m for m in catalogue(db)['matches'] if m['id']=='m1')['groups']


def test_bound_overflow_does_not_report_no_odds(db,monkeypatch):
    quotes(db)
    from engines import combi_match_catalogue as mod
    old=mod._odds
    monkeypatch.setattr(mod,'_odds',lambda *a:(old(*a)[0],True))
    assert catalogue(db)['quote_truncated']
    assert all(not p['eligible'] for m in catalogue(db)['matches'] for g in m['groups'] for p in g['choices'])

@pytest.mark.parametrize('field,value',[('market_closed',True),('suspended','true'),('status','removed')])
def test_explicit_closed_snapshot_is_not_usable(db,field,value):
    quotes(db,ids=(1,))
    with sqlite3.connect(db) as conn:
        conn.execute('ALTER TABLE odds_snapshots ADD COLUMN payload_json TEXT')
        conn.execute('UPDATE odds_snapshots SET payload_json=?',(json.dumps({field:value}),))
    group=next(m for m in catalogue(db)['matches'] if m['id']=='m1')['groups'][0]
    assert not any(p['eligible'] for p in group['choices'])
