import sqlite3
import json
from datetime import datetime, timezone
from threading import Lock

from .models import AlertRule, AuditEvent, WorkOrder


class AlertRuleStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self._lock = Lock()
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_rules (
                    facility_id TEXT PRIMARY KEY,
                    pest_type TEXT NOT NULL,
                    threshold INTEGER NOT NULL,
                    cooldown_minutes INTEGER NOT NULL,
                    enabled INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS work_orders (
                    work_order_id TEXT PRIMARY KEY,
                    facility_id TEXT NOT NULL,
                    trap_id TEXT NOT NULL,
                    pest_count INTEGER NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def upsert(self, rule: AlertRule) -> AlertRule:
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO alert_rules
                    (facility_id, pest_type, threshold, cooldown_minutes, enabled)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(facility_id) DO UPDATE SET
                    pest_type = excluded.pest_type,
                    threshold = excluded.threshold,
                    cooldown_minutes = excluded.cooldown_minutes,
                    enabled = excluded.enabled
                """,
                (rule.facility_id, rule.pest_type, rule.threshold, int(rule.cooldown_minutes), int(rule.enabled)),
            )
        return rule

    def get(self, facility_id: str) -> AlertRule | None:
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT facility_id, pest_type, threshold, cooldown_minutes, enabled "
                "FROM alert_rules WHERE facility_id = ?",
                (facility_id,),
            ).fetchone()
        if row is None:
            return None
        return AlertRule(
            facility_id=row[0],
            pest_type=row[1],
            threshold=row[2],
            cooldown_minutes=row[3],
            enabled=bool(row[4]),
        )

    def save_work_order(self, work_order: WorkOrder) -> WorkOrder:
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO work_orders "
                "(work_order_id, facility_id, trap_id, pest_count, priority, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (work_order.work_order_id, work_order.facility_id, work_order.trap_id,
                 work_order.pest_count, work_order.priority, work_order.status),
            )
        return work_order

    def list_work_orders(self, facility_id: str) -> list[WorkOrder]:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT work_order_id, facility_id, trap_id, pest_count, priority, status "
                "FROM work_orders WHERE facility_id = ? ORDER BY rowid DESC",
                (facility_id,),
            ).fetchall()
        return [
            WorkOrder(
                work_order_id=row[0],
                facility_id=row[1],
                trap_id=row[2],
                pest_count=row[3],
                priority=row[4],
                status=row[5],
            )
            for row in rows
        ]

    def update_work_order_status(self, work_order_id: str, status: str) -> WorkOrder | None:
        with self._lock, self._connection() as connection:
            connection.execute(
                "UPDATE work_orders SET status = ? WHERE work_order_id = ?",
                (status, work_order_id),
            )
            row = connection.execute(
                "SELECT work_order_id, facility_id, trap_id, pest_count, priority, status "
                "FROM work_orders WHERE work_order_id = ?",
                (work_order_id,),
            ).fetchone()
        if row is None:
            return None
        return WorkOrder(
            work_order_id=row[0], facility_id=row[1], trap_id=row[2],
            pest_count=row[3], priority=row[4], status=row[5],
        )

    def audit(self, actor: str, action: str, resource: str, details: dict) -> None:
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT INTO audit_events (actor, action, resource, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (actor, action, resource, json.dumps(details), datetime.now(timezone.utc).isoformat()),
            )

    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT event_id, actor, action, resource, details, created_at "
                "FROM audit_events ORDER BY event_id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [AuditEvent(event_id=row[0], actor=row[1], action=row[2], resource=row[3],
                           details=json.loads(row[4]), created_at=row[5]) for row in rows]
