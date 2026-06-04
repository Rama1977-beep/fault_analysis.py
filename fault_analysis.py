import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ============================================================
# DELTRON UFSBI STRICT SEQUENTIAL DIAGNOSTIC ENGINE (IRS & RE)
# Developed strictly based on S&T Workshop Podanur Technical Manual
# ============================================================

st.set_page_config(page_title="Sequential UFSBI Expert System", page_icon="📡", layout="wide")

st.title("🎛️ Deltron UFSBI Strict Sequential Diagnostic Engine")
st.markdown("### **S&T Department - High-Fidelity Signal Automation & Breach Detector**")
st.write("Upload separate log files for Station A and Station B of the same time window to run multi-station state-machine analytics.")

st.markdown("---")

# Comprehensive Hardware Diagnostics Matrix
DELTRON_CODES = {
    "33": "LINK FAIL (SSB Mode) - Quad Cable / OFC Medium interruption or high signal loss (>30dB).",
    "34": "RSSB MODE - Remote UFSBI unit is alive but reporting that it cannot receive your data packs.",
    "37": "CPU CARD A BAD - Vote mismatch or internal fault inside processing module A.",
    "38": "CPU CARD B BAD - Vote mismatch or internal fault inside processing module B.",
    "39": "CPU CARD C BAD - Vote mismatch or internal fault inside processing module C.",
    "73": "Phase generator failure on Shut Down relays (Phase stable >30 mins). Module locked.",
    "92": "UFSBI Address bad - Jumper configuration setting error on the motherboard backplane."
}

for i in range(1, 9):
    DELTRON_CODES[f"5{i-1 if i>1 else 0}"] = f"IN{i} JITTER / CHATTERING - Unstable relay contact. Low coil voltage or mechanical loose fit."

col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("📥 Upload Station A Excel Log", type=["xls", "xlsx"])
with col2:
    file_b = st.file_uploader("📥 Upload Station B Excel Log", type=["xls", "xlsx"])

