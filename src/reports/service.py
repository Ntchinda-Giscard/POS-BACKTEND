import csv
import io
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.models import CashSession, Payment
from database.sync_data import get_db_file
from .model import DayPoint, HourPoint, Kpi, MethodPoint, ProductPoint, ReportSummary, UserPoint, X3OrdersSummary

METHOD_LABELS = {"cash": "Espèces", "card": "Carte", "digital": "Mobile money"}
DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def _num(value) -> float:
    try:
        return float(str(value).strip()) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _payments(db: Session, date_from: date, date_to: date, site: Optional[str]) -> List[Payment]:
    q = db.query(Payment).filter(
        Payment.status == "success",
        Payment.created_at >= datetime.combine(date_from, datetime.min.time()),
        Payment.created_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
    )
    if site:
        q = q.filter(Payment.site == site)
    return q.order_by(Payment.created_at).all()


def _order_lines(db_path: str, order_ids: List[str]):
    """Lines of the given orders: item, description, qty, net HT/TTC."""
    if not order_ids or not db_path:
        return []
    conn = sqlite3.connect(db_path)
    try:
        rows = []
        for i in range(0, len(order_ids), 400):
            chunk = order_ids[i:i + 400]
            rows += conn.execute(
                f"""
                SELECT P.SOHNUM_0, P.ITMREF_0, COALESCE(NULLIF(TRIM(P.ITMDES_0), ''), M.ITMDES1_0),
                       COALESCE((SELECT SUM(CAST(Q.QTY_0 AS REAL)) FROM SORDERQ Q
                                 WHERE Q.SOHNUM_0 = P.SOHNUM_0 AND Q.ITMREF_0 = P.ITMREF_0
                                   AND (Q.SOPLIN_0 = P.SOPLIN_0 OR P.SOPLIN_0 IS NULL)), 0),
                       P.NETPRINOT_0, P.NETPRIATI_0
                FROM SORDERP P LEFT JOIN ITMMASTER M ON M.ITMREF_0 = P.ITMREF_0
                WHERE P.SOHNUM_0 IN ({','.join('?' * len(chunk))})
                """,
                chunk,
            ).fetchall()
        return rows
    finally:
        conn.close()


def _user_names(db_path: str, codes: List[str]) -> Dict[str, str]:
    codes = [c for c in set(codes) if c]
    if not codes or not db_path:
        return {}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT USR_0, NOMUSR_0 FROM AUTILIS WHERE USR_0 IN ({','.join('?' * len(codes))})", codes
        ).fetchall()
    finally:
        conn.close()
    return {r[0].strip(): (r[1] or "").strip() for r in rows}


