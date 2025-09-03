import sqlite3
from typing import Dict, List
# from src.articles.model import ArticleInput

from ..articles.model import ArticleInput, ArticleRequest


def get_articles_site(input: ArticleInput) -> List[ArticleRequest]:
    results = []
    # --- .1 Connect to SQLite ---
    sqlite_conn = sqlite3.connect("sagex3_seed.db")
    sqlite_cursor = sqlite_conn.cursor()

    # --- .2 Execute SQL Query ---
    sqlite_cursor.execute("""
            SELECT
            T1.ITMREF_0,
            T3.ITMDES1_0,
            SUM(T2.QTYSTUACT_0)
        FROM
            ITMFACILIT AS T1
        LEFT JOIN
            STOCK AS T2 ON T1.ITMREF_0 = T2.ITMREF_0 AND T1.STOFCY_0 = T2.STOFCY_0
        LEFT JOIN
            ITMMASTER AS T3 ON T1.ITMREF_0 = T3.ITMREF_0
        WHERE
            T1.STOFCY_0 = ?
        GROUP BY
            T1.ITMREF_0,
            T3."ITMDES1_0"

        """, (input.site_id,))
    articles = sqlite_cursor.fetchall()
    sqlite_conn.close()
    for article in articles:
        results.append(ArticleRequest(
            item_code=article["ITMREF_0"],
            describtion=article["ITMDES1_0"],
            stock=article["QTYSTUACT_0"]
        ))
    return results

