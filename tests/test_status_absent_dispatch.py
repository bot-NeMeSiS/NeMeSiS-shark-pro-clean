"""Absent status fields must not allocate/dispatch status-source work."""
import cProfile
import pstats
from types import CodeType
from engines import v935_launch_trust_engine as truth


def test_sparse_status_collects_one_present_signal_without_absent_dispatch():
    helper=next(c for c in truth._status_values.__code__.co_consts
                if isinstance(c,CodeType) and c.co_name=='add')
    profile=cProfile.Profile()
    profile.enable()
    try:
        result=truth._status_values({'status':'LIVE','fixture':{},'raw_json':{},'payload_json':{}})
    finally:
        profile.disable()
    calls=sum(v[1] for (file,line,name),v in pstats.Stats(profile).stats.items()
              if file==helper.co_filename and line==helper.co_firstlineno and name=='add')
    assert result==[('status','live')]
    assert calls==1, f'Unnecessary absent status dispatch: {calls} calls for one present signal'
