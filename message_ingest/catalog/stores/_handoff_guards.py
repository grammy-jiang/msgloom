"""Install additive ledger guards without changing transaction ownership."""

from sqlalchemy import Connection

# Each tuple is one complete unique key, including alternate unique keys.
# SQLite rowid is another replacement key even for text/composite PKs.
# BEFORE INSERT runs even when SQLite REPLACE suppresses DELETE triggers.
_IMMUTABLE_KEYS = {
    "acquisition_facts": (("fact_id",), ("staging_key",)),
    "acquisition_release_groups": (("release_group_id",),),
    "acquisition_release_entries": (("release_entry_seq",),),
    "acquisition_release_entry_facts": (("release_entry_seq", "ordinal"),),
    "acquisition_ledger_metadata": (("singleton",), ("catalog_identity",)),
    "acquisition_run_outcomes": (("run_id", "attempt_id"),),
}


def install_guards(connection: Connection) -> None:
    """
    Protect existing and new ledgers with recursive triggers disabled.

    Install inside the caller's additive schema transaction. API retries read
    existing rows before inserting; conflicting raw SQL is always rejected.
    The mutable effective-state index deliberately has no immutable guard.
    """
    for table, keys in _IMMUTABLE_KEYS.items():
        for operation in ("UPDATE", "DELETE"):
            connection.exec_driver_sql(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} "
                f"BEFORE {operation} ON {table} BEGIN "
                "SELECT RAISE(ABORT, 'immutable acquisition ledger row'); END"
            )
        conflicts = " OR ".join(
            "(" + " AND ".join(f"{name}=NEW.{name}" for name in key) + ")"
            for key in (*keys, ("rowid",))
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_INSERT "
            f"BEFORE INSERT ON {table} "
            f"WHEN EXISTS (SELECT 1 FROM {table} WHERE {conflicts}) BEGIN "
            "SELECT RAISE(ABORT, 'immutable acquisition ledger row'); END"
        )
    connection.exec_driver_sql(
        """
        CREATE TRIGGER IF NOT EXISTS canonical_acquisition_entry_member
        BEFORE INSERT ON acquisition_release_entry_facts
        WHEN NOT EXISTS (
            SELECT 1 FROM acquisition_release_entries AS entry,
                json_each(entry.payload, '$.facts') AS member
            WHERE entry.release_entry_seq=NEW.release_entry_seq
                AND length(CAST(entry.payload AS BLOB)) <= 65536
                AND json_type(entry.payload, '$.facts')='array'
                AND json_array_length(entry.payload, '$.facts') BETWEEN 1 AND 128
                AND typeof(NEW.ordinal)='integer'
                AND NEW.ordinal BETWEEN 0 AND 127
                AND member.key=NEW.ordinal
                AND member.type='array'
                AND json_array_length(member.value)=2
                AND json_extract(member.value, '$[0]')=NEW.fact_id
                AND json_extract(member.value, '$[1]')=NEW.role
        )
        BEGIN
            SELECT RAISE(ABORT, 'noncanonical acquisition entry membership');
        END
        """
    )
