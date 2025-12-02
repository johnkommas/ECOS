from typing import Any, Dict


def _first_scalar(val: Any) -> Any:
    """Return a scalar value from a pandas Series/list/tuple, preferring first non-None.
    If it's already a scalar, return as-is.
    """
    if val is None:
        return None
    try:
        # Avoid hard dependency if pandas isn't imported
        from pandas import Series  # type: ignore

        if isinstance(val, Series):
            for x in val.tolist():
                if x is not None:
                    return x
            return None
    except Exception:
        pass

    if isinstance(val, (list, tuple)):
        for x in val:
            if x is not None:
                return x
        return None
    return val


def check_document_status(df):
    # Exactly one row must be returned
    if df is None or df.shape[0] != 1:
        print(
            "Fail • CheckPoint 1/2 • Reason: Multiple records found, please refine the search"
            if df is not None and df.shape[0] != 1
            else "Fail • CheckPoint 1/2 • Reason: No record found"
        )
        return None

    print("Pass • CheckPoint 1/2 • Reason: Exactly one record found")
    row = df.iloc[0]

    # Resolve Status robustly (handles duplicate columns that yield a Series)
    status_val = None
    try:
        status_val = row["Status"] if "Status" in row.index else None
    except Exception:
        status_val = None
    status_val = _first_scalar(status_val)

    status_is_updatable = False
    if status_val is not None:
        try:
            status_is_updatable = int(status_val) == 0
        except Exception:
            s = str(status_val).strip()
            status_is_updatable = s in {"0", "False", "false"}

    if status_is_updatable:
        print("Pass • CheckPoint 2/2 • Reason: Record is updatable")
        # Resolve fDocumentGID robustly
        try:
            uid_val = row["fDocumentGID"] if "fDocumentGID" in row.index else None
        except Exception:
            uid_val = None
        unique_id = _first_scalar(uid_val)
        return unique_id
    else:
        print("Fail • CheckPoint 2/2 • Reason: Record is healthy (no update required)")
        return None


def evaluate_checkpoints(df) -> Dict[str, Any]:
    """Evaluate tri-state checkpoints on the dataframe result.

    Returns a dict:
    {
      'cp1': {'pass': bool, 'message': str},
      'cp2': {'pass': bool, 'message': str},
      'cp3': {'pass': bool, 'message': str},
      'all_pass': bool,
      'unique_id': str|None,
    }
    """
    result: Dict[str, Any] = {
        "cp1": {"pass": False, "message": ""},
        "cp2": {"pass": False, "message": ""},
        "cp3": {"pass": False, "message": ""},
        "all_pass": False,
        "unique_id": None,
    }

    # Checkpoint 1: Exactly one row
    if df is None or df.shape[0] != 1:
        msg = (
            "Checkpoint 1/3 Fail: Multiple records found"
            if df is not None and df.shape[0] != 1
            else "Checkpoint 1/3 Fail: No record found"
        )
        print(msg)
        result["cp1"] = {"pass": False, "message": msg}
        return result

    print("Checkpoint 1/3 Passed: Exactly one record found")
    result["cp1"] = {"pass": True, "message": "Checkpoint 1/3 Passed: Exactly one record found"}

    row = df.iloc[0]

    # Checkpoint 2: StatusText indicates successful submission to ECOS/IAPR
    # Accept multiple possible success messages
    success_markers = [
        "has already been sent to ECOS.",
        "Successfully submitted to IAPR",
    ]
    try:
        st_raw = row["StatusText"] if "StatusText" in row.index else None
    except Exception:
        st_raw = None
    st_raw = _first_scalar(st_raw)
    st_str = str(st_raw).strip() if st_raw is not None else ""
    st_low = st_str.lower()
    markers_low = [m.lower() for m in success_markers]
    if any(m in st_low for m in markers_low):
        print("Checkpoint 2/3 Passed: Record has already been sent to ECOS")
        result["cp2"] = {"pass": True, "message": "Checkpoint 2/3 Passed: Record has already been sent to ECOS"}
    else:
        msg2 = "Checkpoint 2/3 Fail: Record has not been sent to ECOS yet"
        print(msg2)
        result["cp2"] = {"pass": False, "message": msg2}

    # Checkpoint 3: Updatable (Status == 0)
    try:
        status_val = row["Status"] if "Status" in row.index else None
    except Exception:
        status_val = None
    status_val = _first_scalar(status_val)

    status_is_updatable = False
    if status_val is not None:
        try:
            status_is_updatable = int(status_val) == 0
        except Exception:
            s = str(status_val).strip()
            status_is_updatable = s in {"0", "False", "false"}

    if status_is_updatable:
        print("Checkpoint 3/3 Passed: Record is updatable")
        result["cp3"] = {"pass": True, "message": "Checkpoint 3/3 Passed: Record is updatable"}
        # Resolve unique id
        try:
            uid_val = row["fDocumentGID"] if "fDocumentGID" in row.index else None
        except Exception:
            uid_val = None
        result["unique_id"] = _first_scalar(uid_val)
    else:
        msg3 = "Checkpoint 3/3 Fail: Record is healthy (no update required)"
        print(msg3)
        result["cp3"] = {"pass": False, "message": msg3}

    result["all_pass"] = bool(result["cp1"]["pass"] and result["cp2"]["pass"] and result["cp3"]["pass"])
    return result