"""Technical run outcome is independent from content and publication rights."""
PASS_REASONS = {'COMPLETE','NO_VIDEO','NO_STATISTICS','NO_EVENT','RIGHTS_REVIEW',
                'CONFLICT','AMBIGUOUS_MATCH','IDENTITY_MISMATCH','AMBIGUOUS_VIDEO',
                'IDENTITY_CHANGED','NOT_FINAL','SOURCE_NOT_FINAL','UNSUPPORTED_STATISTICS',
                'EMPTY_STATISTIC_VALUES','NO_POSTMATCH_DETAILS'}
DEFERRED_REASONS = {'DAILY_BUDGET','TICK_BUDGET','SOURCE_COOLDOWN','PARTIAL_COVERAGE',
                    'MISSING_PROVIDER_ID','VIDEO_LOOKUP_UNAVAILABLE','HIGHLIGHT_RESPONSE_LIMIT',
                    'PAUSED_OR_RECLAIMED','NO_APPROVED_SOURCE','SOURCE_DISABLED','SOURCE_NOT_ALLOWED',
                    'MEDIA_PENDING','ARCHIVE_BUDGET'}
TECHNICAL_REASONS = {'ACCESS_DENIED','RATE_LIMIT','NETWORK','MALFORMED','REDIRECT_BLOCKED','MISSING_KEY',
                    'INVALID_STATISTIC','CONFLICTING_STATISTICS','INCONSISTENT_STATISTICS','INVALID_VIDEO_URL',
                    'INTERNAL_ERROR','STORAGE_UNAVAILABLE'}


def postmatch_outcome(jobs):
    if any(not isinstance(job,dict) or job.get('state') not in
           {'COMPLETE','RETRY','PARTIAL','REVIEW_REQUIRED','CANCELLED','LEASE_LOST'} for job in jobs):
        return 'FAIL'
    reasons = {job.get('reason') for job in jobs}
    if any(job.get('technical_errors') for job in jobs):
        return 'FAIL'
    if reasons - PASS_REASONS - DEFERRED_REASONS:
        return 'FAIL'
    return 'PARTIAL' if reasons & DEFERRED_REASONS else 'PASS'
