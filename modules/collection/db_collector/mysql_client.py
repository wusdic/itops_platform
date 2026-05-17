"""MySQL metrics collector."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import pymysql
except ImportError:
    pymysql = None


@dataclass
class MySQLConfig:
    """MySQL connection configuration."""

    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    charset: str = "utf8mb4"
    connect_timeout: int = 10
    read_timeout: int = 30

    @property
    def dsn(self) -> str:
        return f"{self.user}:***@{self.host}:{self.port}/{self.database}"


class MySQLCollector:
    """Collects MySQL metrics via SHOW GLOBAL STATUS, InnoDB stats, etc."""

    def __init__(self, config: MySQLConfig):
        self.config = config
        self._conn: Optional["pymysql.Connection"] = None

    def _get_connection(self) -> "pymysql.Connection":
        if pymysql is None:
            raise RuntimeError("pymysql is not installed")
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                connect_timeout=self.config.connect_timeout,
                read_timeout=self.config.read_timeout,
            )
        return self._conn

    def _execute(self, sql: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()

    def _get_variable(self, var_name: str) -> Any:
        """Get a global variable value."""
        result = self._execute(f"SHOW GLOBAL STATUS LIKE '{var_name}'")
        return result[0]["Value"] if result else None

    def collect_global_status(self) -> Dict[str, Any]:
        """Collect SHOW GLOBAL STATUS metrics."""
        rows = self._execute("SHOW GLOBAL STATUS")
        return {row["Variable_name"]: row["Value"] for row in rows}

    def collect_innodb_stats(self) -> Dict[str, Any]:
        """Collect InnoDB engine statistics."""
        innodb_vars = [
            "Innodb_buffer_pool_pages_total",
            "Innodb_buffer_pool_pages_free",
            "Innodb_buffer_pool_pages_dirty",
            "Innodb_buffer_pool_reads",
            "Innodb_buffer_pool_read_requests",
            "Innodb_buffer_pool_write_requests",
            "Innodb_rows_read",
            "Innodb_rows_inserted",
            "Innodb_rows_updated",
            "Innodb_rows_deleted",
            "Innodb_data_read",
            "Innodb_data_written",
            "Innodb_log_writes",
            "Innodb_log_write_requests",
        ]
        stats = {}
        for var in innodb_vars:
            stats[var] = self._get_variable(var)
        return stats

    def collect_slave_status(self) -> Dict[str, Any]:
        """Collect SHOW SLAVE STATUS for replication monitoring."""
        rows = self._execute("SHOW SLAVE STATUS")
        if not rows:
            return {}
        row = rows[0]
        return {
            "slave_io_running": row.get("Slave_IO_Running"),
            "slave_sql_running": row.get("Slave_SQL_Running"),
            "seconds_behind_master": row.get("Seconds_Behind_Master"),
            "master_log_file": row.get("Master_Log_File"),
            "read_master_log_pos": row.get("Read_Master_Log_Pos"),
            "relay_master_log_file": row.get("Relay_Master_Log_File"),
            "exec_master_log_pos": row.get("Exec_Master_Log_Pos"),
            "last_errno": row.get("Last_Errno"),
            "last_error": row.get("Last_Error"),
        }

    def collect_processlist(self) -> List[Dict[str, Any]]:
        """Collect SHOW PROCESSLIST."""
        return self._execute("SHOW PROCESSLIST")

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all MySQL metrics including QPS/TPS, connections, 
        InnoDB buffer pool, slow queries, and replication lag.
        """
        global_status = self.collect_global_status()

        # QPS: Questions per second (derived from Questions counter)
        # TPS: Transactions per second (Com_commit + Com_rollback)
        questions = int(global_status.get("Questions", 0))
        com_commit = int(global_status.get("Com_commit", 0))
        com_rollback = int(global_status.get("Com_rollback", 0))

        # Uptime for per-second calculations
        uptime = int(global_status.get("Uptime", 1))

        qps = questions / uptime
        tps = (com_commit + com_rollback) / uptime

        # Connection stats
        max_connections = int(global_status.get("Max_used_connections", 0))
        threads_connected = int(global_status.get("Threads_connected", 0))
        threads_running = int(global_status.get("Threads_running", 0))

        # Slow queries
        slow_queries = int(global_status.get("Slow_queries", 0))

        # InnoDB stats
        innodb_stats = self.collect_innodb_stats()
        buffer_pool_total = int(innodb_stats.get("Innodb_buffer_pool_pages_total", 0))
        buffer_pool_free = int(innodb_stats.get("Innodb_buffer_pool_pages_free", 0))
        buffer_pool_dirty = int(innodb_stats.get("Innodb_buffer_pool_pages_dirty", 0))
        buffer_pool_reads = int(innodb_stats.get("Innodb_buffer_pool_reads", 0))
        buffer_pool_read_requests = int(innodb_stats.get("Innodb_buffer_pool_read_requests", 0))

        # Replication status
        slave_status = self.collect_slave_status()

        return {
            "qps": round(qps, 2),
            "tps": round(tps, 2),
            "questions": questions,
            "com_commit": com_commit,
            "com_rollback": com_rollback,
            "uptime": uptime,
            "threads_connected": threads_connected,
            "threads_running": threads_running,
            "max_used_connections": max_connections,
            "slow_queries": slow_queries,
            "buffer_pool": {
                "total_pages": buffer_pool_total,
                "free_pages": buffer_pool_free,
                "dirty_pages": buffer_pool_dirty,
                "used_pages": buffer_pool_total - buffer_pool_free,
                "reads": buffer_pool_reads,
                "read_requests": buffer_pool_read_requests,
                "hit_ratio": round(
                    (1 - buffer_pool_reads / buffer_pool_read_requests) * 100, 2
                ) if buffer_pool_read_requests > 0 else None,
            },
            "replication": slave_status,
        }

    def close(self):
        """Close the connection."""
        if self._conn and self._conn.open:
            self._conn.close()
        self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
