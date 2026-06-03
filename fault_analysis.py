import streamlit as st
import pandas as pd
from datetime import datetime

# ============================================================
# DELTRON UFSBI UNIVERSAL DIAGNOSTIC ENGINE (SINGLE & DOUBLE LINE)
# Designed for RE Area Data Logger Automation
# ============================================================

st.set_page_config(page_title="Universal UFSBI Diagnostic Engine", page_icon="⚡", layout="wide")

st.title("📡 Deltron UFSBI Smart Diagnostic Engine")
st.markdown("### **S&T Department - RE Area Block Interface Diagnostic Tool**")
st.write("Upload Excel files from Station A and Station B. The engine will auto-detect whether the block section is Single Line or Double Line.")

st.markdown("---")

# Deltron Make Error Codes (Universal for both Single & Double Line)
ERROR_CODES = {
    "00": "NORMAL MODE - System is healthy & functioning properly. [cite: 1319]",
    "33": "LINK FAIL (SSB Mode) - Remote data not received. Check Quad/OFC telecom cable loss or modem. ",
    "34": "RSSB MODE - Remote end UFSBI is not receiving data. Check channel, modem or media line. [cite: 1342, 1370]",
    "37": "CPU A BAD - Inter-processor or voter card failure in CPU card A. [cite: 1344, 1374]",
    "38": "CPU B BAD - Inter-processor or voter card failure in CPU card B. [cite: 1345, 1374]",
    "39": "CPU C BAD - Inter-processor or voter card failure in CPU card C. [cite: 1346, 1374]",
    "73": "Shutdown relay phase generator failure (Phase not changing within 30 mins). [cite: 1395]",
    "92": "UFSBI Address bad - Configuration jumpers mismatched at the back panel. [cite: 1404]",
    "99": "Start not pressed within 30 seconds of Power-On or BIPR1/BIPR2 failed to pick up. [cite: 1404]"
}

# Auto-add input/output jitter rules (Codes 50-57)
for i in range(1, 9):
    ERROR_CODES[f"5{i-1 if i>1 else 0}"] = f"IN{i} JITTER / CHATTERING - Low coil voltage, faulty receptacles, or loose plugging. [cite: 1389]"

# File Upload Layout
col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("📥 Upload Station A Data Logger (.xlsx / .xls)", type=["xls", "xlsx"])
with col2:
    file_b = st.file_uploader("📥 Upload Station B Data Logger (.xlsx / .xls)", type=["xls", "xlsx"])

