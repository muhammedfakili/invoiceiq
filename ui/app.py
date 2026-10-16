"""InvoiceIQ review screen.

Upload invoices -> the API extracts and checks them -> a person reviews only the
flagged fields, corrects them, approves -> Excel export of approved invoices.

Run:  uv run streamlit run ui/app.py   (API must be running on INVOICEIQ_API_URL)
"""

from __future__ import annotations

import base64
from datetime import date

import streamlit as st

from ui.client import ApiClient, ApiError

st.set_page_config(page_title="InvoiceIQ", page_icon=":material/receipt_long:", layout="wide")

HEADER = [
    ("vendor_name", "Vendor", "text"), ("customer_name", "Customer", "text"),
    ("invoice_number", "Invoice number", "text"), ("currency", "Currency", "text"),
    ("invoice_date", "Invoice date", "date"), ("due_date", "Due date", "date"),
    ("subtotal", "Subtotal (net)", "money"), ("tax", "Tax", "money"),
    ("total", "Total", "money"), ("amount_due", "Amount due", "money"),
]


@st.cache_resource
def get_client() -> ApiClient:
    return ApiClient()


api = get_client()
st.session_state.setdefault("docs", {})  # name -> {"result", "invoice", "original", "status", ...}
st.session_state.setdefault("selected", None)
docs: dict = st.session_state.docs


def add_result(name: str, result: dict) -> None:
    docs[name] = {
        "result": result,
        "invoice": result["invoice"],
        "original": dict(result["invoice"]),
        "checks": result["checks"],
        "flags": result["flags"],
        "status": "needs review" if result["needs_review"] else "ready",
        "confirmed": False,
    }
    st.session_state.selected = name


def run_extraction(files: list[tuple[str, bytes]]) -> None:
    with st.status(f"Reading {len(files)} invoice(s)…", expanded=True) as status:
        for name, data in files:
            st.write(f"{name}…")
            try:
                add_result(name, api.extract(name, data))
            except ApiError as exc:
                st.error(f"{name}: {exc}")
        status.update(label="Done", state="complete", expanded=False)


# --------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.title(":material/receipt_long: InvoiceIQ")
    st.caption("LLM extraction · rule checks · human approval · Excel export")
    health = api.health()
    if health.get("status") == "ok":
        st.success(f"API ready · {health['model']}", icon=":material/check_circle:")
    else:
        st.error(f"API not reachable: {health.get('detail', health.get('status'))}", icon=":material/error:")

    uploads = st.file_uploader("Upload invoices", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)
    new = [f for f in uploads or [] if f.name not in docs]
    if st.button(f"Extract {len(new)} file(s)", disabled=not new, type="primary", width="stretch",
                 icon=":material/auto_awesome:"):
        run_extraction([(f.name, f.getvalue()) for f in new])
    if st.button("Try sample invoices", width="stretch", icon=":material/science:"):
        try:
            run_extraction([(n, api.sample(n)) for n in api.samples() if n not in docs])
        except ApiError as exc:
            st.error(str(exc))

    if docs:
        st.divider()
        counts = {s: sum(d["status"] == s for d in docs.values()) for s in ("ready", "needs review", "approved")}
        c1, c2, c3 = st.columns(3)
        c1.metric("Clean", counts["ready"])
        c2.metric("Flagged", counts["needs review"])
        c3.metric("Approved", counts["approved"])

# --------------------------------------------------------------------------- main

if not docs:
    st.title("Invoice review")
    st.info(
        "Upload PDFs, scans or phone photos of invoices in the sidebar, or try the sample invoices. "
        "Each one is read by an LLM, checked by rules (totals, dates, is the value really on the page?), "
        "and only the suspicious fields are highlighted for you.",
        title="Nothing to review yet",
        icon=":material/upload_file:",
    )
    st.stop()

ICON = {"ready": ":material/check_circle:", "needs review": ":material/warning:", "approved": ":material/verified:"}
names = list(docs)
if st.session_state.selected not in docs:
    st.session_state.selected = names[0]
# Labels must not change when a status changes: a changed label makes Streamlit treat the
# selectbox as a new widget and jump back to the first invoice (then "Approve" hits the wrong one).
selected = st.selectbox("Invoice", names, key="selected")
d = docs[selected]
res = d["result"]
inv = d["invoice"]

COLOR = {"ready": "green", "needs review": "orange", "approved": "blue"}
st.markdown(f":{COLOR[d['status']]}-badge[{ICON[d['status']]} {d['status']}] "
            f":gray[{res['kind'].replace('_', ' ')} · read in {res['mode']} mode · {res['seconds']:.1f} s · "
            f"{res['input_tokens']:,} tokens in]")

left, right = st.columns([5, 4], gap="large")

