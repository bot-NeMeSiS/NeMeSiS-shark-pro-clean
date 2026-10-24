"""Browser persistence bounded by the authenticated session's fixed expiry."""

from datetime import datetime, timezone

from flask.sessions import SecureCookieSessionInterface


class AbsoluteAuthSessionInterface(SecureCookieSessionInterface):
    """Keep signed-cookie renewal inside the existing revocation lifetime.

    Reads can modify Flask's session, for example when a membership changes.
    Re-signing that cookie must not extend the original authentication expiry.
    Account/version/revocation checks remain the application's responsibility.
    """

    def get_expiration_time(self, app, session):
        default = super().get_expiration_time(app, session)
        if not session.permanent or not session.get("user_id"):
            return default
        try:
            expiry = datetime.fromisoformat(str(session.get("auth_session_expires_at") or ""))
            if not session.get("auth_session_id") or expiry.tzinfo is None:
                raise ValueError("invalid authenticated session expiry")
            expiry = expiry.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            # Never fall back to a sliding lifetime for malformed auth state.
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
        return min(expiry, default) if default is not None else expiry
