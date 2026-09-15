import ast
import base64
import sqlite3
from typing import List, Optional
from sqlalchemy.orm import Session
from database.sync_data import get_db_file
from ..articles.model import ArticleInput, ArticleRequest, StockItem, StockLot


def _num(value) -> float:
    try:
        return float(str(value).strip()) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _t(value) -> Optional[str]:
    value = value.strip() if isinstance(value, str) else value
    return value or None


ARTICLE_QUERY = """
    SELECT
        T1.ITMREF_0,
        COALESCE(NULLIF(TRIM(T3.ITMDES1_0), ''), T4.ITMDES1_0),
        T4.TCLCOD_0,
        T3.BASPRI_0,
        COALESCE(NULLIF(TRIM(T4.SAU_0), ''), T4.STU_0),
        (SELECT SUM(CAST(S.QTYSTUACT_0 AS REAL)) FROM STOCK S WHERE S.ITMREF_0 = T1.ITMREF_0 AND S.STOFCY_0 = T1.STOFCY_0),
        T4.EANCOD_0,
        T4.VACITM_0,
        T1.SAFSTO_0,
        T1.MAXSTO_0
    FROM ITMFACILIT AS T1
    LEFT JOIN ITMSALES  AS T3 ON T1.ITMREF_0 = T3.ITMREF_0
    LEFT JOIN ITMMASTER AS T4 ON T4.ITMREF_0 = T1.ITMREF_0
    WHERE T1.STOFCY_0 = ?
"""


def _row_to_article(row) -> ArticleRequest:
    return ArticleRequest(
        item_code=row[0],
        describtion=(row[1] or "").strip(),
        categorie=_t(row[2]),
        base_price=_num(row[3]),
        unit_sales=(row[4] or "").strip(),
        image=None,
        stock=_num(row[5]),
        barcode=_t(row[6]),
        tax_level=_t(row[7]),
        safety_stock=_num(row[8]),
        max_stock=_num(row[9]),
    )


def get_articles_site(input: ArticleInput, db: Session) -> List[ArticleRequest]:
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path)  # type: ignore
    try:
        rows = sqlite_conn.execute(ARTICLE_QUERY + " ORDER BY T1.ITMREF_0", (input.site_id,)).fetchall()
    finally:
        sqlite_conn.close()
    return [_row_to_article(r) for r in rows]


def search_article(site_id: str, q: str, db: Session) -> List[ArticleRequest]:
    """Search by description, item code or barcode (EANCOD_0). `q` already carries the % wildcards."""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path)  # type: ignore
    try:
        rows = sqlite_conn.execute(
            ARTICLE_QUERY + """
              AND (UPPER(COALESCE(T3.ITMDES1_0, T4.ITMDES1_0)) LIKE UPPER(?)
                   OR UPPER(T1.ITMREF_0) LIKE UPPER(?)
                   OR T4.EANCOD_0 LIKE ?)
            ORDER BY T1.ITMREF_0
            """,
            (site_id, q, q, q),
        ).fetchall()
    finally:
        sqlite_conn.close()
    return [_row_to_article(r) for r in rows]


def get_article_by_barcode(site_id: str, barcode: str, db: Session) -> Optional[ArticleRequest]:
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path)  # type: ignore
    try:
        row = sqlite_conn.execute(
            ARTICLE_QUERY + " AND (TRIM(T4.EANCOD_0) = ? OR T1.ITMREF_0 = ?) LIMIT 1",
            (site_id, barcode.strip(), barcode.strip()),
        ).fetchone()
    finally:
        sqlite_conn.close()
    return _row_to_article(row) if row else None


def get_stock_site(site_id: str, db: Session, low_threshold: float = 0.0, with_lots: bool = False) -> List[StockItem]:
    """Stock per item on a site with X3 thresholds (safety / max stock) and lot detail."""
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path)  # type: ignore
    try:
        rows = sqlite_conn.execute(
            """
            SELECT F.ITMREF_0, M.ITMDES1_0, M.TCLCOD_0, COALESCE(NULLIF(TRIM(M.SAU_0), ''), M.STU_0), M.EANCOD_0,
                   COALESCE((SELECT SUM(CAST(S.QTYSTUACT_0 AS REAL)) FROM STOCK S WHERE S.ITMREF_0 = F.ITMREF_0 AND S.STOFCY_0 = F.STOFCY_0), 0),
                   COALESCE((SELECT SUM(CAST(S.CUMALLQTY_0 AS REAL)) FROM STOCK S WHERE S.ITMREF_0 = F.ITMREF_0 AND S.STOFCY_0 = F.STOFCY_0), 0),
                   F.SAFSTO_0, F.MAXSTO_0, F.REOMINQTY_0
            FROM ITMFACILIT F
            LEFT JOIN ITMMASTER M ON M.ITMREF_0 = F.ITMREF_0
            WHERE F.STOFCY_0 = ?
            ORDER BY F.ITMREF_0
            """,
            (site_id,),
        ).fetchall()
        lots_by_item = {}
        if with_lots:
            for r in sqlite_conn.execute(
                "SELECT ITMREF_0, LOT_0, LOC_0, STA_0, QTYSTUACT_0, CUMALLQTY_0, RCPDAT_0 FROM STOCK WHERE STOFCY_0 = ? ORDER BY ITMREF_0, RCPDAT_0",
                (site_id,),
            ).fetchall():
                lots_by_item.setdefault(r[0], []).append(StockLot(
                    lot=_t(r[1]), location=_t(r[2]), status=_t(r[3]), quantity=_num(r[4]),
                    allocated=_num(r[5]), received_at=(r[6] or "")[:10] or None,
                ))
    finally:
        sqlite_conn.close()

    items = []
    for r in rows:
        qty, allocated = _num(r[5]), _num(r[6])
        safety, maximum = _num(r[7]), _num(r[8])
        threshold = safety if safety > 0 else low_threshold
        if qty <= 0:
            status = "out"
        elif threshold > 0 and qty <= threshold:
            status = "low"
        elif maximum > 0 and qty > maximum:
            status = "over"
        else:
            status = "ok"
        items.append(StockItem(
            item_code=r[0], description=(r[1] or "").strip(), category=_t(r[2]), unit=_t(r[3]), barcode=_t(r[4]),
            quantity=qty, allocated=allocated, available=qty - allocated,
            safety_stock=safety, max_stock=maximum, reorder_qty=_num(r[9]), status=status,
            lots=lots_by_item.get(r[0], []),
        ))
    return items


def get_article_image(item_code: str, db: Session) -> Optional[str]:
    db_path = get_db_file(db)
    sqlite_conn = sqlite3.connect(db_path)
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("""
        SELECT BLOB_0
        FROM CBLOB
        WHERE IDENT1_0 = ?
    """, (item_code,))

    result = sqlite_cursor.fetchone()
    sqlite_conn.close()

    if not result:
        return None

    raw_img = result[0]

    if raw_img is None:
        return None

    if isinstance(raw_img, bytes):
        return base64.b64encode(raw_img).decode("ascii")

    if isinstance(raw_img, str):
        try:
            raw_img_bytes = ast.literal_eval(raw_img)
            if isinstance(raw_img_bytes, (bytes, bytearray)):
                return base64.b64encode(raw_img_bytes).decode("ascii")
        except Exception:
            return None

    return None
