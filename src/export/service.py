"""
POS → Sage X3 return channel.

Rows the till created in the X3 mirror (no ZTRANSFERT_0 value) are written to CSV files using the
exact layout of the inbound sync (`TABLE_NAME,col1,col2,...` header, one table per file) so the
X3 side can import them with the same template, then optionally emailed to the X3 mailbox.
Exported keys are remembered in pos_export_log so a row is never sent twice.
"""
import csv
import logging
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.models import ExportLog, POPConfig, Payment
from database.sync_data import get_db_file
from src.settings.service import get_setting
from .model import ExportBatch, ExportedFile, ExportResult, PendingExport

logger = logging.getLogger(__name__)

# (table, key column, filter for till-created rows, optional site column)
X3_TABLES: List[Tuple[str, str, str, Optional[str]]] = [
    ("SORDER", "SOHNUM_0", "ZTRANSFERT_0 IS NULL", "SALFCY_0"),
    ("SORDERP", "SOHNUM_0", "ZTRANSFERT_0 IS NULL", None),
    ("SORDERQ", "SOHNUM_0", "ZTRANSFERT_0 IS NULL", None),
    ("SDELIVERY", "SDHNUM_0", "ZTRANSFERT_0 IS NULL", "STOFCY_0"),
    ("SDELIVERYD", "SDHNUM_0", "ZTRANSFERT_0 IS NULL", "STOFCY_0"),
]
PAYMENT_TABLE = "POS_PAYMENT"
PAYMENT_COLUMNS = ["TXNNUM_0", "SOHNUM_0", "PAYMOD_0", "AMT_0", "AMTTENDER_0", "CHANGE_0", "REF_0", "PROVIDER_0",
                   "PHONE_0", "CUR_0", "BPCNUM_0", "USR_0", "CASHSESSION_0", "FCY_0", "STA_0", "CREDATTIM_0"]


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return str(bytes(value))          # same `b'...'` form as the inbound CSV
    return str(value)


def _exported_keys(db: Session, table: str) -> set:
    return {k for (k,) in db.query(ExportLog.row_key).filter(ExportLog.table_name == table).all()}


def _pending_rows(conn: sqlite3.Connection, db: Session, table: str, key: str, where: str,
                  site_col: Optional[str], site: Optional[str], columns: List[str]):
    query = f'SELECT {", ".join(columns)} FROM "{table}" WHERE {where}'
    params: tuple = ()
    if site and site_col:
        query += f" AND {site_col} = ?"
        params = (site,)
    rows = conn.execute(query, params).fetchall()
    done = _exported_keys(db, table)
    key_index = columns.index(key)
    return [r for r in rows if _cell(r[key_index]) not in done]


def _columns(conn: sqlite3.Connection, table: str) -> List[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall() if r[1] != "ROWID"]


def _pending_payments(db: Session, site: Optional[str]) -> List[Payment]:
    done = _exported_keys(db, PAYMENT_TABLE)
    q = db.query(Payment).filter(Payment.status == "success")
    if site:
        q = q.filter(Payment.site == site)
    return [p for p in q.order_by(Payment.created_at).all() if p.transaction_id not in done]


def pending(db: Session, site: Optional[str]) -> PendingExport:
    result = PendingExport(site=site)
    db_path = get_db_file(db)
    if db_path:
        conn = sqlite3.connect(db_path)
        try:
            for table, key, where, site_col in X3_TABLES:
                cols = _columns(conn, table)
                result.counts[table] = len(_pending_rows(conn, db, table, key, where, site_col, site, cols))
        finally:
            conn.close()
    result.counts[PAYMENT_TABLE] = len(_pending_payments(db, site))
    result.total = sum(result.counts.values())
    return result


