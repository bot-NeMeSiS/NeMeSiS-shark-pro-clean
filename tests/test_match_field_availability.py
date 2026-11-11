from engines.match_field_availability import match_field_availability

def fields(context):
    return {v['key']:v for v in match_field_availability(context)['fields']}

def test_seven_fields_missing_cannot_be_inferred_from_provider_or_plan():
    result=fields({'provider':'api_football','plan':'PRO','coverage':{'lineups':True}})
    assert len(result)==7
    assert result['minute']['state']=='NOT_APPLICABLE'
    assert all(v['state']=='NOT_ESTABLISHED' for k,v in result.items() if k!='minute')

def test_zero_score_and_minute_are_recorded_but_missing_formation_is_explicit():
    result=fields({'score':{'confirmed':True,'home':0,'away':0},
        'lifecycle':{'is_live':True,'minute':0},
        'lineups':{'confirmed':True,'player_count':22,
                   'teams':[{'formation':'4-3-3'},{'formation':None}]}})
    assert result['score']['state']=='RECORDED'
    assert result['minute']['state']=='RECORDED'
    assert result['players']['state']=='RECORDED'
    assert result['formation']['state']=='PARTIAL'
    assert result['formation']['available'] is False

def test_finished_minute_is_inapplicable_even_if_legacy_value_remains():
    result=fields({'lifecycle':{'is_live':False,'minute':90},
        'statistics':{'available':True},'event_summary':{'available':True}})
    assert result['minute']['state']=='NOT_APPLICABLE'
    assert result['minute']['available'] is False
    assert result['statistics']['state']==result['events']['state']=='RECORDED'
