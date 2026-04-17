import os
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- 1. SETUP & SECURITY ---
st.set_page_config(page_title="Analytics Dashboard", layout="wide")

if 'admin_unlocked' not in st.session_state or not st.session_state.admin_unlocked:
    st.warning("🔒 Access Denied. Please enter your Admin PIN on the Main Dashboard first.")
    st.stop()

st.title("📈 Factory Analytics Dashboard")
st.markdown("Real-time production metrics for Shree Nakoda Textiles")
st.divider()

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- NEW: TELLS THE CALCULATOR TO ADD MULTIPLES ---
def extract_meters(fab_str):
    if not fab_str or str(fab_str) == "None" or str(fab_str).strip() == "": return 0.0
    total = 0.0
    for p in str(fab_str).split("+"):
        try: total += float(p.lower().split("mtr")[0].strip())
        except: pass
    return total

# --- 2. FETCH & PROCESS DATA ---
try:
    res = supabase.table("orders").select("*").execute()
    if not res.data:
        st.info("Not enough data to generate analytics yet.")
        st.stop()
        
    df = pd.DataFrame(res.data)
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df = df.dropna(subset=['order_date']) 
    
    def check_status(row):
        chal = str(row.get('delivery_challan', ''))
        if chal and chal.lower() != 'none' and chal.strip() != "": return 'Delivered'
        return 'Pending'
    
    df['Status'] = df.apply(check_status, axis=1)
    df['quantity_total'] = pd.to_numeric(df['quantity_total'], errors='coerce').fillna(0)

    # --- 3. BUILD CHARTS & AUDITS ---
    total_fabric_calc = 0
    for col in ['fabric_36_inch', 'fabric_44_inch', 'fabric_58_inch']:
        total_fabric_calc += df[col].apply(extract_meters).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Pieces Ordered", f"{int(df['quantity_total'].sum()):,}")
    c2.metric("Total Pieces Pending", f"{int(df[df['Status'] == 'Pending']['quantity_total'].sum()):,}")
    c3.metric("Total Fabric Consumed", f"{int(total_fabric_calc):,} mtr")
    
    st.divider()

    # Smart Data Audit Table (Updated to check split strings)
    missing_meters_data = []
    for index, row in df.iterrows():
        for col_name, width_label in [('fabric_36_inch', '36"'), ('fabric_44_inch', '44"'), ('fabric_58_inch', '58"')]:
            val = str(row.get(col_name, "")).strip()
            if val and val.lower() not in ["none", "nan"]:
                for part in val.split("+"):
                    part = part.strip()
                    if part and "mtr" not in part.lower():
                        missing_meters_data.append({"Order ID": row['order_id'], "Fabric Field": width_label, "What was typed": part})
                
    if missing_meters_data:
        st.warning(f"⚠️ **Action Required:** {len(missing_meters_data)} entries are missing 'mtr' and currently show as '1' on the chart for tracking.")
        with st.expander("👀 View Order IDs needing audit"):
            st.dataframe(pd.DataFrame(missing_meters_data), hide_index=True, use_container_width=True)
        st.divider()

    col_chart1, col_chart2 = st.columns(2)
    
    # --- DELETED THE col_chart1, col_chart2 SPLIT ---
    
    # 1. FULL WIDTH FABRIC CHART
    st.subheader("🧵 Fabric Consumption by Type & Variant")
    
    fabric_data_list = []
    columns_to_check = [('fabric_36_inch', '36"'), ('fabric_44_inch', '44"'), ('fabric_58_inch', '58"')]
    
    for index, row in df.iterrows():
        order_id = str(row.get('order_id', 'Unknown'))
        for col_name, width_label in columns_to_check:
            entry = row.get(col_name)
            if pd.isna(entry): continue
            entry_str = str(entry).strip()
            if not entry_str or entry_str.lower() in ["none", "nan"]: continue
                
            for part in entry_str.split("+"):
                part = part.strip()
                if not part: continue
                
                try:
                    actual_meters = 0.0
                    if "mtr" in part.lower():
                        m_split = part.lower().split("mtr")
                        actual_meters = float(m_split[0].strip())
                        base_text = part[part.lower().find("mtr") + 3:].strip().title() 
                    else:
                        actual_meters = 0.0 
                        base_text = part.title()
                        
                    base_material = base_text.split(" ")[0].capitalize()
                    
                    chart_height = actual_meters if actual_meters > 0 else 1.0
                    audit_status = "✅ OK" if actual_meters > 0 else "⚠️ MISSING MTRS"
                    
                    if base_material:
                        fabric_data_list.append({
                            "Order ID": order_id,
                            "Base Material": base_material,
                            "Specific Variant": f"{base_text} {width_label}",
                            "Actual Meters": actual_meters,
                            "Chart Height": chart_height,
                            "Audit Status": audit_status
                        })
                except: continue
    
    if fabric_data_list:
        fab_df = pd.DataFrame(fabric_data_list)
        fab_df = fab_df.sort_values(by=['Base Material', 'Actual Meters'], ascending=[True, False])
        
        fig_fab = px.bar(
            fab_df,
            x='Base Material',
            y='Chart Height',
            color='Specific Variant', 
            hover_data={
                'Chart Height': False,   
                'Actual Meters': True,    
                'Order ID': True, 
                'Audit Status': True
            },
            text='Actual Meters'
        )
        
        fig_fab.update_xaxes(categoryorder='total descending') 
        
        fig_fab.update_layout(
            height=550, # Slightly reduced height since it's full width now
            bargap=0.15, 
            legend_title_text='Variants', 
            yaxis_title="Total Meters",
            xaxis_title="Fabric Base Material",
            font=dict(size=14)
        )
        fig_fab.update_traces(textposition='inside', textangle=0, textfont_size=12)
        
        # Taking up the full width of the screen!
        st.plotly_chart(fig_fab, use_container_width=True)
    else:
        st.info("No fabric data found.")

    st.divider()

    # 2. NEXT ROW: PIE CHART & TREND CHART SIDE-BY-SIDE
    col_pie, col_trend = st.columns([1, 1.5]) # Trend chart gets slightly more space
    
    with col_pie:
        st.subheader("📦 Pending vs. Delivered")
        status_counts = df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_status = px.pie(status_counts, values='Count', names='Status', hole=0.4,
                            color_discrete_map={'Delivered': '#28a745', 'Pending': '#ffc107'})
        fig_status.update_traces(textposition='inside', textinfo='value+label')
        st.plotly_chart(fig_status, use_container_width=True)

    with col_trend:
        st.subheader("📈 Production Volume Trend")
        trend_data = df.groupby('order_date')['quantity_total'].sum().reset_index().sort_values('order_date')
        fig_trend = px.area(trend_data, x='order_date', y='quantity_total', color_discrete_sequence=['#4c78a8'])
        st.plotly_chart(fig_trend, use_container_width=True)

