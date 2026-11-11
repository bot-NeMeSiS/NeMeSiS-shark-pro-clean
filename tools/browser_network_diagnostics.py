"""Bounded metadata for owned browser QA; never reads headers or payloads."""
from collections import deque
from time import monotonic
from urllib.parse import urlsplit


class BrowserNetworkDiagnostics:
    def __init__(self):
        self.started = monotonic()
        self.events = deque(maxlen=512)
        self.pending = {}
        self.case = {}
        self.sequence = 0
        self.dropped_events = 0
        self.untracked_requests = 0
        self.unmatched_terminal_events = 0
        self.failure = None

    def set_case(self, width, role, path):
        self.case = {"width": width, "role": role, "path": path}

    def _elapsed(self):
        return round((monotonic() - self.started) * 1000, 3)

    @staticmethod
    def _copy(row):
        return {**row, "case": dict(row["case"])}

    def _record(self, event, info):
        if len(self.events) == self.events.maxlen:
            self.dropped_events += 1
        self.events.append({**self._copy(info), "event": event, "elapsed_ms": self._elapsed()})

    def request_started(self, request):
        self.sequence += 1
        info = {"sequence": self.sequence, "case": dict(self.case),
                "path": urlsplit(request.url).path[:240], "method": request.method,
                "resource_type": request.resource_type,
                "navigation": request.is_navigation_request(), "started_ms": self._elapsed()}
        if len(self.pending) < 128:
            self.pending[id(request)] = info
        else:
            self.untracked_requests += 1
        self._record("request", info)

    def _terminal(self, request, event):
        info = self.pending.pop(id(request), None)
        if info is None:
            self.unmatched_terminal_events += 1
            return
        self._record(event, info)

    def request_finished(self, request):
        self._terminal(request, "requestfinished")

    def request_failed(self, request):
        self._terminal(request, "requestfailed")

    def capture_failure(self, error_type, *, phase, timeout_ms):
        self.failure = {"error_type": error_type, "phase": phase, "timeout_ms": timeout_ms,
                        "case": dict(self.case), "elapsed_ms": self._elapsed(),
                        "pending": [self._copy(row) for row in self.pending.values()]}

    def snapshot(self):
        return {"scope": "OWNED_BROWSER_METADATA_ONLY", "event_limit": 512, "pending_limit": 128,
                "events": [self._copy(row) for row in self.events],
                "pending": [self._copy(row) for row in self.pending.values()],
                "failure": self.failure, "dropped_events": self.dropped_events,
                "untracked_requests": self.untracked_requests,
                "unmatched_terminal_events": self.unmatched_terminal_events,
                "complete_history": not self.dropped_events and not self.untracked_requests
                                    and not self.unmatched_terminal_events}
