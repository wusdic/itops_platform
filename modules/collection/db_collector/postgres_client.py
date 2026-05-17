"""PostgreSQL metrics collector."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import psycopg2
except ImportError:
    psycopg2 = None


@dataclass
class PostgreSQLConfig:
    """PostgreSQL connection configuration."""

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "postgres"
    connect_timeout: int = 10

    @property
    def dsn(self) -> str:
        return f"{self.user}:***@{self.host}:{self.port}/{self.database}"


class PostgreSQLCollector:
    """Collects PostgreSQL metrics via pg_stat_* views."""

    def __init__(self, config: PostgreSQLConfig):
        self.config = config
        self._conn: Optional["psycopg2.connection"] = None

    def _get_connection(self) -> "psycopg2.connection":
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed")
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                connect_timeout=self.config.connect_timeout,
            )
        return self._conn

    def _execute(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def collect_pg_stat_database(self) -> List[Dict[str, Any]]:
        """
        Collect pg_stat_database - databases activity metrics.
        Includes tup_returned, tup_fetched, tup_inserted, tup_updated, tup_deleted,
        conflicts, temp_files, deadlocks, blk_read_time, blk_write_time, stats_reset.
        """
        return self._execute("""
            SELECT datid, datname, numbackends, xact_commit, xact_rollback,
                   blks_read, blks_hit, tup_returned, tup_fetched,
                   tup_inserted, tup_updated, tup_deleted,
                   conflicts, temp_files, temp_bytes,
                   deadlocks, blk_read_time, blk_write_time,
                   stats_reset, datkaagent_start_time
            FROM pg_stat_database
            WHERE datname IS NOT NULL
        """)

    def collect_pg_stat_activity(self) -> List[Dict[str, Any]]:
        """
        Collect pg_stat_activity - current database connections and queries.
        Used for slow query detection and connection monitoring.
        """
        return self._execute("""
            SELECT pid, usename, application_name, client_addr, client_hostname,
                   backend_start, xact_start, query_start, state_change, wait_event,
                   state, query, backend_xid, backend_xmin, catalog_xid,
                   ssl, sslversion, sslcipher, sslbits, sslcompression,
                   usehost, usepeer
            FROM pg_stat_activity
            WHERE state IS NOT NULL
        """)

    def collect_pg_stat_bgwriter(self) -> Dict[str, Any]:
        """
        Collect pg_stat_bgwriter - background writer statistics.
        Measures buffer cache efficiency and checkpoint performance.
        """
        rows = self._execute("""
            SELECT checkpoints_timed, checkpoints_req, checkpoint_write_time,
                   checkpoint_sync_time, buffers_checkpoint, buffers_clean,
                   buffers_backend, buffers_alloc, buffers_backend_fsync,
                   maxwritten_clean, maxwritten_clean, stats_reset
            FROM pg_stat_bgwriter
        """)
        return rows[0] if rows else {}

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all PostgreSQL metrics including:
        - Connection count (active, idle, total)
        - Cache hit ratio
        - Transaction count (commits, rollbacks)
        - Slow queries (long-running queries)
        - Buffer stats from bgwriter
        """
        # Database stats
        db_stats = self.collect_pg_stat_database()

        # Activity stats
        activity = self.collect_pg_stat_activity()

        # BGWriter stats
        bgwriter = self.collect_pg_stat_bgwriter()

        # Aggregate connection counts
        total_connections = 0
        active_connections = 0
        idle_connections = 0
        idle_in_transaction = 0

        for row in activity:
            state = row.get("state")
            if state == "active":
                active_connections += 1
            elif state == "idle":
                idle_connections += 1
            elif state == "idle in transaction":
                idle_in_transaction += 1
            total_connections += 1

        # Slow queries: queries running longer than 30 seconds
        slow_queries = [
            {
                "pid": row["pid"],
                "usename": row.get("usename"),
                "query": row.get("query"),
                "duration_seconds": (
                    (row.get("query_start") and (row["query_start"]))
                ),
                "state": row.get("state"),
            }
            for row in activity
            if row.get("state") == "active"
            and row.get("query_start")
            and row.get("query") != "<IDLE>"
        ]

        # Aggregate database-level metrics
        total_commits = sum(int(r.get("xact_commit", 0)) for r in db_stats)
        total_rollbacks = sum(int(r.get("xact_rollback", 0)) for r in db_stats)
        total_blks_read = sum(int(r.get("blks_read", 0)) for r in db_stats)
        total_blks_hit = sum(int(r.get("blks_hit", 0)) for r in db_stats)
        cache_hit_ratio = (
            round(total_blks_hit / (total_blks_hit + total_blks_read) * 100, 2)
            if (total_blks_hit + total_blks_read) > 0
            else None
        )

        return {
            "connections": {
                "total": total_connections,
                "active": active_connections,
                "idle": idle_connections,
                "idle_in_transaction": idle_in_transaction,
            },
            "transactions": {
                "commits": total_commits,
                "rollbacks": total_rollbacks,
                "total": total_commits + total_rollbacks,
            },
            "cache": {
                "blks_hit": total_blks_hit,
                "blks_read": total_blks_read,
                "hit_ratio": cache_hit_ratio,
            },
            "slow_queries": slow_queries,
            "database_stats": db_stats,
            "bgwriter": bgwriter,
        }

    def close(self):
        """Close the connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
        self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
