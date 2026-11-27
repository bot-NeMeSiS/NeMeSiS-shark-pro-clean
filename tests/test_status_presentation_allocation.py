"""Status presentation keeps fresh truth and independent mutable outputs."""
import pytest


@pytest.mark.parametrize("lifecycle,key,label,badge,flags", [
    ("LIVE", "LIVE", "En directo", "live", (True, False, False, False)),
    ("HALFTIME", "HT", "Descanso", "halftime", (True, False, False, False)),
    ("FINISHED", "FT", "Finalizado", "finished", (False, True, False, False)),
    ("ARCHIVED", "FT", "Finalizado", "finished", (False, True, False, False)),
    ("RESULT_PENDING", "RESULT_PENDING", "Resultado pendiente", "result_pending", (False, False, True, False)),
    ("SUSPENDED", "SUSPENDED", "Suspendido", "incident", (False, False, False, False)),
    ("POSTPONED", "POSTPONED", "Aplazado", "incident", (False, False, False, False)),
    ("CANCELLED", "CANCELLED", "Cancelado", "incident", (False, False, False, False)),
    ("ABANDONED", "ABANDONED", "Abandonado", "incident", (False, False, False, False)),
    ("STALE", "STALE", "Actualización pendiente", "incomplete", (False, False, False, False)),
    ("UPCOMING", "UPCOMING", "Próximo", "upcoming", (False, False, False, True)),
    ("INCOMPLETE", "INCOMPLETE", "Estado pendiente", "incomplete", (False, False, False, False)),
    ("UNKNOWN", "INCOMPLETE", "Estado pendiente", "incomplete", (False, False, False, False)),
])
def test_lifecycle_presentation_contract(app_module, monkeypatch, lifecycle, key, label, badge, flags):
    monkeypatch.setattr(app_module, "v935_match_status_truth", lambda row, now=None: {"lifecycle": lifecycle})
    result = app_module.canonical_match_status({"id": "owned"})
    assert (result["key"], result["label"], result["badge"]) == (key, label, badge)
    assert tuple(result[name] for name in ("is_live", "is_finished", "is_result_pending", "is_upcoming")) == flags
    assert result["raw_lifecycle"] == lifecycle
    assert result["contract"] == "MATCH-STATUS-TRUTH-V2"


def test_status_is_recomputed_and_outputs_do_not_alias(app_module, monkeypatch):
    calls = []
    signals = ["live"]
    truth = {"lifecycle": "LIVE", "signal_kinds": signals, "live_age_seconds": 2}
    def observed_truth(row, now=None):
        calls.append((row.copy(), now))
        return truth
    monkeypatch.setattr(app_module, "v935_match_status_truth", observed_truth)
    row = {"id": "owned", "status": "LIVE"}
    first = app_module.canonical_match_status(row, now="first-observation")
    first["label"] = "caller edit"
    first["signal_kinds"].append("caller edit")
    row["status"] = "FT"
    truth.update(lifecycle="FINISHED", live_age_seconds=7, is_stale=True, stale_reason="fresh", contract="observed-contract")
    second = app_module.canonical_match_status(row, now="second-observation")
    assert calls == [({"id": "owned", "status": "LIVE"}, "first-observation"), ({"id": "owned", "status": "FT"}, "second-observation")]
    assert second["label"] == "Finalizado"
    assert second["signal_kinds"] == signals == ["live"]
    assert (second["live_age_seconds"], second["is_stale"], second["stale_reason"], second["contract"]) == (7, True, "fresh", "observed-contract")
    truth.update(lifecycle="LIVE", status_conflict=True, conflict_type="score")
    third = app_module.canonical_match_status(row)
    assert third["is_live"] is False
    assert third["conflict_type"] == "score"
    assert third["label"] == "En directo"