def build_summary(db: Session, date_from: date, date_to: date, site: Optional[str]) -> ReportSummary:
    db_path = get_db_file(db)
    payments = _payments(db, date_from, date_to, site)
    span = (date_to - date_from).days + 1
    previous = _payments(db, date_from - timedelta(days=span), date_from - timedelta(days=1), site)

    kpi = Kpi()
    kpi.revenue = round(sum(p.amount for p in payments), 2)
    kpi.transactions = len(payments)
    kpi.average_basket = round(kpi.revenue / kpi.transactions, 2) if kpi.transactions else 0.0
    kpi.cash_total = round(sum(p.amount for p in payments if p.method == "cash"), 2)
    kpi.card_total = round(sum(p.amount for p in payments if p.method == "card"), 2)
    kpi.digital_total = round(sum(p.amount for p in payments if p.method == "digital"), 2)
    kpi.previous_revenue = round(sum(p.amount for p in previous), 2)
    kpi.previous_transactions = len(previous)
    if kpi.previous_revenue:
        kpi.revenue_change_pct = round((kpi.revenue - kpi.previous_revenue) / kpi.previous_revenue * 100, 1)

    # by day (every day of the range, even empty ones)
    by_day: Dict[str, DayPoint] = {}
    d = date_from
    while d <= date_to:
        key = d.isoformat()
        by_day[key] = DayPoint(date=key, label=f"{DAY_LABELS[d.weekday()]} {d.day:02d}/{d.month:02d}")
        d += timedelta(days=1)
    by_method: Dict[str, MethodPoint] = {}
    by_user: Dict[str, UserPoint] = {}
    by_hour: Dict[int, HourPoint] = {h: HourPoint(hour=h) for h in range(24)}
    for p in payments:
        key = p.created_at.date().isoformat()
        if key in by_day:
            by_day[key].revenue = round(by_day[key].revenue + p.amount, 2)
            by_day[key].transactions += 1
        m = by_method.setdefault(p.method, MethodPoint(method=p.method, label=METHOD_LABELS.get(p.method, p.method)))
        m.total = round(m.total + p.amount, 2)
        m.count += 1
        u = by_user.setdefault(p.user_code or "?", UserPoint(user_code=p.user_code or "?"))
        u.transactions += 1
        u.revenue = round(u.revenue + p.amount, 2)
        by_hour[p.created_at.hour].transactions += 1
        by_hour[p.created_at.hour].revenue = round(by_hour[p.created_at.hour].revenue + p.amount, 2)

    names = _user_names(db_path, list(by_user.keys()))
    for code, point in by_user.items():
        point.name = names.get(code)

    # products from the lines of the paid orders
    products: Dict[str, ProductPoint] = {}
    lines = _order_lines(db_path, list({p.order_id for p in payments}))
    for _order, item, desc, qty, net_ht, net_ttc in lines:
        pt = products.setdefault(item, ProductPoint(item_code=item, description=(desc or "").strip()))
        pt.quantity += _num(qty)
        pt.revenue_ht = round(pt.revenue_ht + _num(qty) * _num(net_ht), 2)
        pt.revenue_ttc = round(pt.revenue_ttc + _num(qty) * _num(net_ttc), 2)
    kpi.items_sold = round(sum(pt.quantity for pt in products.values()), 2)
    kpi.orders_revenue_ht = round(sum(pt.revenue_ht for pt in products.values()), 2)
    kpi.tax_total = round(sum(pt.revenue_ttc - pt.revenue_ht for pt in products.values()), 2)

    # cash sessions in the range
    sessions_q = db.query(func.count(CashSession.id), func.coalesce(func.sum(CashSession.difference), 0.0)).filter(
        CashSession.opened_at >= datetime.combine(date_from, datetime.min.time()),
        CashSession.opened_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
    )
    if site:
        sessions_q = sessions_q.filter(CashSession.site == site)
    sessions = sessions_q.first()

    currency = next((p.currency for p in payments if p.currency), None)
    return ReportSummary(
        date_from=date_from.isoformat(), date_to=date_to.isoformat(), site=site, currency=currency,
        kpi=kpi,
        by_day=list(by_day.values()),
        by_method=sorted(by_method.values(), key=lambda m: -m.total),
        by_user=sorted(by_user.values(), key=lambda u: -u.revenue),
        by_hour=[h for h in by_hour.values()],
        top_products=sorted(products.values(), key=lambda p: -p.revenue_ttc)[:10],
        cash_sessions=int(sessions[0] or 0) if sessions else 0,
        cash_difference_total=round(float(sessions[1] or 0.0), 2) if sessions else 0.0,
        x3=build_x3_summary(db_path, site),
    )


