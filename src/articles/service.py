import sqlite3
from typing import Dict, List
import base64
from ...database.sync_data import sync_data_new

# from src.articles.model import ArticleInput

from ..articles.model import ArticleInput, ArticleRequest


def get_articles_site(input: ArticleInput) -> List[ArticleRequest]:
    db_path = ""
    db_path = sync_data_new()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    results = []
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("""
        SELECT
            T1.ITMREF_0,
            T3.ITMDES1_0,
            T4.TCLCOD_0,
            T3.BASPRI_0,
            T4.SAU_0,
            T5.BLOB_0,
            SUM(T2.QTYSTUACT_0) AS StockActif
        FROM
        ITMFACILIT AS T1
        LEFT JOIN STOCK AS T2 ON T1.ITMREF_0 = T2.ITMREF_0
        AND T1.STOFCY_0 = T2.STOFCY_0
        LEFT JOIN ITMSALES AS T3 ON T1.ITMREF_0 = T3.ITMREF_0
        LEFT JOIN ITMMASTER AS T4 ON T4.ITMREF_0 = T3.ITMREF_0
        LEFT JOIN CBLOB AS T5 ON T4.ITMREF_0 = T5.IDENT1_0
        WHERE
        T1.STOFCY_0 = ?
        GROUP BY
            T1.ITMREF_0,
            T3.ITMDES1_0,
            T4.TCLCOD_0,
            T3.BASPRI_0,
            T4.SAU_0,
            T5.BLOB_0
    """, (input.site_id,))
    
    articles = sqlite_cursor.fetchall()
    sqlite_conn.close()

    for article in articles:
        raw_img = article[5]   # BLOB from DB
        img_b64 = base64.b64encode(raw_img).decode("utf-8") if raw_img else None

        results.append(ArticleRequest(
            item_code=article[0],
            describtion=article[1] or "",
            categorie=article[2],
            base_price=article[3] or 0.0,
            unit_sales=article[4] or "",
            image=img_b64,   
            stock=article[6] or 0.0,
        ))

    return results

def search_article(site_id: str, q: str) -> List[ArticleRequest]:

    results = []
    # --- .1 Connect to SQLite ---
    db_path = ""
    db_path = sync_data_new()
    sqlite_conn = sqlite3.connect(db_path) # type: ignore
    sqlite_cursor = sqlite_conn.cursor()

    # --- .2 Execute SQL Query ---
    sqlite_cursor.execute("""
            SELECT
  T1.ITMREF_0,
  T3.ITMDES1_0,
  T3.TCLCOD_0,
  T3.PURBASPRI_0,
                          T4.SAU_0,
  SUM(T2.QTYSTUACT_0) AS StockActif
FROM
  ITMFACILIT AS T1
  LEFT JOIN STOCK AS T2 ON T1.ITMREF_0 = T2.ITMREF_0
  AND T1.STOFCY_0 = T2.STOFCY_0
  LEFT JOIN ITMMASTER AS T3 ON T1.ITMREF_0 = T3.ITMREF_0
WHERE
  T1.STOFCY_0 = ?
  AND UPPER(ITMDES1_0) LIKE UPPER(?)
GROUP BY
  T1.ITMREF_0,
  T3.ITMDES1_0,
  T3.TCLCOD_0,
  T3.PURBASPRI_0,
                          T4.SAU_0

        """, (site_id, q))
    articles = sqlite_cursor.fetchall()
    sqlite_conn.close()
    for article in articles:
        results.append(ArticleRequest(
            item_code=article[0],
            describtion=article[1] if article[1] is not None else "" ,
            categorie= article[2],
            base_price=article[3] if article[3] is not None else 0.0,
            unit_sales=article[4] if article[4] is not None else "",
            stock=article[5] if article[5] is not None else 0.0,
        ))
    return results