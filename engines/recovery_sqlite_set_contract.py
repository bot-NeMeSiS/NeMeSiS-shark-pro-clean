"""Closed metadata contract for a COMPLETE declared SQLite set.

This is not a capture capability, a data-operation permission, or proof of
cross-store quiescence. It never opens files or chooses restore destinations.
"""
from dataclasses import dataclass
import re

MAX_MEMBERS = 8
MAX_TOTAL_BYTES = 4 * 1024 * 1024 * 1024
SCHEMA = "SQLITE_SET_RECEIPT_V1"
_ID = re.compile(r"principal|aux_[a-z0-9_]{1,40}")
_REF = re.compile(r"[A-Z0-9_-]{1,96}")
_HEX = re.compile(r"[0-9a-f]{64}")
_CAPTURE = re.compile(r"[0-9a-f]{32}")
_FILE = re.compile(r"database_[0-9a-f]{32}\.db")
_DECIMAL = re.compile(r"[0-9]{10}")


class SqliteSetContractError(ValueError):
    """Closed codes only."""


def member_budgets(value):
    if (type(value) is not tuple or not 2 <= len(value) <= MAX_MEMBERS
            or any(type(pair) is not tuple or len(pair) != 2 for pair in value)):
        raise SqliteSetContractError("INVALID_SQLITE_SET_MEMBERS")
    ids = tuple(pair[0] for pair in value)
    quotas = tuple(pair[1] for pair in value)
    if (any(type(v) is not str or _ID.fullmatch(v) is None for v in ids)
            or ids[0] != "principal" or ids[1:] != tuple(sorted(ids[1:]))
            or len(set(ids)) != len(ids)
            or any(type(q) is not int or not 0 < q <= MAX_TOTAL_BYTES for q in quotas)
            or sum(quotas) > MAX_TOTAL_BYTES):
        raise SqliteSetContractError("INVALID_SQLITE_SET_MEMBERS")
    return value


@dataclass(frozen=True)
class SqliteSetMemberReceipt:
    source_id: str
    capture_id: str
    backup_file: str
    sha256: str
    size_bytes: int
    maximum_bytes: int

    def __post_init__(self):
        if (type(self.source_id) is not str or _ID.fullmatch(self.source_id) is None
                or type(self.capture_id) is not str or _CAPTURE.fullmatch(self.capture_id) is None
                or type(self.backup_file) is not str or _FILE.fullmatch(self.backup_file) is None
                or type(self.sha256) is not str or _HEX.fullmatch(self.sha256) is None
                or type(self.maximum_bytes) is not int
                or not 0 < self.maximum_bytes <= MAX_TOTAL_BYTES
                or type(self.size_bytes) is not int
                or not 0 < self.size_bytes <= self.maximum_bytes):
            raise SqliteSetContractError("INVALID_SQLITE_SET_MEMBER_RECEIPT")


@dataclass(frozen=True)
class SqliteSetReceipt:
    artifact_id: str
    members: tuple[SqliteSetMemberReceipt, ...]
    published_and_validated: bool

    def __post_init__(self):
        if (type(self.artifact_id) is not str or _REF.fullmatch(self.artifact_id) is None
                or self.published_and_validated is not True
                or type(self.members) is not tuple
                or any(type(m) is not SqliteSetMemberReceipt for m in self.members)):
            raise SqliteSetContractError("SQLITE_SET_RECEIPT_NOT_VERIFIED")
        for member in self.members:
            SqliteSetMemberReceipt.__post_init__(member)
        member_budgets(tuple((m.source_id, m.maximum_bytes) for m in self.members))
        if (len({m.capture_id for m in self.members}) != len(self.members)
                or len({m.backup_file for m in self.members}) != len(self.members)):
            raise SqliteSetContractError("DUPLICATE_SQLITE_SET_CAPTURE")


def _member_record(member):
    return {"source_id": member.source_id, "capture_id": member.capture_id,
            "backup_file": member.backup_file, "sha256": member.sha256,
            # Fixed widths let the owner size the manifest BEFORE capture.
            "size_bytes": f"{member.size_bytes:010d}",
            "maximum_bytes": f"{member.maximum_bytes:010d}"}


def to_record(receipt):
    if type(receipt) is not SqliteSetReceipt:
        raise SqliteSetContractError("SQLITE_SET_RECEIPT_NOT_VERIFIED")
    # Revalidate the complete object rather than inheriting another member's state.
    SqliteSetReceipt(receipt.artifact_id, receipt.members, receipt.published_and_validated)
    return {"schema": SCHEMA, "artifact_id": receipt.artifact_id,
            "published_and_validated": True,
            "members": [_member_record(m) for m in receipt.members]}


def _decimal(value):
    if type(value) is not str or _DECIMAL.fullmatch(value) is None:
        raise SqliteSetContractError("NONCANONICAL_SQLITE_SET_BYTES")
    result = int(value)
    if value != f"{result:010d}":
        raise SqliteSetContractError("NONCANONICAL_SQLITE_SET_BYTES")
    return result


def from_record(value):
    if (type(value) is not dict
            or set(value) != {"schema", "artifact_id", "published_and_validated", "members"}
            or value["schema"] != SCHEMA or value["published_and_validated"] is not True
            or type(value["members"]) is not list
            or not 2 <= len(value["members"]) <= MAX_MEMBERS):
        raise SqliteSetContractError("SQLITE_SET_RECEIPT_NOT_VERIFIED")
    fields = {"source_id", "capture_id", "backup_file", "sha256", "size_bytes", "maximum_bytes"}
    members = []
    for item in value["members"]:
        if type(item) is not dict or set(item) != fields:
            raise SqliteSetContractError("INVALID_SQLITE_SET_MEMBER_RECEIPT")
        members.append(SqliteSetMemberReceipt(
            item["source_id"], item["capture_id"], item["backup_file"], item["sha256"],
            _decimal(item["size_bytes"]), _decimal(item["maximum_bytes"])))
    receipt = SqliteSetReceipt(value["artifact_id"], tuple(members), value["published_and_validated"])
    if to_record(receipt) != value:
        raise SqliteSetContractError("NONCANONICAL_SQLITE_SET_RECEIPT")
    return receipt


def sizing_record(artifact_id, budgets):
    """Shape mask only: null publication and zero sizes are NOT a valid receipt."""
    member_budgets(budgets)
    if type(artifact_id) is not str or _REF.fullmatch(artifact_id) is None:
        raise SqliteSetContractError("INVALID_SQLITE_SET_ARTIFACT")
    return {"schema": SCHEMA, "artifact_id": artifact_id, "published_and_validated": None,
            "members": [{"source_id": label, "capture_id": "0" * 32,
                         "backup_file": "database_" + "0" * 32 + ".db", "sha256": "0" * 64,
                         "size_bytes": "0" * 10, "maximum_bytes": f"{quota:010d}"}
                        for label, quota in budgets]}
