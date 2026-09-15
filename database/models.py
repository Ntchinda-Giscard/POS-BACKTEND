from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
try:
    from .session import Base
except ImportError:
    from session import Base

class POPConfig(Base):
    __tablename__ = "pop_config"

    id = Column(Integer, primary_key=True, index=True)
    server = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    path = Column(String, unique=True, index=True)
    address_vente = Column(String, nullable=True)
    site_livraison = Column(String, nullable=True)

    def __repr__(self):
        return f"<POPConfig(id={self.id}, server='{self.server}', username='{self.username}', port={self.port})>"


class FolderConfig(Base):
    __tablename__ = "folder_config"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)

    def __repr__(self):
        return f"<FolderConfig(id={self.id}, path='{self.path}')>"


class AppSetting(Base):
    """Key/value settings of the till (low stock threshold, export folder, SMTP...)."""
    __tablename__ = "pos_setting"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class UserPin(Base):
    """Local PIN for a Sage X3 user (AUTILIS.USR_0). X3 passwords are hashed with a proprietary
    scheme and cannot be verified here, so each user sets a PIN on first login at the till."""
    __tablename__ = "pos_user_pin"

    user_code = Column(String, primary_key=True)
    pin_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login_at = Column(DateTime, nullable=True)


class CashSession(Base):
    """One opening → closing of the till (fond de caisse, comptage, écart)."""
    __tablename__ = "pos_cash_session"

    id = Column(Integer, primary_key=True, index=True)
    site = Column(String, index=True)
    user_code = Column(String, index=True)            # who opened
    closed_by = Column(String, nullable=True)
    opened_at = Column(DateTime, default=datetime.now, index=True)
    closed_at = Column(DateTime, nullable=True)
    opening_amount = Column(Float, default=0.0)       # fond de caisse
    cash_sales = Column(Float, nullable=True)         # filled at close
    cash_in = Column(Float, nullable=True)
    cash_out = Column(Float, nullable=True)
    expected_amount = Column(Float, nullable=True)    # opening + sales + in - out
    closing_amount = Column(Float, nullable=True)     # counted
    difference = Column(Float, nullable=True)         # counted - expected
    currency = Column(String, nullable=True)
    status = Column(String, default="open", index=True)  # open | closed
    notes = Column(Text, nullable=True)


class CashMovement(Base):
    """Cash added to / removed from the drawer outside of sales (apport, retrait, dépense)."""
    __tablename__ = "pos_cash_movement"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True)
    type = Column(String)                              # in | out
    amount = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    user_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Payment(Base):
    """A payment registered at the till for a sales order (SORDER.SOHNUM_0)."""
    __tablename__ = "pos_payment"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    order_id = Column(String, index=True)
    method = Column(String, index=True)          # cash | card | digital
    amount = Column(Float, nullable=False)
    amount_tendered = Column(Float, nullable=True)  # cash only
    change = Column(Float, nullable=True)           # cash only
    reference = Column(String, nullable=True)       # terminal approval ref / mobile money txn id
    provider = Column(String, nullable=True)        # MOMO | OM (digital only)
    phone = Column(String, nullable=True)           # digital only
    currency = Column(String, nullable=True)
    customer_code = Column(String, nullable=True)
    user_code = Column(String, nullable=True, index=True)      # cashier (AUTILIS.USR_0)
    cash_session_id = Column(Integer, nullable=True, index=True)
    site = Column(String, nullable=True)
    status = Column(String, default="success")
    created_at = Column(DateTime, default=datetime.now, index=True)

    def __repr__(self):
        return f"<Payment(transaction_id='{self.transaction_id}', order_id='{self.order_id}', method='{self.method}', amount={self.amount})>"


class ExportLog(Base):
    """Rows created by the till that have been exported towards Sage X3 (POS → X3 return channel)."""
    __tablename__ = "pos_export_log"

    id = Column(Integer, primary_key=True, index=True)
    batch = Column(String, index=True)                 # export batch id (timestamp)
    table_name = Column(String, index=True)            # SORDER | SORDERP | SORDERQ | SDELIVERY | SDELIVERYD | POS_PAYMENT
    row_key = Column(String, index=True)               # SOHNUM_0 / SDHNUM_0 / transaction id
    file_path = Column(String, nullable=True)
    sent_by_email = Column(Integer, default=0)
    exported_at = Column(DateTime, default=datetime.now)