with left:
    for i, page in enumerate(res["pages"], 1):
        st.image(base64.b64decode(page["data_base64"]), caption=f"Page {i}/{len(res['pages'])}",
                 alt=f"Page {i} of {selected}")

with right:
    flags: dict = d["flags"]
    if d["status"] == "approved":
        st.success("Approved and included in the export.", icon=":material/verified:")
    elif flags:
        st.warning("Check the highlighted fields against the document, correct them if needed, then approve.",
                   title=f"{len(flags)} field(s) need a look", icon=":material/warning:")
    else:
        st.success("All checks passed. Glance over and approve.", icon=":material/check_circle:")

    with st.form(f"form-{selected}", border=True):
        edited: dict = {}
        cols = st.columns(2)
        for i, (field, label, kind) in enumerate(HEADER):
            col = cols[i % 2]
            flagged = field in flags
            shown = f":orange[**{label}**] :material/flag:" if flagged else label
            key = f"{selected}-{field}"
            value = inv.get(field)
            if kind == "text":
                edited[field] = col.text_input(shown, value=value or "", key=key)
            elif kind == "date":
                edited[field] = col.date_input(shown, value=date.fromisoformat(value) if value else None, key=key,
                                               format="YYYY-MM-DD")
            else:
                edited[field] = col.number_input(shown, value=float(value), step=0.01, format="%.2f", key=key)
            if flagged:
                col.caption(" · ".join(dict.fromkeys(flags[field])))

        st.markdown("**Line items**" + (" :orange[:material/flag:]" if "line_items" in flags else ""))
        if "line_items" in flags:
            st.caption(" · ".join(dict.fromkeys(flags["line_items"])))
        items = st.data_editor(
            inv["line_items"], num_rows="dynamic", key=f"{selected}-items", width="stretch",
            column_config={
                "description": st.column_config.TextColumn("Description", width="large"),
                "quantity": st.column_config.NumberColumn("Qty", format="%.2f"),
                "unit_price": st.column_config.NumberColumn("Unit price", format="%.2f"),
                "amount": st.column_config.NumberColumn("Amount", format="%.2f", required=True),
            },
            alt="Line items extracted from the invoice",
        )
        recheck = st.form_submit_button("Save and re-check", icon=":material/refresh:", width="stretch")

    if recheck:
        new_inv = {**inv, **{k: (v.isoformat() if isinstance(v, date) else v) for k, v in edited.items()}}
        new_inv["line_items"] = [row for row in items if row.get("description") or row.get("amount")]
        new_inv["uncertain_fields"] = []  # a human has now looked at it
        try:
            review = api.validate(new_inv)
        except ApiError as exc:
            st.error(f"Could not re-check: {exc}")
        else:
            d["invoice"], d["checks"], d["flags"] = new_inv, review["checks"], review["flags"]
            if d["status"] != "approved":
                d["status"] = "needs review" if review["needs_review"] else "ready"
            st.rerun()

    if d["status"] != "approved":
        if flags:
            d["confirmed"] = st.checkbox("I checked the flagged fields against the document", value=d["confirmed"],
                                         key=f"{selected}-confirm")
        if st.button("Approve", type="primary", icon=":material/verified:", width="stretch",
                     disabled=bool(flags) and not d["confirmed"]):
            d["status"] = "approved"
            st.rerun()
    elif st.button("Undo approval", icon=":material/undo:"):
        d["status"] = "needs review" if flags else "ready"
        st.rerun()

    with st.expander("All checks"):
        for c in d["checks"]:
            st.markdown(f"{':material/check:' if c['ok'] else ':orange[:material/close:]'} **{c['name']}** — "
                        f"{c['message']}")

# --------------------------------------------------------------------------- export

approved = [(n, x) for n, x in docs.items() if x["status"] == "approved"]
st.divider()
st.subheader(f"Export · {len(approved)} approved")
if approved:
    payload = [{
        "file": n,
        "invoice": x["invoice"],
        "corrected_fields": [f for f, *_ in HEADER if x["invoice"].get(f) != x["original"].get(f)]
        + (["line_items"] if x["invoice"]["line_items"] != x["original"]["line_items"] else []),
        "reviewed_flags": list(x["result"]["flags"]),
    } for n, x in approved]
    st.dataframe(
        [{"File": p["file"], "Vendor": p["invoice"]["vendor_name"], "Invoice no.": p["invoice"]["invoice_number"],
          "Date": p["invoice"]["invoice_date"], "Total": p["invoice"]["total"], "Currency": p["invoice"]["currency"],
          "Corrected": ", ".join(p["corrected_fields"])} for p in payload],
        hide_index=True, alt="Approved invoices ready for export",
    )
    try:
        st.download_button("Download Excel", api.export(payload), file_name=f"invoices-{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           type="primary", icon=":material/download:")
    except ApiError as exc:
        st.error(f"Export failed: {exc}")
else:
    st.caption("Approve invoices to add them to the Excel export.")
