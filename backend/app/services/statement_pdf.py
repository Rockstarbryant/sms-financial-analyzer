"""Parse M-Pesa and Airtel Money PDF statements into structured rows.

M-Pesa PDFs are often password-protected (ID number or SMS access code).
We decrypt with pypdf, then extract tables/text with pdfplumber.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

from app.models.transaction import (
    Category,
    Confidence,
    Direction,
    Provider,
    TransactionType,
)

_AMOUNT = re.compile(r"([\d,]+(?:\.\d{1,2})?)")
_RECEIPT = re.compile(r"\b([A-Z0-9]{8,14})\b")
_PHONE = re.compile(r"(?:\+?254|0)?(7\d{8})")
_DATE_TIME = re.compile(
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)",
    re.IGNORECASE,
)


@dataclass
class StatementRow:
    provider: Provider
    direction: Direction
    transaction_type: TransactionType
    category: Category
    amount: float
    fee: float | None
    balance: float | None
    counterparty: str | None
    counterparty_phone: str | None
    transaction_id: str | None
    timestamp: datetime
    confidence: Confidence
    source_hash: str
    details: str


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("Ksh", "").replace("KES", "")
    if not s or s in {"-", "—", "None", "null"}:
        return None
    try:
        return float(s)
    except ValueError:
        m = _AMOUNT.search(s)
        if not m:
            return None
        return float(m.group(1).replace(",", ""))


def _parse_dt(raw: str) -> datetime | None:
    raw = re.sub(r"\s+", " ", (raw or "").strip())
    if not raw:
        return None
    for fmt in (
        "%d-%m-%y %I:%M %p",
        "%d-%m-%y %I:%M:%S %p",
        "%d/%m/%y %I:%M %p",
        "%d/%m/%y %I:%M:%S %p",
        "%d-%m-%Y %I:%M %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%y %H:%M:%S",
        "%d-%m-%y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %I:%M:%S %p",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    # Last resort: extract a date-looking substring
    m = _DATE_TIME.search(raw)
    if m and m.group(1) != raw:
        return _parse_dt(m.group(1))
    return None


def _classify_details(details: str) -> tuple[TransactionType, Category, Direction | None]:
    d = details.lower()
    if "airtime" in d:
        return TransactionType.AIRTIME, Category.AIRTIME, Direction.OUT
    if "bundle" in d or ("data" in d and ("buy" in d or "purchase" in d)):
        return TransactionType.BUNDLE, Category.BUNDLE, Direction.OUT
    if "withdraw" in d or "cash out" in d or "agent withdrawal" in d:
        return TransactionType.WITHDRAWAL, Category.WITHDRAWAL, Direction.OUT
    if "deposit" in d or "cash in" in d or "funds received from" in d:
        return TransactionType.DEPOSIT, Category.DEPOSIT, Direction.IN
    if (
        "pay bill" in d
        or "paybill" in d
        or "buy goods" in d
        or "merchant" in d
        or " till " in d
        or "paid to" in d
    ):
        return TransactionType.PAYMENT, Category.PAYMENT, Direction.OUT
    if "received from" in d or d.startswith("from ") or "funds received" in d:
        return TransactionType.RECEIVED, Category.TRANSFER, Direction.IN
    if (
        "sent to" in d
        or "transfer to" in d
        or "customer transfer to" in d
        or "give" in d and "to" in d
    ):
        return TransactionType.SENT, Category.TRANSFER, Direction.OUT
    if "charge" in d or "fee" in d or "transaction cost" in d or "od charge" in d:
        return TransactionType.OTHER, Category.OTHER, Direction.OUT
    return TransactionType.OTHER, Category.OTHER, None


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9 and digits.startswith("7"):
        return "0" + digits
    if len(digits) == 12 and digits.startswith("254"):
        return "0" + digits[3:]
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    return None


def _clean_person_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" -.,")
    # Drop masked fragments noise
    name = re.sub(r"\*+", "", name)
    # Title-case for consistent grouping of "brian ouma" vs "BRIAN OUMA"
    if name.isupper() or name.islower():
        name = name.title()
    return name[:255]


def _counterparty_from_details(details: str) -> tuple[str | None, str | None]:
    phone = None
    phone_m = _PHONE.search(details)
    if phone_m:
        phone = _normalize_phone(phone_m.group(0))

    for pattern in (
        r"(?:Customer Transfer (?:to|from)|Transfer (?:to|from))\s+[-]?\s*(.+?)(?:\s+Acc\.|\s+Completed|$)",
        r"(?:sent to|transfer to|paid to)\s+[-]?\s*(.+?)(?:\s+Acc\.|\s+on\s|\s+\d{1,2}[/-]|$)",
        r"(?:received from|funds received from|from)\s+(.+?)(?:\s+Acc\.|\s+on\s|\s+\d{1,2}[/-]|$)",
        r"(?:Withdraw.*?from|Deposit.*?to)\s+(.+?)(?:\s+Acc\.|$)",
        r"to\s+(.+?)(?:\s+Acc\.|$)",
    ):
        m = re.search(pattern, details, re.IGNORECASE)
        if m:
            name = m.group(1)
            name = re.sub(r"\s*(?:\+?254|0)?7\d{8}", "", name)
            name = re.sub(r"\s*2547\*+\d+", "", name)
            name = _clean_person_name(name)
            if name and name.lower() not in {"completed", "null", "none"}:
                return name, phone
    if phone:
        return phone, phone
    return None, phone


def _row_hash(provider: str, receipt: str, ts: str, amount: float, details: str) -> str:
    payload = f"{provider}|{receipt}|{ts}|{amount:.2f}|{details[:120]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _open_pdf_bytes(data: bytes, password: str | None) -> bytes:
    """Return decrypted PDF bytes (or original if not encrypted)."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF statements") from exc

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        if not password:
            raise ValueError(
                "This PDF is password-protected. Enter the statement password "
                "(often your national ID, or the access code from Safaricom SMS)."
            )
        result = reader.decrypt(password)
        if result == 0:
            # try again if library returns status differently
            ok = reader.decrypt(password)
            if not ok and reader.is_encrypted:
                raise ValueError("Wrong PDF password. Check the SMS code or ID number and try again.")
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    return data


