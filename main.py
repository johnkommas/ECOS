import socket
import base64
import binascii
import re
from datetime import datetime

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from SQL import fetch_data, check
from SQL import set as sql_set

# Centralized SQL file registry for maintainability
SQL_FILES = {
    "check": "check.sql",
    "set": "set.sql",
    "auto": "auto.sql",
    "update_wrong_login_day": "update_wrong_login_day.sql",
}

app = FastAPI(title="ECOS Document Fix Tool")

# Mount static and images
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="images"), name="images")

templates = Jinja2Templates(directory="templates")


def _format_datetime(value):
    """Format various date-like inputs to 'dd.mm.yyyy • hh:mm:ss'. Returns None if not parseable."""
    if value is None or value == "":
        return None
    try:
        # pandas Timestamp support (optional)
        try:
            import pandas as pd  # type: ignore

            if isinstance(value, pd.Timestamp):
                value = value.to_pydatetime()
        except Exception:
            pass

        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y • %H:%M:%S")
        if isinstance(value, str):
            s = value.strip()
            # Normalize 'Z' suffix to offset for fromisoformat
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            # Try ISO first
            try:
                dt = datetime.fromisoformat(s)
                return dt.strftime("%d.%m.%Y • %H:%M:%S")
            except Exception:
                pass
            # Try a few common formats
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%d.%m.%Y • %H:%M:%S")
                except Exception:
                    continue
        # Fallback string
        return str(value)
    except Exception:
        return None


def _to_datetime(value):
    """Parse various date-like inputs and return a datetime or None."""
    if value is None or value == "":
        return None
    try:
        # pandas Timestamp support (optional)
        try:
            import pandas as pd  # type: ignore
            if isinstance(value, pd.Timestamp):
                return value.to_pydatetime()
        except Exception:
            pass

        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(s)
            except Exception:
                pass
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
        return None
    except Exception:
        return None


def _sort_df_by_datetime(df, columns=None):
    """Return a copy of df sorted by the best available datetime column (ascending).
    Tries provided columns first, then common datetime-like names. If none match,
    returns the original df unchanged.
    """
    try:
        if df is None or getattr(df, "empty", True):
            return df

        # Build case-insensitive column map
        cols_map = {str(c).lower(): c for c in getattr(df, "columns", [])}

        # Candidate columns to try (preference order)
        preferred = columns or [
            "esdcreated",  # main document datetime in our queries
            "esucreated",
            "createdat",
            "createdon",
            "createddate",
            "creationdate",
            "date",
            "timestamp",
            "created",
        ]

        # If none of the preferred exist, try to auto-detect by substring
        candidates = []
        for key in preferred:
            if key in cols_map:
                candidates.append(cols_map[key])
        if not candidates:
            for c in getattr(df, "columns", []):
                lc = str(c).lower()
                if any(s in lc for s in ("created", "date", "time", "timestamp")):
                    candidates.append(c)
            # Keep original order but unique
            seen = set()
            candidates = [x for x in candidates if not (x in seen or seen.add(x))]

        # Try sorting by the first usable candidate
        for col in candidates:
            try:
                # Convert values to float timestamps (None -> +inf) for safe sorting
                def _to_ts(v):
                    dt = _to_datetime(v)
                    try:
                        return dt.timestamp() if dt is not None else float("inf")
                    except Exception:
                        return float("inf")

                sorted_df = df.sort_values(by=col, key=lambda s: s.apply(_to_ts), ascending=True, kind="mergesort")
                return sorted_df
            except Exception:
                continue
        return df
    except Exception:
        return df


def _format_number(value):
    """Format numeric values with 2 decimals and thousand separators in Greek style (1.234,56)."""
    try:
        if value is None or value == "":
            return None
        num = float(value)
        s = f"{num:,.2f}"  # e.g., 12,345.67
        # Convert to European style: 12.345,67
        s = s.replace(",", "_").replace(".", ",").replace("_", ".")
        return s
    except Exception:
        try:
            return str(value)
        except Exception:
            return None


