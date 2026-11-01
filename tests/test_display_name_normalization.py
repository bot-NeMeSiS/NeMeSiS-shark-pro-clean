"""Compare the deterministic text contract with immutable published functions."""
import hashlib
import re
import unicodedata
import pytest
from display_name_baseline import SOURCES
from engines import display_name_normalization as normalized
from engines import team_identity_engine as teams
from engines import spanish_localization_engine as spanish

def legacy(key):
    entry=SOURCES[key]
    assert hashlib.sha256(entry["source"].encode()).hexdigest()==entry["sha256"]
    scope={"re":re,"unicodedata":unicodedata}
    exec(compile("from __future__ import annotations\n"+entry["source"],"<published-name-formatter>","exec"),scope)
    return scope["_title_preserving_acronyms" if key=="TITLE" else "_norm"]

WORDS=[None,False,0,0.0,True,1,[],{},(),{"x":1},"A💥B","Atlético C.F. Women U19","A\u0301Bc","   fC  Porto ","Sevilla FC","\0A\tB","ß I İ ı","ＡＢＣ","\u00a0x\u200dy","x"*129,"x"*2048,"İstanbul","L'Équipe","Real-Madrid","A💥💥B","ﬃ Ⅷ ²"]
WORDS += [chr(i)+"A B"+chr(0x300+i%96) for i in range(0,200)]
@pytest.mark.parametrize("value",WORDS)
def test_normalizers_keep_published_output(value):
    assert teams._norm(value)==legacy("TEAM_NORM")(value)
    assert spanish._norm(value)==legacy("SPANISH_NORM")(value)

@pytest.mark.parametrize("word",["Atletico","Mexico","Copa America","Division","Brasileirao"])
@pytest.mark.parametrize("shape",["{}","pre {} post","{}suffix","prefix{}","_{}_","{}!"])
def test_precompiled_title_rules_keep_replacement_and_boundary_behavior(word,shape):
    value=shape.format(word)
    for text in (value,value.lower(),value.upper()):
        assert spanish._title_preserving_acronyms(text)==legacy("TITLE")(text)

@pytest.mark.parametrize("truthy",[False,True])
def test_truth_and_string_conversion_are_current_even_on_cache_hit(truthy):
    class Input:
        def __init__(self,text):self.text=text;self.events=[]
        def __bool__(self):self.events.append("bool");return truthy
        def __str__(self):self.events.append("str");return self.text
    x=Input("Harbor FC")
    for text in ("Harbor FC","Harbor FC","Another FC"):
        x.text=text;x.events=[]
        got=normalized.display_name_key(x)
        y=Input(text);expected=legacy("TEAM_NORM")(y)
        assert got==expected and x.events==y.events

def test_unhashable_custom_text_does_not_enter_the_cache():
    class Text(str):
        __hash__=None
        def __str__(self):return self
        def strip(self,*args,**kwargs):return self
        def lower(self):return self
    x=Text("already lower")
    assert normalized.display_name_key(x)==legacy("TEAM_NORM")(Text("already lower"))

def test_cache_is_bounded_and_long_inputs_are_not_retained():
    cache=normalized._normalize_short_text
    cache.cache_clear()
    try:
        for i in range(2100):normalized.display_name_key("club "+str(i))
        assert cache.cache_info().maxsize==2048 and cache.cache_info().currsize==2048
        before=cache.cache_info()
        assert normalized.display_name_key("a"*129)=="a"*129
        assert cache.cache_info()==before
        normalized.display_name_key("club 2099")
        assert cache.cache_info().hits==before.hits+1
    finally:cache.cache_clear()

def test_provider_alias_lookup_stays_current_after_text_cache_hit(monkeypatch):
    value="QA Mutable Alias"
    key=teams._norm(value)
    monkeypatch.setitem(teams._PROVIDER_TEAM_IDENTITY_ALIASES,key,"first current alias")
    assert teams.provider_team_identity_key(value)=="first current alias"
    monkeypatch.setitem(teams._PROVIDER_TEAM_IDENTITY_ALIASES,key,"second current alias")
    assert teams.provider_team_identity_key(value)=="second current alias"

@pytest.mark.parametrize("replacement",[None,"","Nuevo nombre"])
def test_spanish_override_lookup_is_never_cached(monkeypatch,replacement):
    value="QA Translation Alias";key=spanish._norm(value)
    monkeypatch.setitem(spanish.SPANISH_TEAM_OVERRIDES,key,"Nombre anterior")
    assert spanish.spanish_team_name(value)=="Nombre anterior"
    monkeypatch.setitem(spanish.SPANISH_TEAM_OVERRIDES,key,replacement)
    assert spanish.spanish_team_name(value) is replacement