def build_x3_summary(db_path: Optional[str], site: Optional[str]) -> X3OrdersSummary:
    """What Sage X3 already knows for this site: its own sales orders (history / context)."""
    summary = X3OrdersSummary()
    if not db_path:
        return summary
    conn = sqlite3.connect(db_path)
    try:
        where = "WHERE ZTRANSFERT_0 IS NOT NULL" + (" AND SALFCY_0 = ?" if site else "")
        params = (site,) if site else ()
        head = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(CAST(ORDATI_0 AS REAL)),0), COALESCE(SUM(CAST(ORDNOT_0 AS REAL)),0), MIN(ORDDAT_0), MAX(ORDDAT_0) FROM SORDER {where}",
            params,
        ).fetchone()
        summary.orders = int(head[0] or 0)
        summary.revenue_ttc = round(_num(head[1]), 2)
        summary.revenue_ht = round(_num(head[2]), 2)
        summary.first_date = (head[3] or "")[:10] or None
        summary.last_date = (head[4] or "")[:10] or None
        summary.by_month = [
            DayPoint(date=r[0], label=r[0], revenue=round(_num(r[1]), 2), transactions=int(r[2]))
            for r in conn.execute(
                f"SELECT substr(ORDDAT_0,1,7), SUM(CAST(ORDATI_0 AS REAL)), COUNT(*) FROM SORDER {where} GROUP BY 1 ORDER BY 1", params
            ).fetchall()
        ]
        summary.top_products = [
            ProductPoint(item_code=r[0], description=(r[1] or "").strip(), quantity=round(_num(r[2]), 2),
                         revenue_ht=round(_num(r[3]), 2), revenue_ttc=round(_num(r[4]), 2))
            for r in conn.execute(
                f"""
                SELECT P.ITMREF_0, MAX(COALESCE(NULLIF(TRIM(P.ITMDES_0), ''), M.ITMDES1_0)),
                       SUM(CAST(Q.QTY_0 AS REAL)), SUM(CAST(Q.QTY_0 AS REAL) * CAST(P.NETPRINOT_0 AS REAL)),
                       SUM(CAST(Q.QTY_0 AS REAL) * CAST(P.NETPRIATI_0 AS REAL))
                FROM SORDER S
                JOIN SORDERP P ON P.SOHNUM_0 = S.SOHNUM_0
                JOIN SORDERQ Q ON Q.SOHNUM_0 = P.SOHNUM_0 AND Q.SOPLIN_0 = P.SOPLIN_0
                LEFT JOIN ITMMASTER M ON M.ITMREF_0 = P.ITMREF_0
                {where.replace('ZTRANSFERT_0', 'S.ZTRANSFERT_0').replace('SALFCY_0', 'S.SALFCY_0')}
                GROUP BY P.ITMREF_0 ORDER BY 5 DESC LIMIT 10
                """,
                params,
            ).fetchall()
        ]
        summary.top_customers = [
            UserPoint(user_code=r[0], name=(r[1] or "").strip(), transactions=int(r[2]), revenue=round(_num(r[3]), 2))
            for r in conn.execute(
                f"""
                SELECT S.BPCORD_0, MAX(C.BPCNAM_0), COUNT(*), SUM(CAST(S.ORDATI_0 AS REAL))
                FROM SORDER S LEFT JOIN BPCUSTOMER C ON C.BPCNUM_0 = S.BPCORD_0
                {where.replace('ZTRANSFERT_0', 'S.ZTRANSFERT_0').replace('SALFCY_0', 'S.SALFCY_0')}
                GROUP BY S.BPCORD_0 ORDER BY 4 DESC LIMIT 10
                """,
                params,
            ).fetchall()
        ]
    finally:
        conn.close()
    return summary


def payments_csv(db: Session, date_from: date, date_to: date, site: Optional[str]) -> str:
    """Flat export of the payments (one row per payment) for Excel."""
    payments = _payments(db, date_from, date_to, site)
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Date", "Heure", "Transaction", "Commande", "Site", "Client", "Caissier", "Mode", "Montant",
                     "Devise", "Reçu", "Monnaie", "Référence", "Opérateur", "Téléphone", "Session caisse"])
    for p in payments:
        writer.writerow([
            p.created_at.strftime("%Y-%m-%d"), p.created_at.strftime("%H:%M:%S"), p.transaction_id, p.order_id,
            p.site or "", p.customer_code or "", p.user_code or "", METHOD_LABELS.get(p.method, p.method),
            f"{p.amount:.2f}".replace(".", ","), p.currency or "",
            f"{p.amount_tendered:.2f}".replace(".", ",") if p.amount_tendered is not None else "",
            f"{p.change:.2f}".replace(".", ",") if p.change is not None else "",
            p.reference or "", p.provider or "", p.phone or "", p.cash_session_id or "",
        ])
    return "﻿" + out.getvalue()


def sales_lines_csv(db: Session, date_from: date, date_to: date, site: Optional[str]) -> str:
    """One row per order line paid at the till (for accounting / ERP checks)."""
    payments = _payments(db, date_from, date_to, site)
    by_order = defaultdict(list)
    for p in payments:
        by_order[p.order_id].append(p)
    lines = _order_lines(get_db_file(db), list(by_order.keys()))
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Date", "Commande", "Transaction", "Client", "Caissier", "Article", "Désignation", "Quantité",
                     "PU net HT", "PU net TTC", "Total HT", "Total TTC"])
    for order_id, item, desc, qty, net_ht, net_ttc in lines:
        p = by_order[order_id][0]
        q, ht, ttc = _num(qty), _num(net_ht), _num(net_ttc)
        writer.writerow([
            p.created_at.strftime("%Y-%m-%d"), order_id, p.transaction_id, p.customer_code or "", p.user_code or "",
            item, (desc or "").strip(), f"{q:g}".replace(".", ","),
            f"{ht:.2f}".replace(".", ","), f"{ttc:.2f}".replace(".", ","),
            f"{q*ht:.2f}".replace(".", ","), f"{q*ttc:.2f}".replace(".", ","),
        ])
    return "﻿" + out.getvalue()
