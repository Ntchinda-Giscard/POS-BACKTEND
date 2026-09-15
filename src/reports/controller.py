from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database.session import get_db
from .model import ReportSummary
from .service import build_summary, payments_csv, sales_lines_csv

router = APIRouter(prefix="/reports", tags=["Reports"])


def _range(period: Optional[str], date_from: Optional[date], date_to: Optional[date]):
    """`period` shortcuts (today | week | month | year) or an explicit from/to."""
    today = date.today()
    if date_from and date_to:
        if date_to < date_from:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_to doit être postérieure à date_from")
        return date_from, date_to
    if period == "today" or not period:
        return today, today
    if period == "yesterday":
        return today - timedelta(days=1), today - timedelta(days=1)
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if period == "month":
        return today.replace(day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    if period == "last7":
        return today - timedelta(days=6), today
    if period == "last30":
        return today - timedelta(days=29), today
    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Période inconnue: {period}")


@router.get("/summary", response_model=ReportSummary)
def read_summary(period: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
                 site: Optional[str] = None, db: Session = Depends(get_db)):
    """KPIs, sales per day / method / cashier / hour, top products, plus the X3 order history of the site."""
    start, end = _range(period, date_from, date_to)
    return build_summary(db, start, end, site)


@router.get("/export/payments.csv")
def export_payments(period: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
                    site: Optional[str] = None, db: Session = Depends(get_db)):
    start, end = _range(period, date_from, date_to)
    content = payments_csv(db, start, end, site)
    return Response(content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="paiements_{start}_{end}.csv"'})


@router.get("/export/sales-lines.csv")
def export_sales_lines(period: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
                       site: Optional[str] = None, db: Session = Depends(get_db)):
    start, end = _range(period, date_from, date_to)
    content = sales_lines_csv(db, start, end, site)
    return Response(content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="ventes_{start}_{end}.csv"'})