def _normalize_url(value: str | None):
    if not value:
        return None
    u = str(value).strip()
    if not u:
        return None
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u):
        # If it looks like a domain/path, assume https
        if re.match(r"^[\w.-]+(/.*)?$", u):
            u = "https://" + u
    return u


def build_card_context(df, document: str):
    """Builds context for the single result card and fix button state."""
    context = {
        "document": document,
        "result_found": False,
        "multiple": False,
        "can_fix": False,
        "id_to_update": None,
        "status_message": None,
        "row": None,
        "qr_data_url": None,
        "result_count": None,
        "checkpoints": None,
    }

    if df is None or df.empty:
        context["status_message"] = "No records were found for the given document."
        return context

    # Ensure consistent ordering: older first, newer last
    try:
        df = _sort_df_by_datetime(df, columns=["ESDCreated", "ESUCreated"])  # type: ignore[arg-type]
    except Exception:
        pass

    # Keep only one card always – inspect only the first row visually
    # Drop NA values to avoid showing empty fields
    row = df.iloc[0]
    try:
        row = row.dropna()
    except Exception:
        # If for any reason dropna isn't available, continue with the raw row
        pass
    row_dict = row.to_dict()
    context["row"] = row_dict
    context["result_found"] = True
    # Total matched rows
    try:
        context["result_count"] = int(df.shape[0])
    except Exception:
        context["result_count"] = None

    # Determine if multiple rows matched
    if df.shape[0] != 1:
        context["multiple"] = True
        context["status_message"] = (
            "More than one record was found. Please refine your search."
        )

    # New tri-state checkpoints evaluation
    eval_res = check.evaluate_checkpoints(df)
    cp1 = eval_res.get("cp1", {"pass": False, "message": ""})
    cp2 = eval_res.get("cp2", {"pass": False, "message": ""})
    cp3 = eval_res.get("cp3", {"pass": False, "message": ""})
    context["checkpoints"] = [
        {"label": "Checkpoint 1", "pass": bool(cp1.get("pass")), "message": cp1.get("message")},
        {"label": "Checkpoint 2", "pass": bool(cp2.get("pass")), "message": cp2.get("message")},
        {"label": "Checkpoint 3", "pass": bool(cp3.get("pass")), "message": cp3.get("message")},
    ]
    all_pass = bool(eval_res.get("all_pass"))
    uid = eval_res.get("unique_id")
    context["can_fix"] = all_pass
    context["id_to_update"] = uid if all_pass else None
    # If any checkpoint failed, capture the first failure reason as status_message (informational)
    if not all_pass:
        for cp in context["checkpoints"]:
            if not cp["pass"] and cp.get("message"):
                context["status_message"] = cp["message"]
                break

    # Build grouped info (basic, user, provider, pricing)
    shown_keys = set()
    def add_shown(k):
        if k:
            shown_keys.add(k)

    # Helper: resolve the first non-empty value from a list of possible column names
    def _resolve_first(keys):
        for k in keys:
            if k in row_dict:
                v = row_dict.get(k)
                if v is not None and str(v).strip() != "":
                    return k, v
        return None, None

    status_val = row_dict.get("Status")
    # Map numeric status to human-readable English messages
    display_status = None
    try:
        if status_val is not None and str(status_val).strip() != "":
            sv = str(status_val).strip()
            if sv in {"1", "True", "true"}:
                display_status = "Submitted Successfully"
            elif sv in {"0", "False", "false"}:
                display_status = "Submission Failed"
            else:
                display_status = sv
    except Exception:
        display_status = status_val
    uid_val = row_dict.get("fDocumentGID")
    mark_id_val = row_dict.get("MarkID")
    invoice_raw = row_dict.get("InvoiceURL")
    esu_created = row_dict.get("ESUCreated")
    esd_created = row_dict.get("ESDCreated")
    provider_name = row_dict.get("ProviderName")

    invoice_href = _normalize_url(invoice_raw)

    # Groups per request
    basic_info = [
        {"label": "Document", "value": document},
        {"label": "Status", "value": display_status, "key": "Status"},
        {"label": "GID", "value": uid_val, "key": "fDocumentGID"},
    ]
    # Insert UID directly under GID (resolve common aliases)
    uid_key2, uid_val2 = _resolve_first(["UID", "Uid", "DocumentUID", "fDocumentUID", "ADUID"])
    if uid_val2 is not None and str(uid_val2).strip() != "":
        basic_info.append({"label": "UID", "value": str(uid_val2).strip(), "key": uid_key2 or "UID"})
    # Then AuthenticationCode directly under UID
    auth_code = row_dict.get("AuthenticationCode")
    if auth_code is not None and str(auth_code).strip() != "":
        basic_info.append({"label": "AuthenticationCode", "value": str(auth_code).strip(), "key": "AuthenticationCode"})
    # Place MarkID after AuthenticationCode if available
    basic_info.append({"label": "MarkID", "value": mark_id_val, "key": "MarkID"})
    # User name must come from ESUCreated per requirements (strict)
    user_name = None
    esu_created_str = row_dict.get("ESUCreated")
    if esu_created_str is not None and str(esu_created_str).strip() != "":
        user_name = str(esu_created_str).strip()
    else:
        # If ESUCreated is missing/empty, add a soft diagnostic in English
        existing_msg = context.get("status_message")
        note = "No value found in field ESUCreated for the record."
        context["status_message"] = (existing_msg + "\n" + note) if existing_msg else note

    user_info = [
        {"label": "User", "value": user_name, "key": "ESUCreated"},
        {"label": "Date", "value": _format_datetime(esd_created), "key": "ESDCreated"},
    ]
    # Expose date parts (day/month) for the visual date badge in User Info
    user_date = None
    try:
        dt = _to_datetime(esd_created)
        if dt is not None:
            months_gr = [
                "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
            ]
            user_date = {
                "day": dt.strftime("%d"),
                "month": months_gr[dt.month - 1],
            }
    except Exception:
        user_date = None
    provider_info = [
        {"label": "Provider", "value": provider_name, "key": "ProviderName"},
        {"label": "Invoice Link", "value": invoice_raw if invoice_href else None, "href": invoice_href, "is_link": True, "key": "InvoiceURL"},
        # QR Code rendered in template using context["qr_data_url"], but mark key as shown to avoid duplication below
        {"label": "QR Code", "value": None, "key": "QRCode", "is_qr": True},
    ]
    # Track shown keys
    for item in basic_info:
        k = item.get("key")
        if k:
            add_shown(k)
    for item in user_info:
        k = item.get("key")
        if k:
            add_shown(k)
    for item in provider_info:
        k = item.get("key")
        if k:
            add_shown(k)

    # Currency price fields per requirements (with safe fallbacks to common alternatives)
    # Try currency fields first; fallback to AD* or generic names if currency fields are absent.
    net_key, net_val = _resolve_first(["CurrencyNetValue", "ADNetValue", "NetValue"])
    vat_key, vat_val = _resolve_first(["CurrencyVATValue", "ADVATValue", "VATValue", "VatValue"])
    total_key, total_val = _resolve_first(["CurrencyTotalValue", "ADTotalValue", "TotalValue"])

    price_info = [
        {"label": "Net Amount", "value": _format_number(net_val), "key": net_key or "CurrencyNetValue"},
        {"label": "VAT Amount", "value": _format_number(vat_val), "key": vat_key or "CurrencyVATValue"},
        {"label": "Total", "value": _format_number(total_val), "key": total_key or "CurrencyTotalValue"},
    ]

    # If any fallback (non-Currency*) was used, add a brief note for visibility
    used_fallback = any(k and not k.startswith("Currency") for k in [net_key, vat_key, total_key])
    if used_fallback:
        fb_note = "Prices are shown from alternative fields because Currency* fields are missing."
        existing_msg = context.get("status_message")
        context["status_message"] = (existing_msg + "\n" + fb_note) if existing_msg else fb_note
    for item in price_info:
        k = item.get("key")
        if k:
            add_shown(k)

    # Payment info mapping (fCashAccountTypeCode and AuthorizationID)
    pay_code = None
    try:
        v = row_dict.get("fCashAccountTypeCode")
        pay_code = (str(v).strip() if v is not None else None)
    except Exception:
        pay_code = None

    payment = None
    if pay_code:
        # Map codes to human readable labels and icons
        pay_map = {
            # Codes remain the same; display strings in English
            "ΜΕΤ": {"display": "Cash Payment", "icon": "fa-money-bill-1-wave"},
            "ΠΚΑ": {"display": "Credit Card", "icon": "fa-credit-card"},
        }
        m = pay_map.get(pay_code)
        display = m["display"] if m else f"Unknown Payment Method ({pay_code})"
        icon = m["icon"] if m else "fa-circle-question"

        auth_id = None
        try:
            a = row_dict.get("AuthorizationID")
            auth_id = (str(a).strip() if a is not None and str(a).strip() != "" else None)
        except Exception:
            auth_id = None

        payment = {
            "code": pay_code,
            "display": display,
            "icon": icon,
            "auth_id": auth_id if pay_code == "ΠΚΑ" else None,
        }
        add_shown("fCashAccountTypeCode")
        if payment["auth_id"]:
            add_shown("AuthorizationID")

    context["basic_info"] = basic_info
    context["user_info"] = user_info
    context["user_date"] = user_date
    context["provider_info"] = provider_info
    context["price_info"] = price_info
    context["payment"] = payment
    context["shown_keys"] = sorted(shown_keys)

    # DEBUG: Print key data to terminal to help investigate missing values
    # try:
    #     print("\n===== DEBUG • build_card_context =====")
    #     print(f"Document: {document}")
    #     try:
    #         cols = sorted([str(k) for k in row_dict.keys()])
    #         print("Available columns (first 40):", ", ".join(cols[:40]), ("…" if len(cols) > 40 else ""))
    #     except Exception:
    #         pass
    #     print(f"ESUCreated (user): {repr(esu_created)}")
    #     print(f"ESDCreated (timestamp): {repr(esd_created)}")
    #     print(f"ProviderName: {repr(provider_name)}")
    #     print(f"InvoiceURL raw: {repr(invoice_raw)}")
    #     print(f"InvoiceURL normalized: {repr(invoice_href)}")
    #     print(f"Status:, {repr(status_val)}")
    #     print(
    #         "Prices → "
    #         f"net[{net_key}]={repr(net_val)}, "
    #         f"vat[{vat_key}]={repr(vat_val)}, "
    #         f"total[{total_key}]={repr(total_val)}"
    #     )
    #     raw_qr_dbg = row_dict.get("QRCode") if isinstance(row_dict, dict) else None
    #     if raw_qr_dbg is None or raw_qr_dbg == "":
    #         print("QRCode: <empty>")
    #     elif isinstance(raw_qr_dbg, (bytes, bytearray, memoryview)):
    #         print(f"QRCode: bytes length={len(bytes(raw_qr_dbg))}")
    #     else:
    #         s_dbg = str(raw_qr_dbg)
    #         print(f"QRCode: str length={len(s_dbg)} prefix={s_dbg[:16]!r}")
    #     print("===== /DEBUG • build_card_context =====\n")
    # except Exception:
    #     # Never allow debug printing to break the request
    #     pass

    # Prepare QR image data URL if QRCode is present
    try:
        raw_qr = row_dict.get("QRCode") if isinstance(row_dict, dict) else None
        data_url = None
        if raw_qr is not None and raw_qr != "":
            # bytes-like
            if isinstance(raw_qr, (bytes, bytearray, memoryview)):
                b = bytes(raw_qr)
                # validate PNG signature
                if len(b) >= 8 and b[:8] == b"\x89PNG\r\n\x1a\n":
                    data_url = "data:image/png;base64," + base64.b64encode(b).decode("ascii")
            else:
                # normalize to string
                s = str(raw_qr).strip()
                if s.startswith("data:"):
                    # assume already a valid data URL
                    data_url = s
                else:
                    # Try base64 first
                    b = None
                    try:
                        b = base64.b64decode(s, validate=True)
                    except (binascii.Error, ValueError):
                        b = None
                    if not b:
                        # Try HEX string
                        if len(s) % 2 == 0 and re.fullmatch(r"[0-9A-Fa-f]+", s or ""):
                            try:
                                b = bytes.fromhex(s)
                            except ValueError:
                                b = None
                    if b and len(b) >= 8 and b[:8] == b"\x89PNG\r\n\x1a\n":
                        data_url = "data:image/png;base64," + base64.b64encode(b).decode("ascii")
                    # Some sources store base64 without validation but still decodable
                    elif s.startswith("iVBOR"):
                        # PNG base64 commonly starts with 'iVBORw0KGgo'
                        try:
                            b2 = base64.b64decode(s + ("=" * ((4 - len(s) % 4) % 4)))
                            if len(b2) >= 8 and b2[:8] == b"\x89PNG\r\n\x1a\n":
                                data_url = "data:image/png;base64," + base64.b64encode(b2).decode("ascii")
                        except Exception:
                            pass
        context["qr_data_url"] = data_url
    except Exception:
        # Silently ignore QR parsing issues
        context["qr_data_url"] = None

    return context


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logo_url": "/images/SOFTONE-EINVOICING.svg",
            "card": None,
            "message": None,
            "auto_results": None,
        },
    )


