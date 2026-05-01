from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.project import ProjectDetail


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RagChunk:
    project_reg_id: int
    section: str
    title: str
    content: str
    metadata: dict[str, Any]


def build_rag_chunks(listing: dict, detail: dict) -> list[RagChunk]:
    project_reg_id = detail["registration"]["project_reg_id"]
    registration = detail["registration"]
    promoter = detail["promoter"]
    financials = detail["financials"]
    progress = detail["progress"]
    location = detail["location"]

    chunks: list[RagChunk] = [
        RagChunk(
            project_reg_id=project_reg_id,
            section="overview",
            title=f"{registration.get('project_name') or 'Project'} overview",
            content=(
                f"Project {registration.get('project_name')} registration {registration.get('project_reg_no')}. "
                f"District {location.get('district')}, taluka {location.get('taluka')}. "
                f"Type {registration.get('project_type')}, status {registration.get('project_status')}. "
                f"Promoter {promoter.get('name')} ({promoter.get('type')}). "
                f"Approved on {registration.get('approved_on')}. "
                f"Start {registration.get('start_date')} end {registration.get('original_end_date')} extended {registration.get('extended_end_date')}. "
                f"Total project cost {financials.get('total_project_cost')}. "
                f"Progress label {progress.get('label')} score {progress.get('score')} time laps ratio {progress.get('time_laps_ratio')}."
            ),
            metadata={
                "project_name": registration.get("project_name"),
                "project_reg_no": registration.get("project_reg_no"),
                "district_name": location.get("district"),
                "project_type": registration.get("project_type"),
                "project_status": registration.get("project_status"),
            },
        )
    ]

    for block in detail.get("blocks", []):
        chunks.append(
            RagChunk(
                project_reg_id=project_reg_id,
                section="block",
                title=f"Block {block.get('block_name')}",
                content=(
                    f"Project {registration.get('project_name')} block {block.get('block_name')} "
                    f"development from {block.get('dev_start_date')} to {block.get('dev_end_date')}. "
                    f"Booked units {block.get('units_booked')} unbooked units {block.get('units_unbooked')} "
                    f"booking percent {block.get('booking_pct')} block progress {block.get('block_progress_pct')}."
                ),
                metadata={
                    "block_name": block.get("block_name"),
                    "block_id": block.get("block_id"),
                },
            )
        )

    for quarter in detail.get("quarters", []):
        progress_pct = None
        qtr_index = quarter.get("qtr_index")
        if isinstance(qtr_index, int) and qtr_index > 0:
            trend = detail.get("progress", {}).get("quarterly_trend", [])
            if len(trend) >= qtr_index:
                progress_pct = trend[qtr_index - 1].get("progress_pct")
        chunks.append(
            RagChunk(
                project_reg_id=project_reg_id,
                section="quarter",
                title=f"Quarter {quarter.get('quarter_name')}",
                content=(
                    f"Project {registration.get('project_name')} quarter {quarter.get('quarter_name')} "
                    f"index {quarter.get('qtr_index')} from {quarter.get('start_date')} to {quarter.get('end_date')} "
                    f"extended date {quarter.get('extended_date')} filing status {quarter.get('status') or quarter.get('payment_status')} "
                    f"submitted on {quarter.get('submitted_on')} progress percent {progress_pct}."
                ),
                metadata={
                    "quarter_id": quarter.get("quarter_id"),
                    "quarter_name": quarter.get("quarter_name"),
                    "qtr_index": quarter.get("qtr_index"),
                },
            )
        )

    for unit in detail.get("inventory", []):
        chunks.append(
            RagChunk(
                project_reg_id=project_reg_id,
                section="inventory",
                title=f"Unit {unit.get('flat_no')} block {unit.get('block_name')}",
                content=(
                    f"Project {registration.get('project_name')} unit {unit.get('flat_no')} in block {unit.get('block_name')} "
                    f"usage {unit.get('usage')} status {unit.get('unit_status')} "
                    f"carpet area {unit.get('carpet_area_sqm')} balcony area {unit.get('balcony_area_sqm')} "
                    f"agreement date {unit.get('date_of_agreement')} allottee {unit.get('allottee_name')} "
                    f"kyc type {unit.get('type_of_kyc')} kyc id {unit.get('kyc_id')} mobile {unit.get('mobile_number')} "
                    f"consideration {unit.get('unit_consideration')} received {unit.get('received_amount')} balance {unit.get('balance_amount')} "
                    f"encumbrance {unit.get('encumbrance_status')}."
                ),
                metadata={
                    "flat_no": unit.get("flat_no"),
                    "block_name": unit.get("block_name"),
                    "allottee_name": unit.get("allottee_name"),
                    "kyc_id": unit.get("kyc_id"),
                    "mobile_number": unit.get("mobile_number"),
                },
            )
        )

    for audit in detail.get("annual_audits", []):
        chunks.append(
            RagChunk(
                project_reg_id=project_reg_id,
                section="audit",
                title=f"Annual audit {audit.get('financial_year')}",
                content=(
                    f"Project {registration.get('project_name')} annual audit financial year {audit.get('financial_year')} "
                    f"status {audit.get('status')} submitted on {audit.get('submitted_on')}."
                ),
                metadata={"financial_year": audit.get("financial_year")},
            )
        )
    return chunks


class LocalStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")

    async def init(self) -> None:
        await asyncio.to_thread(self._init_schema)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS sync_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            total_projects INTEGER,
            synced_projects INTEGER NOT NULL DEFAULT 0,
            failed_projects INTEGER NOT NULL DEFAULT 0,
            limit_value INTEGER,
            offset_value INTEGER,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS projects (
            project_reg_id INTEGER PRIMARY KEY,
            project_name TEXT,
            reg_no TEXT,
            district_name TEXT,
            district_type TEXT,
            project_type TEXT,
            project_status TEXT,
            promoter_name TEXT,
            start_date TEXT,
            end_date TEXT,
            extended_end_date TEXT,
            approved_on TEXT,
            project_cost REAL,
            registration_fee REAL,
            payment_status TEXT,
            wfo_id TEXT,
            listing_json TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            inventory_count INTEGER NOT NULL DEFAULT 0,
            quarter_count INTEGER NOT NULL DEFAULT 0,
            last_synced_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS blocks (
            project_reg_id INTEGER NOT NULL,
            block_id INTEGER,
            block_name TEXT,
            block_progress_pct REAL,
            units_booked INTEGER,
            units_unbooked INTEGER,
            booking_pct REAL,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (project_reg_id, block_id),
            FOREIGN KEY (project_reg_id) REFERENCES projects(project_reg_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quarters (
            project_reg_id INTEGER NOT NULL,
            quarter_id INTEGER NOT NULL,
            quarter_name TEXT,
            qtr_index INTEGER,
            start_date TEXT,
            end_date TEXT,
            extended_date TEXT,
            status TEXT,
            payment_status TEXT,
            submitted_on TEXT,
            progress_pct REAL,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (project_reg_id, quarter_id),
            FOREIGN KEY (project_reg_id) REFERENCES projects(project_reg_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS inventory_units (
            unit_key TEXT PRIMARY KEY,
            project_reg_id INTEGER NOT NULL,
            flat_no TEXT,
            block_name TEXT,
            usage TEXT,
            unit_status TEXT,
            carpet_area_sqm REAL,
            balcony_area_sqm REAL,
            agreement_date TEXT,
            allottee_name TEXT,
            type_of_kyc TEXT,
            kyc_id TEXT,
            mobile_number TEXT,
            unit_consideration REAL,
            received_amount REAL,
            balance_amount REAL,
            encumbrance_status TEXT,
            raw_json TEXT NOT NULL,
            FOREIGN KEY (project_reg_id) REFERENCES projects(project_reg_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_reg_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY (project_reg_id) REFERENCES projects(project_reg_id) ON DELETE CASCADE
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
            title,
            content,
            section,
            tokenize = 'porter unicode61'
        );
        """
        with self._lock:
            self._conn.executescript(schema)
            self._conn.commit()

    async def create_sync_run(
        self, *, total_projects: int | None, limit_value: int | None, offset_value: int
    ) -> int:
        return await asyncio.to_thread(
            self._create_sync_run, total_projects, limit_value, offset_value
        )

    def _create_sync_run(
        self, total_projects: int | None, limit_value: int | None, offset_value: int
    ) -> int:
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO sync_runs (
                    status, total_projects, limit_value, offset_value, started_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                ("running", total_projects, limit_value, offset_value, utc_now()),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    async def update_sync_run_progress(
        self, run_id: int, *, synced_projects: int, failed_projects: int
    ) -> None:
        await asyncio.to_thread(
            self._update_sync_run_progress, run_id, synced_projects, failed_projects
        )

    def _update_sync_run_progress(
        self, run_id: int, synced_projects: int, failed_projects: int
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE sync_runs
                SET synced_projects = ?, failed_projects = ?
                WHERE id = ?
                """,
                (synced_projects, failed_projects, run_id),
            )
            self._conn.commit()

    async def complete_sync_run(
        self, run_id: int, *, synced_projects: int, failed_projects: int
    ) -> None:
        await asyncio.to_thread(
            self._complete_sync_run, run_id, synced_projects, failed_projects
        )

    def _complete_sync_run(
        self, run_id: int, synced_projects: int, failed_projects: int
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE sync_runs
                SET status = ?, synced_projects = ?, failed_projects = ?, finished_at = ?
                WHERE id = ?
                """,
                ("completed", synced_projects, failed_projects, utc_now(), run_id),
            )
            self._conn.commit()

    async def fail_sync_run(
        self, run_id: int, *, synced_projects: int, failed_projects: int, error_message: str
    ) -> None:
        await asyncio.to_thread(
            self._fail_sync_run,
            run_id,
            synced_projects,
            failed_projects,
            error_message,
        )

    def _fail_sync_run(
        self,
        run_id: int,
        synced_projects: int,
        failed_projects: int,
        error_message: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE sync_runs
                SET status = ?, synced_projects = ?, failed_projects = ?, finished_at = ?, error_message = ?
                WHERE id = ?
                """,
                ("failed", synced_projects, failed_projects, utc_now(), error_message, run_id),
            )
            self._conn.commit()

    async def get_sync_run(self, run_id: int) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_sync_run, run_id)

    def _get_sync_run(self, run_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM sync_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    async def get_storage_summary(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_storage_summary)

    def _get_storage_summary(self) -> dict[str, Any]:
        with self._lock:
            project_count = self._conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            block_count = self._conn.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
            quarter_count = self._conn.execute("SELECT COUNT(*) FROM quarters").fetchone()[0]
            inventory_count = self._conn.execute("SELECT COUNT(*) FROM inventory_units").fetchone()[0]
            chunk_count = self._conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()[0]
            last_run = self._conn.execute(
                "SELECT * FROM sync_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "db_path": str(self.db_path),
            "project_count": project_count,
            "block_count": block_count,
            "quarter_count": quarter_count,
            "inventory_count": inventory_count,
            "rag_chunk_count": chunk_count,
            "last_sync_run": dict(last_run) if last_run else None,
        }

    async def upsert_project_bundle(
        self, listing_data: dict[str, Any], detail: ProjectDetail
    ) -> None:
        await asyncio.to_thread(
            self._upsert_project_bundle, listing_data, detail.model_dump(mode="json")
        )

    def _upsert_project_bundle(
        self, listing_data: dict[str, Any], detail_data: dict[str, Any]
    ) -> None:
        project_reg_id = detail_data["registration"]["project_reg_id"]
        blocks = detail_data.get("blocks", [])
        quarters = detail_data.get("quarters", [])
        inventory = detail_data.get("inventory", [])
        chunks = build_rag_chunks(listing_data, detail_data)
        now = utc_now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO projects (
                    project_reg_id, project_name, reg_no, district_name, district_type,
                    project_type, project_status, promoter_name, start_date, end_date,
                    extended_end_date, approved_on, project_cost, registration_fee,
                    payment_status, wfo_id, listing_json, detail_json, inventory_count,
                    quarter_count, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_reg_id) DO UPDATE SET
                    project_name = excluded.project_name,
                    reg_no = excluded.reg_no,
                    district_name = excluded.district_name,
                    district_type = excluded.district_type,
                    project_type = excluded.project_type,
                    project_status = excluded.project_status,
                    promoter_name = excluded.promoter_name,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    extended_end_date = excluded.extended_end_date,
                    approved_on = excluded.approved_on,
                    project_cost = excluded.project_cost,
                    registration_fee = excluded.registration_fee,
                    payment_status = excluded.payment_status,
                    wfo_id = excluded.wfo_id,
                    listing_json = excluded.listing_json,
                    detail_json = excluded.detail_json,
                    inventory_count = excluded.inventory_count,
                    quarter_count = excluded.quarter_count,
                    last_synced_at = excluded.last_synced_at
                """,
                (
                    project_reg_id,
                    detail_data["registration"].get("project_name"),
                    detail_data["registration"].get("project_reg_no"),
                    listing_data.get("district_name"),
                    listing_data.get("district_type"),
                    detail_data["registration"].get("project_type"),
                    detail_data["registration"].get("project_status"),
                    detail_data["promoter"].get("name"),
                    detail_data["registration"].get("start_date"),
                    detail_data["registration"].get("original_end_date"),
                    detail_data["registration"].get("extended_end_date"),
                    detail_data["registration"].get("approved_on"),
                    detail_data["financials"].get("total_project_cost"),
                    detail_data["financials"].get("registration_fee"),
                    detail_data["financials"].get("payment_status"),
                    detail_data["registration"].get("wfo_id"),
                    json.dumps(listing_data),
                    json.dumps(detail_data),
                    len(inventory),
                    len(quarters),
                    now,
                ),
            )

            self._conn.execute("DELETE FROM blocks WHERE project_reg_id = ?", (project_reg_id,))
            self._conn.execute("DELETE FROM quarters WHERE project_reg_id = ?", (project_reg_id,))
            self._conn.execute(
                "DELETE FROM inventory_units WHERE project_reg_id = ?", (project_reg_id,)
            )
            existing_chunk_rows = self._conn.execute(
                "SELECT id FROM rag_chunks WHERE project_reg_id = ?", (project_reg_id,)
            ).fetchall()
            for row in existing_chunk_rows:
                self._conn.execute("DELETE FROM rag_chunks_fts WHERE rowid = ?", (row["id"],))
            self._conn.execute("DELETE FROM rag_chunks WHERE project_reg_id = ?", (project_reg_id,))

            for block in blocks:
                self._conn.execute(
                    """
                    INSERT INTO blocks (
                        project_reg_id, block_id, block_name, block_progress_pct,
                        units_booked, units_unbooked, booking_pct, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_reg_id,
                        block.get("block_id"),
                        block.get("block_name"),
                        block.get("block_progress_pct"),
                        block.get("units_booked"),
                        block.get("units_unbooked"),
                        block.get("booking_pct"),
                        json.dumps(block),
                    ),
                )

            trend_map = {
                item.get("quarter_name"): item.get("progress_pct")
                for item in detail_data.get("progress", {}).get("quarterly_trend", [])
            }
            for quarter in quarters:
                self._conn.execute(
                    """
                    INSERT INTO quarters (
                        project_reg_id, quarter_id, quarter_name, qtr_index, start_date,
                        end_date, extended_date, status, payment_status, submitted_on,
                        progress_pct, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_reg_id,
                        quarter.get("quarter_id"),
                        quarter.get("quarter_name"),
                        quarter.get("qtr_index"),
                        quarter.get("start_date"),
                        quarter.get("end_date"),
                        quarter.get("extended_date"),
                        quarter.get("status"),
                        quarter.get("payment_status"),
                        quarter.get("submitted_on"),
                        trend_map.get(quarter.get("quarter_name")),
                        json.dumps(quarter),
                    ),
                )

            for index, unit in enumerate(inventory):
                unit_key = (
                    f"{project_reg_id}:{unit.get('block_name') or ''}:{unit.get('flat_no') or ''}:"
                    f"{unit.get('usage') or ''}:{index}"
                )
                self._conn.execute(
                    """
                    INSERT INTO inventory_units (
                        unit_key, project_reg_id, flat_no, block_name, usage, unit_status,
                        carpet_area_sqm, balcony_area_sqm, agreement_date, allottee_name,
                        type_of_kyc, kyc_id, mobile_number, unit_consideration,
                        received_amount, balance_amount, encumbrance_status, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        unit_key,
                        project_reg_id,
                        unit.get("flat_no"),
                        unit.get("block_name"),
                        unit.get("usage"),
                        unit.get("unit_status"),
                        unit.get("carpet_area_sqm"),
                        unit.get("balcony_area_sqm"),
                        unit.get("date_of_agreement"),
                        unit.get("allottee_name"),
                        unit.get("type_of_kyc"),
                        unit.get("kyc_id"),
                        unit.get("mobile_number"),
                        unit.get("unit_consideration"),
                        unit.get("received_amount"),
                        unit.get("balance_amount"),
                        unit.get("encumbrance_status"),
                        json.dumps(unit),
                    ),
                )

            for chunk in chunks:
                cursor = self._conn.execute(
                    """
                    INSERT INTO rag_chunks (
                        project_reg_id, section, title, content, metadata_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.project_reg_id,
                        chunk.section,
                        chunk.title,
                        chunk.content,
                        json.dumps(chunk.metadata),
                    ),
                )
                rowid = int(cursor.lastrowid)
                self._conn.execute(
                    """
                    INSERT INTO rag_chunks_fts(rowid, title, content, section)
                    VALUES (?, ?, ?, ?)
                    """,
                    (rowid, chunk.title, chunk.content, chunk.section),
                )

            self._conn.commit()

    async def search_chunks(
        self,
        *,
        query: str,
        limit: int,
        project_reg_id: int | None = None,
        section: str | None = None,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._search_chunks,
            query,
            limit,
            project_reg_id,
            section,
        )

    def _fts_query(self, query: str) -> str:
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
            "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
            "what", "when", "where", "which", "who", "why", "with",
        }
        tokens = [
            token
            for token in re.findall(r"[A-Za-z0-9_-]+", query)
            if token and token.casefold() not in stop_words
        ]
        if not tokens:
            return '""'
        return " AND ".join(f'"{token}"' for token in tokens[:12])

    def _search_chunks(
        self,
        query: str,
        limit: int,
        project_reg_id: int | None,
        section: str | None,
    ) -> list[dict[str, Any]]:
        where = ["rag_chunks_fts MATCH ?"]
        params: list[Any] = [self._fts_query(query)]
        if project_reg_id is not None:
            where.append("rag_chunks.project_reg_id = ?")
            params.append(project_reg_id)
        if section:
            where.append("rag_chunks.section = ?")
            params.append(section)
        params.append(limit)
        sql = f"""
            SELECT
                rag_chunks.id,
                rag_chunks.project_reg_id,
                rag_chunks.section,
                rag_chunks.title,
                rag_chunks.content,
                rag_chunks.metadata_json,
                projects.project_name,
                projects.reg_no,
                projects.district_name,
                bm25(rag_chunks_fts) AS score,
                snippet(rag_chunks_fts, 1, '[', ']', ' ... ', 18) AS snippet
            FROM rag_chunks_fts
            JOIN rag_chunks ON rag_chunks.id = rag_chunks_fts.rowid
            JOIN projects ON projects.project_reg_id = rag_chunks.project_reg_id
            WHERE {" AND ".join(where)}
            ORDER BY score
            LIMIT ?
        """
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
            if not rows:
                like_params: list[Any] = [f"%{query}%"]
                like_where = ["(rag_chunks.content LIKE ? OR rag_chunks.title LIKE ?)"]
                like_params.append(f"%{query}%")
                if project_reg_id is not None:
                    like_where.append("rag_chunks.project_reg_id = ?")
                    like_params.append(project_reg_id)
                if section:
                    like_where.append("rag_chunks.section = ?")
                    like_params.append(section)
                like_params.append(limit)
                rows = self._conn.execute(
                    f"""
                    SELECT
                        rag_chunks.id,
                        rag_chunks.project_reg_id,
                        rag_chunks.section,
                        rag_chunks.title,
                        rag_chunks.content,
                        rag_chunks.metadata_json,
                        projects.project_name,
                        projects.reg_no,
                        projects.district_name,
                        9999.0 AS score,
                        substr(rag_chunks.content, 1, 240) AS snippet
                    FROM rag_chunks
                    JOIN projects ON projects.project_reg_id = rag_chunks.project_reg_id
                    WHERE {" AND ".join(like_where)}
                    ORDER BY rag_chunks.id DESC
                    LIMIT ?
                    """,
                    like_params,
                ).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "chunk_id": row["id"],
                    "project_reg_id": row["project_reg_id"],
                    "project_name": row["project_name"],
                    "reg_no": row["reg_no"],
                    "district_name": row["district_name"],
                    "section": row["section"],
                    "title": row["title"],
                    "content": row["content"],
                    "snippet": row["snippet"],
                    "score": row["score"],
                    "metadata": json.loads(row["metadata_json"]),
                }
            )
        return results