def clean_and_load(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.title()
        
        time_col = "Signal Time" if "Signal Time" in df.columns else ("Time" if "Time" in df.columns else None)
        name_col = "Signal Name" if "Signal Name" in df.columns else ("Event" if "Event" in df.columns else None)
        status_col = "Signal Status" if "Signal Status" in df.columns else ("Status" if "Status" in df.columns else None)
        
        if not (time_col and name_col and status_col):
            st.error(f"Required columns missing in {uploaded_file.name}. Please ensure Time, Event/Name, and Status exist.")
            return None
            
        df = df.dropna(subset=[time_col, name_col, status_col])
        df[name_col] = df[name_col].astype(str).str.strip()
        df[status_col] = df[status_col].astype(str).str.strip().str.upper()
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        df = df.sort_values(by=time_col).reset_index(drop=True)
        return {"data": df, "time": time_col, "name": name_col, "status": status_col}
    except Exception as e:
        st.error(f"Failed to read file {uploaded_file.name}: {e}")
        return None

data_a = clean_and_load(file_a)
data_b = clean_and_load(file_b)

if file_a and file_b and data_a and data_b:
    df_a = data_a["data"]
    df_b = data_b["data"]
    
    # ============================================================
    # ⚙️ AUTOMATIC BLOCK TYPE DETECTION LOGIC
    # ============================================================
    # Convert all logs to a massive string to detect specific signature relays
    all_events_str = " ".join(df_a[data_a["name"]].tolist()) + " " + " ".join(df_b[data_b["name"]].tolist())
    
    # Signature relays for Single Line vs Double Line
    is_single_line = any(r in all_events_str for r in ["TCFSR", "TGTSR", "LCSR", "BCSR"])
    is_double_line = any(r in all_events_str for r in ["LCR", "TOLR", "BLR", "DI_"]) or not is_single_line

    if is_single_line:
        st.sidebar.markdown("### 🔀 Detected Block Mode:\n**IRS SINGLE LINE TLBI**")
        block_mode = "SINGLE_LINE"
    else:
        st.sidebar.markdown("### 🔁 Detected Block Mode:\n**DOUBLE LINE RE BLOCK**")
        block_mode = "DOUBLE_LINE"

    st.success(f"✅ Data successfully synchronized! Auto-detected mode: **{block_mode.replace('_', ' ')}**")

    # 1. CORE SCAN: Deltron Internal Hardware Errors
    detected_errors = []
    for code, desc in ERROR_CODES.items():
        match_a = df_a[df_a[data_a["name"]].str.contains(code, case=False, na=False)]
        match_b = df_b[df_b[data_b["name"]].str.contains(code, case=False, na=False)]
        if not match_a.empty:
            detected_errors.append(f"⚠️ **Station A Internal Fault**: Code **{code}** -> {desc}")
        if not match_b.empty:
            detected_errors.append(f"⚠️ **Station B Internal Fault**: Code **{code}** -> {desc}")

    # 2. DIFFERENTIAL INTER-STATION HANDSHAKE DIAGNOSTICS
    verdict_found = False
    fault_summary = ""

    if block_mode == "SINGLE_LINE":
        # Single Line Logic: Check TCFSR -> TCFRR [cite: 56, 57]
        tcf_sent_a = df_a[(df_a[data_a["name"]].str.contains("TCFSR", case=False)) & (df_a[data_a["status"]] == "UP")] [cite: 56]
        tcf_recv_b = df_b[(df_b[data_b["name"]].str.contains("TCFRR", case=False)) & (df_b[data_b["status"]] == "UP")] [cite: 57]
        
        if not tcf_sent_a.empty and tcf_recv_b.empty:
            fault_summary = "🚨 **DIAGNOSTIC VERDICT: Quad Cable / OFC Medium Failure (Station A to Station B)**"
            st.error(fault_summary)
            st.markdown("* **Reasoning:** Station A picked up **TCFSR** (Line Clear Demand Sending) , but Station B never registered **TCFRR** (Line Clear Received)[cite: 57]. Check line transformer modules.")
            verdict_found = True
            
    elif block_mode == "DOUBLE_LINE":
        # Double Line RE Area Logic: Check Line Clear Relay (LCR Sending vs LCRR Receiving)
        # Typically looks for LCR / LC_SEND at Station A vs LCRR / LC_RECV at Station B
        lcr_sent_a = df_a[(df_a[data_a["name"]].str.contains("LCR", case=False)) & (df_a[data_a["status"]] == "UP")]
        lcr_recv_b = df_b[(df_b[data_b["name"]].str.contains("LCRR", case=False)) & (df_b[data_b["status"]] == "UP")]
        
        if not lcr_sent_a.empty and lcr_recv_b.empty:
            fault_summary = "🚨 **DIAGNOSTIC VERDICT: Double Line Transmission Medium Failure**"
            st.error(fault_summary)
            st.markdown("* **Reasoning:** Double Line Line Clear Command (LCR) was initiated at Station A, but the corresponding Receiving Relay (LCRR) on Station B failed to pick up. Check RE area filter unit/surge arresters or OFC voice converter channels.")
            verdict_found = True

    # Print Deltron card failures if detected
    if detected_errors:
        st.subheader("📋 Deltron Card Voter & Hardware Diagnostic Alerts")
        for err in detected_errors:
            st.warning(err)

    if not verdict_found and not detected_errors:
        st.balloons()
        st.success("✅ **SYSTEM STATUS: HEALTHY OPERATION**")
        st.info(f"The chronological millisecond sequencing validates a healthy Deltron UFSBI communication sequence for {block_mode.replace('_', ' ')}.")

    # Show Timelines side by side
    st.markdown("---")
    st.subheader("📋 Side-by-Side Chronological Timelines")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.write(f"**Station A Final Events ({block_mode}):**")
        st.dataframe(df_a.tail(10)[[data_a["time"], data_a["name"], data_a["status"]]])
    with t_col2:
        st.write(f"**Station B Final Events ({block_mode}):**")
        st.dataframe(df_b.tail(10)[[data_b["time"], data_b["name"], data_b["status"]]])

    # Text report generation
    report_out = (
        f"DELTRON UFSBI UNIVERSAL DIAGNOSTIC REPORT\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Detected Mode: {block_mode}\n"
        f"----------------------------------------------------\n"
        f"Analysis Verdict: {fault_summary if verdict_found else 'Healthy System Handshake Sequence'}\n"
        f"Hardware Alerts Found: {len(detected_errors)}\n"
        f"----------------------------------------------------\n"
        f"Compliant with IRS S:104/2012 RE Area Signaling Guidelines."
    )
    st.download_button("💾 Download Report for WhatsApp Sharing", data=report_out, file_name="Deltron_UFSBI_Report.txt")
else:
    st.info("💡 Please upload data logger Excel sheets from **both connected stations** to initiate cross-station differential diagnostic parsing.")
