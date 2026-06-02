import streamlit as st
import pandas as pd
from collections import Counter
from datetime import datetime

# ============================================================
# DELTRON UFSBI MOBILE DIAGNOSTIC ENGINE (WEB INTERFACE)
# PURPOSE : One-Tap Failure Analysis for Field Staff
# ============================================================

# Configure the web app to look like a clean mobile interface
st.set_page_config(page_title="UFSBI Fault Locator", page_icon="📡", layout="centered")

# Visual Header
st.title("📡 Deltron UFSBI Fault Locator")
st.markdown("### **S&T Department - Railway Signaling Diagnostic Tool**")
st.write("Upload a data logger Excel file below to instantly detect the root cause of a block instrument failure.")

st.markdown("---")

# 1. MOBILE-FRIENDLY FILE UPLOADER
uploaded_file = st.file_uploader("📥 Step 1: Tap to select/upload Data Logger Excel File (.xls or .xlsx)", type=["xls", "xlsx"])

if uploaded_file is not None:
    st.success("✅ File uploaded successfully! Analyzing data...")
    
    try:
        # Load file directly from the browser memory stream
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.title()
        
        # Standardized Column Mappings
        TIME_COLUMN = "Signal Time"       
        EVENT_COLUMN = "Signal Name"     
        STATUS_COLUMN = "Signal Status"   
        
        if TIME_COLUMN not in df.columns and "Time" in df.columns: TIME_COLUMN = "Time"
        if EVENT_COLUMN not in df.columns and "Event" in df.columns: EVENT_COLUMN = "Event"
        if STATUS_COLUMN not in df.columns and "Status" in df.columns: STATUS_COLUMN = "Status"
        
        # Clean blank data and trailing whitespace
        df = df.dropna(subset=[TIME_COLUMN, EVENT_COLUMN, STATUS_COLUMN], how='any')
        df[EVENT_COLUMN] = df[EVENT_COLUMN].astype(str).str.strip()
        df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip().str.upper()
        
        # High-precision millisecond chronological sorting
        df[TIME_COLUMN] = pd.to_datetime(df[TIME_COLUMN], format='%m/%d/%Y %H:%M:%S:%f', errors='coerce')
        df = df.sort_values(by=TIME_COLUMN).reset_index(drop=True)
        
        # Analyze relay state frequencies
        event_counts = df[EVENT_COLUMN].value_counts()
        CHATTER_LIMIT = 20
        chatter_list = [event for event, count in event_counts.items() if count > CHATTER_LIMIT]
        final_events = df.tail(15)
        
        # 2. AUTOMATED EXPERT CONCLUSION ENGINE
        st.subheader("🔍 Step 2: Automated Diagnostic Verdict")
        
        # Check for LCB path interruption or chattering links
        is_lcb_fault = len(chatter_list) > 0 or any("FR" in str(x) for x in final_events[EVENT_COLUMN])
        
        if is_lcb_fault:
            st.error("🚨 **LIKELY ROOT CAUSE: Line Clear Box (LCB) Path Interruption / Discontinuity**")
            
            st.markdown("""
            **📋 Recommended Field Actions for Maintainers:**
            1. 🛑 **Check Continuity:** Inspect for complete or intermittent connection breaks along the LCB circuit path.
            2. ⚡ **Measure Attenuation:** Check transmission line parameters on the media channel (Quad Cable / OFC).
            3. 👁️ **Inspect Cabinet:** Look at the faceplate Rx/Tx communication card LEDs on the Deltron UFSBI cabinet to see if they are flickering or dark.
            """)
        else:
            st.warning("⚠️ **VERDICT: No clear chattering signature found. Inspect final sequential relay drops below.**")
            
        st.markdown("---")
        
        # 3. CRITICAL CLOSURE TIMELINE DISPLAY
        st.subheader("📋 Step 3: Critical Events Right Before Lockout")
        st.write("This timeline shows exactly what the relays did down to the millisecond before the system froze:")
        
        timeline_records = []
        for idx, row in final_events.iterrows():
            time_str = row[TIME_COLUMN].strftime('%H:%M:%S:%f')[:-3] if pd.notnull(row[TIME_COLUMN]) else "N/A"
            timeline_records.append({
                "Row": idx + 2,
                "Time Stamp": time_str,
                "Relay / Signal Name": row[EVENT_COLUMN],
                "Current Position": row[STATUS_COLUMN]
            })
            
        st.table(pd.DataFrame(timeline_records))
        
        # 4. PORTABLE REPORT SHARING EXPORTER
        st.subheader("📲 Step 4: Share This Report")
        
        report_text = (
            f"DELTRON UFSBI FAILURE DIAGNOSTIC REPORT\n"
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Target Log File: {uploaded_file.name}\n"
            f"-----------------------------------------\n"
            f"VERDICT: {'LCB Communication Path Failure' if is_lcb_fault else 'Sequence Out of Phase Check'}\n"
            f"-----------------------------------------\n"
            f"Final Relay Action: {final_events.iloc[-1][EVENT_COLUMN]} went {final_events.iloc[-1][STATUS_COLUMN]}"
        )
        
        st.download_button(
            label="💾 Download Text File to Share on WhatsApp",
            data=report_text,
            file_name=f"UFSBI_Fault_Report_{datetime.now().strftime('%H%M%S')}.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"❌ Processing Error: Make sure this file matches your standard station data logger layout. Info: {e}")

else:
    st.info("💡 Waiting for data logger file... You can transfer a file to this smartphone via WhatsApp, Email, or USB-OTG and upload it here.")