def run_export(db: Session, site: Optional[str], send_email: bool = True) -> ExportResult:
    batch = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = get_setting(db, "export_folder") or r"C:\poswaza\temp\export"
    os.makedirs(folder, exist_ok=True)
    result = ExportResult(batch=batch, folder=folder)
    suffix = f"_{site}" if site else ""

    db_path = get_db_file(db)
    logs: List[ExportLog] = []
    if db_path:
        conn = sqlite3.connect(db_path)
        try:
            for table, key, where, site_col in X3_TABLES:
                cols = _columns(conn, table)
                rows = _pending_rows(conn, db, table, key, where, site_col, site, cols)
                if not rows:
                    continue
                path = os.path.join(folder, f"pos_{table}{suffix}_{batch}.csv")
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["TABLE_NAME"] + cols)
                    for r in rows:
                        writer.writerow([table] + [_cell(v) for v in r])
                key_index = cols.index(key)
                seen = set()
                for r in rows:
                    k = _cell(r[key_index])
                    if k in seen:
                        continue
                    seen.add(k)
                    logs.append(ExportLog(batch=batch, table_name=table, row_key=k, file_path=path))
                result.files.append(ExportedFile(table=table, path=path, rows=len(rows)))
        finally:
            conn.close()

    payments = _pending_payments(db, site)
    if payments:
        path = os.path.join(folder, f"pos_{PAYMENT_TABLE}{suffix}_{batch}.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["TABLE_NAME"] + PAYMENT_COLUMNS)
            for p in payments:
                writer.writerow([PAYMENT_TABLE, p.transaction_id, p.order_id, p.method, f"{p.amount:.2f}",
                                 "" if p.amount_tendered is None else f"{p.amount_tendered:.2f}",
                                 "" if p.change is None else f"{p.change:.2f}",
                                 p.reference or "", p.provider or "", p.phone or "", p.currency or "",
                                 p.customer_code or "", p.user_code or "", p.cash_session_id or "", p.site or "",
                                 p.status, p.created_at.strftime("%Y-%m-%d %H:%M:%S")])
                logs.append(ExportLog(batch=batch, table_name=PAYMENT_TABLE, row_key=p.transaction_id, file_path=path))
        result.files.append(ExportedFile(table=PAYMENT_TABLE, path=path, rows=len(payments)))

    result.total_rows = sum(f.rows for f in result.files)
    if not result.files:
        return result

    recipient = (get_setting(db, "export_recipient") or "").strip()
    result.recipient = recipient or None
    if send_email and recipient:
        try:
            _send_email(db, recipient, batch, [f.path for f in result.files])
            result.emailed = True
        except Exception as e:  # keep the files, report the problem
            logger.error(f"export email failed: {e}")
            result.email_error = str(e)

    for log in logs:
        log.sent_by_email = 1 if result.emailed else 0
        db.add(log)
    db.commit()
    logger.info(f"export batch {batch}: {result.total_rows} rows in {len(result.files)} files, emailed={result.emailed}")
    return result


def _send_email(db: Session, recipient: str, batch: str, paths: List[str]) -> None:
    config = db.query(POPConfig).first()
    if not config or not config.username or not config.password:
        raise RuntimeError("Identifiants email non configurés (Paramètres → IMAP)")
    server = (get_setting(db, "smtp_server") or "").strip() or (config.server or "").replace("imap.", "smtp.").replace("pop.", "smtp.")
    port = int(get_setting(db, "smtp_port") or 587)

    msg = EmailMessage()
    msg["Subject"] = f"POS export {batch}"
    msg["From"] = config.username
    msg["To"] = recipient
    msg.set_content(f"Export point de vente {batch}: {len(paths)} fichier(s) en pièce jointe.")
    for path in paths:
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="csv", filename=os.path.basename(path))

    if port == 465:
        with smtplib.SMTP_SSL(server, port, timeout=30) as smtp:
            smtp.login(config.username, config.password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(server, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.username, config.password)
            smtp.send_message(msg)


def history(db: Session, limit: int = 50) -> List[ExportBatch]:
    rows = (
        db.query(ExportLog.batch, ExportLog.table_name, func.count(ExportLog.id), func.max(ExportLog.exported_at),
                 func.max(ExportLog.sent_by_email), func.max(ExportLog.file_path))
        .group_by(ExportLog.batch, ExportLog.table_name).order_by(ExportLog.batch.desc()).all()
    )
    batches: Dict[str, ExportBatch] = {}
    for batch, table, count, at, emailed, path in rows:
        b = batches.setdefault(batch, ExportBatch(batch=batch, exported_at=at, emailed=bool(emailed)))
        b.tables[table] = int(count)
        if path and path not in b.files:
            b.files.append(path)
        b.exported_at = max(b.exported_at, at)
    return list(batches.values())[:limit]