def _extract_tables(pdf_bytes: bytes) -> list[list[list[str | None]]]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required for PDF statements") from exc

    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                tables.append(table)
    return tables


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required for PDF statements") from exc

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _normalize_header(cell: str | None) -> str:
    if not cell:
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip().lower()


def _map_mpesa_columns(header: list[str | None]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, cell in enumerate(header):
        h = _normalize_header(cell)
        if "receipt" in h:
            mapping["receipt"] = i
        elif "completion" in h or h == "time" or "date" in h and "time" in h:
            mapping["time"] = i
        elif "detail" in h:
            mapping["details"] = i
        elif "status" in h:
            mapping["status"] = i
        elif "paid in" in h or h == "paid in":
            mapping["paid_in"] = i
        elif "withdraw" in h:
            mapping["withdrawn"] = i
        elif "balance" in h:
            mapping["balance"] = i
    return mapping


def _parse_mpesa_tables(tables: list[list[list[str | None]]]) -> list[StatementRow]:
    rows: list[StatementRow] = []
    for table in tables:
        if not table or len(table) < 2:
            continue
        # Find header row
        header_idx = None
        colmap: dict[str, int] = {}
        for i, row in enumerate(table[:5]):
            colmap = _map_mpesa_columns(row)
            if "receipt" in colmap and ("paid_in" in colmap or "withdrawn" in colmap):
                header_idx = i
                break
        if header_idx is None:
            continue

        for raw in table[header_idx + 1 :]:
            if not raw or all(c is None or str(c).strip() == "" for c in raw):
                continue

            def cell(key: str) -> str:
                idx = colmap.get(key)
                if idx is None or idx >= len(raw):
                    return ""
                return str(raw[idx] or "").replace("\n", " ").strip()

            receipt = cell("receipt")
            if not receipt or not _RECEIPT.search(receipt):
                continue
            status = cell("status").lower()
            if status and status not in {"completed", "complete", ""}:
                continue

            details = cell("details") or ""
            paid_in = _to_float(cell("paid_in"))
            withdrawn = _to_float(cell("withdrawn"))
            balance = _to_float(cell("balance"))
            ts_raw = cell("time")
            ts = _parse_dt(ts_raw) if ts_raw else None
            if ts is None:
                continue

            # Prefer explicit columns; withdrawn may be negative in some PDFs
            paid_in_v = abs(paid_in) if paid_in and paid_in != 0 else 0.0
            withdrawn_v = abs(withdrawn) if withdrawn and withdrawn != 0 else 0.0

            if paid_in_v > 0 and withdrawn_v == 0:
                amount = paid_in_v
                direction = Direction.IN
            elif withdrawn_v > 0 and paid_in_v == 0:
                amount = withdrawn_v
                direction = Direction.OUT
            elif paid_in_v > 0 and withdrawn_v > 0:
                # Rare both filled — trust the larger non-zero? Prefer details hint
                amount = max(paid_in_v, withdrawn_v)
                direction = Direction.IN if paid_in_v >= withdrawn_v else Direction.OUT
            else:
                continue

            txn_type, category, dir_hint = _classify_details(details)
            # Column direction is primary; details refine type. Only override
            # direction when details are strongly directional and columns conflict.
            if dir_hint is not None and dir_hint != direction:
                # Details win for clear send/receive/withdraw wording
                if any(
                    k in details.lower()
                    for k in (
                        "sent to",
                        "transfer to",
                        "withdraw",
                        "received from",
                        "paid to",
                        "deposit",
                    )
                ):
                    direction = dir_hint

            fee = None
            if direction == Direction.OUT and any(
                k in details.lower() for k in ("charge", "fee", "transaction cost", "od charge")
            ):
                fee = amount
                txn_type, category = TransactionType.OTHER, Category.OTHER

            cp, phone = _counterparty_from_details(details)
            rows.append(
                StatementRow(
                    provider=Provider.MPESA,
                    direction=direction,
                    transaction_type=txn_type,
                    category=category,
                    amount=amount,
                    fee=fee,
                    balance=balance,
                    counterparty=cp,
                    counterparty_phone=phone,
                    transaction_id=receipt.strip(),
                    timestamp=ts,
                    confidence=Confidence.HIGH,
                    source_hash=_row_hash("mpesa", receipt, ts.isoformat(), amount, details),
                    details=details,
                )
            )
    return rows


def _parse_mpesa_text_fallback(text: str) -> list[StatementRow]:
    """Line-oriented fallback when tables are empty."""
    rows: list[StatementRow] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i < len(lines):
        if not _RECEIPT.fullmatch(lines[i].replace(" ", "")) and not (
            len(lines[i]) >= 8 and _RECEIPT.search(lines[i]) and " " not in lines[i].strip()
        ):
            i += 1
            continue
        receipt = lines[i].strip()
        i += 1
        if i >= len(lines):
            break
        ts = _parse_dt(lines[i])
        if ts is None:
            continue
        i += 1
        details_parts: list[str] = []
        status = ""
        amounts: list[float] = []
        while i < len(lines) and not _RECEIPT.fullmatch(lines[i].replace(" ", "")):
            if lines[i].lower() in {"completed", "failed"}:
                status = lines[i].lower()
            else:
                val = _to_float(lines[i])
                if val is not None and re.fullmatch(r"[\d,]+(?:\.\d{1,2})?", lines[i].replace(" ", "")):
                    amounts.append(val)
                elif _DATE_TIME.match(lines[i]):
                    break
                else:
                    details_parts.append(lines[i])
            i += 1
            if len(amounts) >= 3:
                break
        if status and status != "completed":
            continue
        details = " ".join(details_parts)
        if not amounts:
            continue
        # Heuristic: paid_in, withdrawn, balance — empties omitted in text stream
        paid_in = amounts[0] if len(amounts) == 1 and ("from" in details.lower() or "received" in details.lower()) else None
        withdrawn = None
        balance = amounts[-1] if len(amounts) >= 2 else None
        if len(amounts) == 2:
            if "from" in details.lower() or "received" in details.lower():
                paid_in, balance = amounts[0], amounts[1]
            else:
                withdrawn, balance = amounts[0], amounts[1]
        elif len(amounts) >= 3:
            paid_in, withdrawn, balance = amounts[0], amounts[1], amounts[2]

        if paid_in and paid_in > 0:
            amount, direction = paid_in, Direction.IN
        elif withdrawn and withdrawn > 0:
            amount, direction = abs(withdrawn), Direction.OUT
        else:
            continue

        txn_type, category, dir_hint = _classify_details(details)
        if dir_hint:
            direction = dir_hint
        cp, phone = _counterparty_from_details(details)
        rows.append(
            StatementRow(
                provider=Provider.MPESA,
                direction=direction,
                transaction_type=txn_type,
                category=category,
                amount=amount,
                fee=None,
                balance=balance,
                counterparty=cp,
                counterparty_phone=phone,
                transaction_id=receipt,
                timestamp=ts,
                confidence=Confidence.MEDIUM,
                source_hash=_row_hash("mpesa", receipt, ts.isoformat(), amount, details),
                details=details,
            )
        )
    return rows


def parse_mpesa_statement(data: bytes, password: str | None = None) -> list[StatementRow]:
    pdf_bytes = _open_pdf_bytes(data, password)
    tables = _extract_tables(pdf_bytes)
    rows = _parse_mpesa_tables(tables)
    if not rows:
        text = _extract_text(pdf_bytes)
        rows = _parse_mpesa_text_fallback(text)
    return rows


def _map_airtel_columns(header: list[str | None]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, cell in enumerate(header):
        h = _normalize_header(cell)
        if "transaction id" in h or h in {"tid", "txn id", "id"}:
            mapping["id"] = i
        elif "date" in h or "time" in h:
            mapping["time"] = i
        elif "description" in h or "detail" in h:
            mapping["details"] = i
        elif "status" in h:
            mapping["status"] = i
        elif "credit" in h:
            mapping["credit"] = i
        elif "debit" in h:
            mapping["debit"] = i
        elif "balance" in h:
            mapping["balance"] = i
    return mapping


def _classify_airtel_details(
    details: str,
) -> tuple[TransactionType, Category, Direction | None]:
    d = details.lower()
    if "airtime" in d:
        return TransactionType.AIRTIME, Category.AIRTIME, Direction.OUT
    if "bundle" in d:
        return TransactionType.BUNDLE, Category.BUNDLE, Direction.OUT
    if (
        "electricity" in d
        or "merchant payment" in d
        or "paybill" in d
        or "lipa na" in d
    ):
        return TransactionType.PAYMENT, Category.PAYMENT, Direction.OUT
    if "money sent" in d and "bank" in d:
        return TransactionType.WITHDRAWAL, Category.WITHDRAWAL, Direction.OUT
    if "money received from bank" in d or ("bank" in d and "received" in d):
        return TransactionType.DEPOSIT, Category.DEPOSIT, Direction.IN
    if "received money" in d or d.startswith("received"):
        return TransactionType.RECEIVED, Category.TRANSFER, Direction.IN
    if "sent money" in d or d.startswith("sent"):
        return TransactionType.SENT, Category.TRANSFER, Direction.OUT
    return _classify_details(details)


def _airtel_counterparty(details: str) -> tuple[str | None, str | None]:
    """Extract name + phone from Airtel description lines."""
    lower = details.lower()
    phone = None
    phone_m = re.search(r"(?:254|0)?(7\d{8})", details)
    if phone_m:
        phone = _normalize_phone(phone_m.group(0))

    # System / self labels first
    if "bundle purchase for self" in lower:
        return "Airtel Bundle (self)", None
    if "airtime purchase for self" in lower:
        return "Airtel Airtime (self)", None
    if "lipa na mpesa" in lower or "000003344" in details:
        return "Lipa Na M-Pesa", None
    if "merchant payment" in lower and "mpesa" in lower:
        return "M-Pesa Paybill (via Airtel)", None
    if "electricity" in lower:
        return "Electricity", None
    if "money received from bank" in lower or ("bank" in lower and "received" in lower):
        return "Bank", phone
    if "money sent" in lower and "bank" in lower:
        return "Bank", phone

    patterns = (
        r"Sent Money to\s+(?:\+?254|0)?(\d{9,12})?\s*([A-Za-z][A-Za-z .'-]{1,60}?)(?:\.|$|Receiving)",
        r"Sent Money to\s+(\d{6,12})\s+([A-Za-z][A-Za-z .'-]{1,60}?)(?:\.|$|Receiving)",
        r"Received Money from\s+(.+?)\s+(?:254|0)?(7\d{8})",
        r"Received Money from\s+(.+?)(?:\.|$|Sender)",
        r"Sent Money to\s+(\d{6,12})\s+([A-Za-z].+?)(?:\.|$)",
    )
    for pattern in patterns:
        m = re.search(pattern, details, re.IGNORECASE)
        if not m:
            continue
        groups = [g for g in m.groups() if g]
        name = None
        for g in groups:
            if re.fullmatch(r"\d{6,12}", g.strip()):
                phone = phone or _normalize_phone(g.strip())
            else:
                name = _clean_person_name(g)
        if name and name.lower() not in {"receiving", "tid", "sender"}:
            return name, phone

    return _counterparty_from_details(details)


def _parse_airtel_tables(tables: list[list[list[str | None]]]) -> list[StatementRow]:
    rows: list[StatementRow] = []
    for table in tables:
        if not table or len(table) < 2:
            continue
        header_idx = None
        colmap: dict[str, int] = {}
        for i, row in enumerate(table[:5]):
            colmap = _map_airtel_columns(row)
            if ("credit" in colmap or "debit" in colmap) and (
                "time" in colmap or "id" in colmap or "details" in colmap
            ):
                header_idx = i
                break
        if header_idx is None:
            continue

        for raw in table[header_idx + 1 :]:
            if not raw or all(c is None or str(c).strip() == "" for c in raw):
                continue

            def cell(key: str) -> str:
                idx = colmap.get(key)
                if idx is None or idx >= len(raw):
                    return ""
                return str(raw[idx] or "").replace("\n", " ").strip()

            status = cell("status").lower()
            if status and "success" not in status and status not in {"", "completed", "complete"}:
                continue

            details = cell("details") or ""
            if not details:
                continue

            credit = _to_float(cell("credit"))
            debit = _to_float(cell("debit"))
            balance = _to_float(cell("balance"))
            credit_v = abs(credit) if credit else 0.0
            debit_v = abs(debit) if debit else 0.0

            if credit_v > 0 and debit_v == 0:
                amount, direction = credit_v, Direction.IN
            elif debit_v > 0 and credit_v == 0:
                amount, direction = debit_v, Direction.OUT
            elif credit_v > 0 and debit_v > 0:
                # Misaligned OCR: prefer description wording
                amount = max(credit_v, debit_v)
                direction = Direction.IN
            else:
                continue

            ts_raw = cell("time")
            ts = _parse_dt(ts_raw) if ts_raw else None
            if ts is None:
                # Skip rows without a usable date — avoids isoformat crash
                continue

            txn_type, category, dir_hint = _classify_airtel_details(details)
            if dir_hint is not None:
                direction = dir_hint
                # If description says sent but only credit filled (OCR swap), keep OUT
                if dir_hint == Direction.OUT and credit_v > 0 and debit_v == 0:
                    amount = credit_v
                elif dir_hint == Direction.IN and debit_v > 0 and credit_v == 0:
                    amount = debit_v

            receipt = cell("id") or ""
            if not receipt:
                receipt_m = _RECEIPT.search(details)
                receipt = receipt_m.group(1) if receipt_m else hashlib.sha1(
                    f"{ts.isoformat()}|{details}|{amount}".encode()
                ).hexdigest()[:12]

            cp, phone = _airtel_counterparty(details)
            rows.append(
                StatementRow(
                    provider=Provider.AIRTEL_MONEY,
                    direction=direction,
                    transaction_type=txn_type,
                    category=category,
                    amount=amount,
                    fee=None,
                    balance=balance,
                    counterparty=cp,
                    counterparty_phone=phone,
                    transaction_id=receipt.strip(),
                    timestamp=ts,
                    confidence=Confidence.HIGH,
                    source_hash=_row_hash(
                        "airtel", receipt, ts.isoformat(), amount, details
                    ),
                    details=details,
                )
            )
    return rows


def parse_airtel_statement(data: bytes, password: str | None = None) -> list[StatementRow]:
    """Parse official Airtel Money PDF statements (Credit / Debit columns)."""
    pdf_bytes = _open_pdf_bytes(data, password)
    tables = _extract_tables(pdf_bytes)
    rows = _parse_airtel_tables(tables)

    if not rows:
        # Text fallback: line-oriented for when table extraction fails
        text = _extract_text(pdf_bytes)
        for line in text.splitlines():
            line = line.strip()
            if not line or "transaction successful" not in line.lower():
                # Many extractors put status on same row; also accept sent/received lines
                if not any(
                    k in line.lower()
                    for k in (
                        "sent money",
                        "received money",
                        "bundle purchase",
                        "airtime purchase",
                        "merchant payment",
                        "electricity",
                        "money received from bank",
                    )
                ):
                    continue

            ts_m = _DATE_TIME.search(line)
            ts = _parse_dt(ts_m.group(1)) if ts_m else None
            if ts is None:
                continue

            amounts = [float(m.replace(",", "")) for m in _AMOUNT.findall(line)]
            if not amounts:
                continue
            # Heuristic: last number often balance; use first money amount
            amount = amounts[0]
            txn_type, category, dir_hint = _classify_airtel_details(line)
            direction = dir_hint or Direction.OUT
            receipt_m = _RECEIPT.search(line)
            receipt = (
                receipt_m.group(1)
                if receipt_m
                else hashlib.sha1(line.encode()).hexdigest()[:12]
            )
            cp, phone = _airtel_counterparty(line)
            rows.append(
                StatementRow(
                    provider=Provider.AIRTEL_MONEY,
                    direction=direction,
                    transaction_type=txn_type,
                    category=category,
                    amount=amount,
                    fee=None,
                    balance=amounts[-1] if len(amounts) > 1 else None,
                    counterparty=cp,
                    counterparty_phone=phone,
                    transaction_id=receipt,
                    timestamp=ts,
                    confidence=Confidence.MEDIUM,
                    source_hash=_row_hash(
                        "airtel", receipt, ts.isoformat(), amount, line
                    ),
                    details=line,
                )
            )
    return rows


def parse_statement(
    data: bytes,
    provider: str,
    password: str | None = None,
) -> list[StatementRow]:
    provider = provider.strip().lower()
    if provider in {"mpesa", "m-pesa"}:
        return parse_mpesa_statement(data, password)
    if provider in {"airtel", "airtel_money", "airtelmoney"}:
        return parse_airtel_statement(data, password)
    raise ValueError("provider must be 'mpesa' or 'airtel_money'")