def parse_logger_file(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.title()
        
        t_col = "Signal Time" if "Signal Time" in df.columns else ("Time" if "Time" in df.columns else None)
        n_col = "Signal Name" if "Signal Name" in df.columns else ("Event" if "Event" in df.columns else None)
        s_col = "Signal Status" if "Signal Status" in df.columns else ("Status" if "Status" in df.columns else None)
        
        if not (t_col and n_col and s_col):
            st.error(f"Formatting structure unreadable in {uploaded_file.name}. Ensure Time, Event/Name, Status headers exist.")
            return None
            
        df = df.dropna(subset=[t_col, n_col, s_col])
        df[n_col] = df[n_col].astype(str).str.strip()
        df[s_col] = df[s_col].astype(str).str.strip().str.upper()
        df[t_col] = pd.to_datetime(df[t_col], errors='coerce')
        df = df.sort_values(by=t_col).reset_index(drop=True)
        return {"df": df, "t": t_col, "n": n_col, "s": s_col}
    except Exception as e:
        st.error(f"Parsing failure on {uploaded_file.name}: {e}")
        return None

parsed_a = parse_logger_file(file_a)
parsed_b = parse_logger_file(file_b)

if file_a and file_b and parsed_a and parsed_b:
    df_a, t_a, n_a, s_a = parsed_a["df"], parsed_a["t"], parsed_a["n"], parsed_a["s"]
    df_b, t_b, n_b, s_b = parsed_b["df"], parsed_b["t"], parsed_b["n"], parsed_b["s"]
    
    # DYNAMIC CONFIGURATION DETECTION
    combined_names = " ".join(df_a[n_a].tolist()) + " " + " ".join(df_b[n_b].tolist())
    is_single = any(r in combined_names for r in ["TCFSR", "TGTSR", "BCSR", "LCSR"])
    mode_label = "SINGLE LINE (IRS PUSH BUTTON)" if is_single else "DOUBLE LINE (RE AREA BLOCK)"
    
    st.sidebar.info(f"⚙️ Target Configuration:\n**{mode_label}**")
    
    # --------------------------------------------------------
    # STEP 1: PRE-REQUISITES & INITIAL HEALTH GATEWAY
    # --------------------------------------------------------
    health_breached = False
    critical_alerts = []
    
    # Check for sudden hardware shutdowns anywhere in the log
    bipr_drop_a = df_a[df_a[n_a].str.contains("BIPR1|BIPR2", case=False, na=False) & (df_a[s_a] == "DOWN")]
    bipr_drop_b = df_b[df_b[n_b].str.contains("BIPR1|BIPR2", case=False, na=False) & (df_b[s_b] == "DOWN")]
    
    if not bipr_drop_a.empty or not bipr_drop_b.empty:
        health_breached = True
        fault_loc = "Station A" if not bipr_drop_a.empty else "Station B"
        timestamp_str = str(bipr_drop_a[t_a].iloc[0]) if not bipr_drop_a.empty else str(bipr_drop_b[t_b].iloc[0])
        
        st.error(f"🚨 **CRITICAL HARDWARE FAULT DETECTED AT {fault_loc.upper()}**")
        st.markdown(f"""
        ### **Root Cause Diagnostic Verdict:**
        * **Event Summary:** Sudden **BIPR Vital Health Relay Drop** registered at **{timestamp_str}** on {fault_loc}.
        * **Engineering Impact:** This is an intentional Deltron UFSBI failsafe system shutdown. Any subsequent relay chattering or volatile oscillations on lines like FR1/FR2 or TGTZR are a direct byproduct of this shutdown, **NOT an LCB path disconnection**.
        * **Field Directives:** Go to the Deltron cabinet at {fault_loc}. Inspect the internal DC-DC converter output parameters (Ensure 24V DC is stable between 21.6V and 28.8V). Look for an active hardware code trip on the CPU panel display.
        """)
    
    # Scan for explicit Deltron 2-digit hex system codes
    for code, desc in DELTRON_CODES.items():
        if not df_a[df_a[n_a].str.contains(code, case=False, na=False)].empty:
            critical_alerts.append(f"⚠️ **Station A Internal Diagnostic Card Alert:** Code [{code}] -> {desc}")
        if not df_b[df_b[n_b].str.contains(code, case=False, na=False)].empty:
            critical_alerts.append(f"⚠️ **Station B Internal Diagnostic Card Alert:** Code [{code}] -> {desc}")

    if critical_alerts:
        st.subheader("📋 Hardware Interlocking Diagnostic Traces")
        for alert in critical_alerts:
            st.warning(alert)

    # --------------------------------------------------------
    # STEP 2: SEQUENTIAL STATE MACHINE EVALUATION
    # --------------------------------------------------------
    if not health_breached:
        sequence_broken = False
        st.subheader("🔄 Inter-Station Sequential Operation Handshake Analysis")
        
        if is_single:
            # Step 2.1: Station A initiates bell code and demand
            sent_demand = df_a[df_a[n_a].str.contains("TCFSR", case=False, na=False) & (df_a[s_a] == "UP")]
            
            if not sent_demand.empty:
                t_init = sent_demand[t_a].iloc[0]
                st.write(f"1. 🟩 **Step 1 Passed:** Station A initiated Line Clear Demand [TCFSR UP] at `{t_init}`.")
                
                # Step 2.2: Verify reception at Station B within a 2-second telemetry window
                t_window_max = t_init + timedelta(seconds=2)
                recv_demand = df_b[df_b[n_b].str.contains("TCFRR", case=False, na=False) & 
                                   (df_b[s_b] == "UP") & 
                                   (df_b[t_b] >= t_init) & (df_b[t_b] <= t_window_max)]
                
                if not recv_demand.empty:
                    t_recv = recv_demand[t_b].iloc[0]
                    st.write(f"2. 🟩 **Step 2 Passed:** Station B correctly decoded transmission payload [TCFRR UP] at `{t_recv}`.")
                    
                    # Step 2.3: Station B grants Line Clear answer-back response
                    grant_back = df_b[df_b[n_b].str.contains("TGTSR", case=False, na=False) & 
                                      (df_b[s_b] == "UP") & (df_b[t_b] >= t_recv)]
                    
                    if not grant_back.empty:
                        t_grant = grant_back[t_b].iloc[0]
                        st.write(f"3. 🟩 **Step 3 Passed:** Station B generated Line Clear Answer-Back code [TGTSR UP] at `{t_grant}`.")
                        
                        # Step 2.4: Station A registers response confirmation
                        recv_confirm = df_a[df_a[n_a].str.contains("TGTRR", case=False, na=False) & 
                                            (df_a[s_a] == "UP") & (df_a[t_a] >= t_grant)]
                        
                        if not recv_confirm.empty:
                            st.balloons()
                            st.success("✅ **SEQUENTIAL VALIDATION SUCCESSFUL:** Perfect operational handshake verified. End-to-end signaling cycle integrity intact.")
                        else:
                            st.error("🚨 **SEQUENCE BREACH DETECTED AT STEP 4: Return Path Isolation**")
                            st.markdown(f"* **Analysis:** Station B granted line clear correctly, but Station A never registered confirmation relay **TGTRR UP**. Check local media card processing loops on Station A or verify if an explicit RSSB Code 34 locked the remote transceiver.")
                            sequence_broken = True
                    else:
                        st.error("🚨 **SEQUENCE BREACH DETECTED AT STEP 3: Local Interlocking Lockout on Station B**")
                        st.markdown(f"* **Analysis:** Station B received the block demand but failed to trigger response relay **TGTSR UP**. Verify if Station B SM Key was out or if local lever alignment parameters (`SNR` dropped) cancelled co-operation.")
                        sequence_broken = True
                else:
                    st.error("🚨 **SEQUENCE BREACH DETECTED AT STEP 2: Forward Path Media Interruption**")
                    st.markdown(f"* **Analysis:** Station A sent block request command, but Station B never received **TCFRR UP** within the safe 2000ms window. Check for real-time quad cable core grounding, line transformer attenuation or voice modem decoupling.")
                    sequence_broken = True
            else:
                st.warning("💡 No active line clear sequential movement (TCFSR initiation trace) captured in this specific file log dataset.")
        
        else:
            # DOUBLE LINE SEQUENTIAL RUNTIME LOGIC
            lcr_init = df_a[df_a[n_a].str.contains("LCR", case=False, na=False) & (df_a[s_a] == "UP")]
            if not lcr_init.empty:
                t_lcr = lcr_init[t_a].iloc[0]
                st.write(f"1. 🟩 **Step 1 Passed:** Double Line Clear Request [LCR UP] initiated at Station A at `{t_lcr}`.")
                
                lcr_recv = df_b[df_b[n_b].str.contains("LCRR", case=False, na=False) & (df_b[s_b] == "UP") & (df_b[t_b] >= t_lcr)]
                if not lcr_recv.empty:
                    st.balloons()
                    st.success("✅ **DOUBLE LINE SYSTEM OK:** Clear operational telemetry transmission link path established between locations.")
                else:
                    st.error("🚨 **SEQUENCE BREACH DETECTED: Double Line Link Discontinuity**")
                    st.markdown("* **Analysis:** Station A initiated double-line block transmission sequence, but the receiving validation unit **LCRR** failed to lock on Station B side. Inspect for transmission quad deterioration or sudden power drop spikes inside the filter cabinet.")
                    sequence_broken = True

    # SIDE BY SIDE CHRONOLOGICAL VERIFICATION PANELS
    st.markdown("---")
    st.subheader("📋 Chronological Critical Event Panels (Side-by-Side Validation)")
    t_panel1, t_panel2 = st.columns(2)
    with t_panel1:
        st.write("**Station A Chronological Tail:**")
        st.dataframe(df_a.tail(12)[[t_a, n_a, s_a]])
    with t_panel2:
        st.write("**Station B Chronological Tail:**")
        st.dataframe(df_b.tail(12)[[t_b, n_b, s_b]])
else:
    st.info("💡 Advanced Sequential Analysis active. Please upload separate Excel logging reports for both Station A and Station B to execute the state-machine breach locator.")