@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, document: str = Form(...)):
    params = {"document": document}
    df = fetch_data.get_sql_data(SQL_FILES["check"], params)
    card = build_card_context(df, document)
    # Keep auto search results visible after selecting a document
    df_auto = fetch_data.get_sql_data(SQL_FILES["auto"])
    auto_results = _extract_documents_list(df_auto)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logo_url": "/images/SOFTONE-EINVOICING.svg",
            "card": card,
            "message": None,
            "auto_results": auto_results,
        },
    )


@app.post("/fix", response_class=HTMLResponse)
async def fix(request: Request, document: str = Form(...)):
    # Re-run search and validation server-side
    params = {"document": document}
    df = fetch_data.get_sql_data(SQL_FILES["check"], params)
    card = build_card_context(df, document)

    # Default values
    message = None
    affected = 0

    # Special case: AADE IssueDate validation error can be fixed with a different SQL
    special_error = "Aade Validation Error: IssueDate is invalid, it must be equal with current date"
    status_text = None
    try:
        status_text = (card.get("row") or {}).get("StatusText")
        status_text = str(status_text).strip() if status_text is not None else None
    except Exception:
        status_text = None

    # Evaluate checkpoint pass flags from the card (order is cp1, cp2, cp3)
    cp_list = card.get("checkpoints") or []
    cp1_pass = bool(cp_list[0]["pass"]) if len(cp_list) >= 1 else False
    cp3_pass = bool(cp_list[2]["pass"]) if len(cp_list) >= 3 else False

    # Decide which SQL to use
    sql_to_use = None
    post_success_hint = None
    if (
        status_text == special_error
        and cp1_pass
        and cp3_pass
        and card.get("id_to_update")
    ):
        # Use the dedicated update for wrong login day / issue date
        sql_to_use = SQL_FILES["update_wrong_login_day"]
        post_success_hint = "να γίνει ενημέρωση offline συναλλαγών"
    elif card.get("can_fix") and card.get("id_to_update"):
        # Fallback to normal set.sql
        sql_to_use = SQL_FILES["set"]

    if sql_to_use and card.get("id_to_update"):
        affected = sql_set.update(card["id_to_update"], sql_to_use)
        if affected:
            message = f"Update completed successfully (affected: {affected})."
            if post_success_hint:
                # Surface the requested hint prominently in the card status area
                existing = card.get("status_message")
                hint_msg = post_success_hint
                card["status_message"] = (
                    f"{existing} — {hint_msg}" if existing else hint_msg
                )
                # Also show as popup/alert message
                message = f"{message} — {post_success_hint}"
            # Re-fetch to reflect new status after update
            df_after = fetch_data.get_sql_data(SQL_FILES["check"], params)
            card = build_card_context(df_after, document)
        else:
            message = "Update failed. Please try again."
    else:
        message = "Fix is not possible for the current result."

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logo_url": "/images/SOFTONE-EINVOICING.svg",
            "card": card,
            "message": message,
            # Keep auto search results visible after fix
            "auto_results": _extract_documents_list(fetch_data.get_sql_data(SQL_FILES["auto"])),
        },
    )