except Exception as e:
    st.error(f"Error generating analytics: {e}")
    

    with col_chart2:
        st.subheader("📦 Pending vs. Delivered")
        status_counts = df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_status = px.pie(status_counts, values='Count', names='Status', hole=0.4,
                            color_discrete_map={'Delivered': '#28a745', 'Pending': '#ffc107'})
        fig_status.update_traces(textposition='inside', textinfo='value+label')
        st.plotly_chart(fig_status, use_container_width=True)

    st.divider()
    st.subheader("📈 Production Volume Trend (Pieces Ordered)")
    trend_data = df.groupby('order_date')['quantity_total'].sum().reset_index().sort_values('order_date')
    fig_trend = px.area(trend_data, x='order_date', y='quantity_total', color_discrete_sequence=['#4c78a8'])
    st.plotly_chart(fig_trend, use_container_width=True)

except Exception as e:
    st.error(f"Error generating analytics: {e}")


# ==========================================
# ANALYSIS: NUMBER OF DESIGNS BY PARTY
# ==========================================
st.divider()
st.subheader("📊 Catalog Overview & Party Analysis")
st.caption("Track your total catalog size and see which parties register the most designs.")

try:
    # 1. Fetch all designs and their associated parties from the catalog
    res_catalog = supabase.table("kurti_catalog").select("design_id, party_name").execute()
    
    if res_catalog.data:
        df_catalog = pd.DataFrame(res_catalog.data)
        
        # --- NEW: GRAND TOTAL METRIC CARD ---
        # This counts the absolute number of unique designs in your entire database
        total_designs = df_catalog['design_id'].nunique()
        
        # We put it in a column so the number doesn't stretch across the whole screen
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="Total Designs in Catalog", value=total_designs)
            
        st.write("") # Adds a little bit of breathing room before the chart
        # ------------------------------------
        
        # 2. Clean up the party names (so "vaanisa" and "Vaanisa" group together correctly)
        df_catalog['party_name'] = df_catalog['party_name'].astype(str).str.strip().str.title()
        
        # 3. Count how many unique designs belong to each party
        party_counts = df_catalog.groupby('party_name')['design_id'].nunique().reset_index()
        party_counts.columns = ['Party Name', 'Total Designs']
        
        # Sort them from highest to lowest
        party_counts = party_counts.sort_values(by='Total Designs', ascending=False)
        
        col_chart, col_data = st.columns([2, 1])
        
        with col_chart:
            # 4. Draw a beautiful interactive bar chart
            st.bar_chart(data=party_counts, x='Party Name', y='Total Designs', color="#FF4B4B")
            
        with col_data:
            # 5. Show a neat summary table next to it
            st.dataframe(
                party_counts, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Party Name": st.column_config.TextColumn("Party"),
                    "Total Designs": st.column_config.NumberColumn("Designs")
                }
            )
    else:
        st.info("Not enough data in the catalog to generate this chart.")
        
except Exception as e:
    st.error(f"Could not load party design analysis: {e}")
st.divider() 