@app.get("/search/{document}", response_class=HTMLResponse)
async def search_get(request: Request, document: str):
    params = {"document": document}
    df = fetch_data.get_sql_data(SQL_FILES["check"], params)
    card = build_card_context(df, document)
    # Keep auto search results visible while viewing a selected document
    df_auto = fetch_data.get_sql_data(SQL_FILES["auto"])
    auto_results = _extract_documents_list(df_auto)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logo_url": "/images/SOFTONE-EINVOICING.svg",
            "card": card,
            "message": None,
            "auto_results": auto_results,
        },
    )


def _extract_documents_list(df):
    """Return a list of document codes (adcode) from auto.sql results.
    Tries common column name variants and ensures uniqueness while keeping order.
    """
    results = []
    if df is None or df.empty:
        return results
    # Sort by datetime so that the resulting list is oldest-first
    try:
        df = _sort_df_by_datetime(df, columns=["ESDCreated", "ESUCreated"])  # type: ignore[arg-type]
    except Exception:
        pass
    cols = {c.lower(): c for c in df.columns}
    # Resolve document column (ADCode or similar)
    ad_col = None
    for key in ("adcode", "ad_code", "document", "doc", "code"):
        if key in cols:
            ad_col = cols[key]
            break
    if not ad_col:
        # Fallback: attempt exact case-insensitive match
        for c in df.columns:
            if c.lower() == "adcode":
                ad_col = c
                break
    # Resolve status column
    status_col = None
    for key in ("status",):
        if key in cols:
            status_col = cols[key]
            break
    if not ad_col:
        return results
    seen = set()
    # Iterate rows to carry both document and status forward
    for _, row in df.iterrows():
        try:
            raw_doc = row.get(ad_col) if isinstance(row, dict) else row[ad_col]
        except Exception:
            raw_doc = None
        doc = str(raw_doc).strip() if raw_doc is not None else ""
        if not doc or doc in seen:
            continue
        seen.add(doc)
        # Extract status
        status_val = None
        if status_col:
            try:
                raw_status = row.get(status_col) if isinstance(row, dict) else row[status_col]
            except Exception:
                raw_status = None
            if raw_status is not None and str(raw_status).strip() != "":
                try:
                    status_val = int(str(raw_status).strip())
                except Exception:
                    # keep as None if unparsable
                    status_val = None
        results.append({"document": doc, "status": status_val})
    return results


@app.get("/refresh", response_class=HTMLResponse)
async def refresh(request: Request):
    # Run the auto discovery SQL to find candidate documents
    df = fetch_data.get_sql_data(SQL_FILES["auto"])
    auto_results = _extract_documents_list(df)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "logo_url": "/images/SOFTONE-EINVOICING.svg",
            "card": None,
            "message": None,
            "auto_results": auto_results,
        },
    )
def get_ip_address():
    """
    Gets the local IP address by connecting to Google's DNS server.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

# Convenience for local development (optional)
if __name__ == "__main__":
    import uvicorn

    my_ip = get_ip_address()  # Get the actual IP address for display purposes
    uvicorn.run("main:app", host=my_ip, port=8080, reload=True)



