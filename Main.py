import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 1. SETUP & STATE MEMORY ---
st.set_page_config(page_title="Shree Nakoda Dashboard", layout="wide")

# ==========================================
# BRANDING & UI SETUP
# ==========================================
if os.path.exists("logo.jpeg"):
    st.sidebar.image("logo.jpeg", use_container_width=True)
elif os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)

st.sidebar.title("🏢 Shree Nakoda Textiles")
st.sidebar.caption("Enterprise Portal")
st.sidebar.divider()

col_logo, col_title = st.columns([1, 11]) 
with col_logo:
    if os.path.exists("logo.jpeg"):
        st.image("logo.jpeg", width=70)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=70)
    else:
        st.markdown("<h1 style='text-align: center; margin-top: 0px;'>🏢</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown("<h1 style='margin-top: -15px;'>Active Order Dashboard</h1>", unsafe_allow_html=True)

# Supabase Connection
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def calculate_quantity(input_str):
    try: return int(eval(input_str))
    except: return 0

# Memory Initialization
if 'form_key' not in st.session_state: st.session_state.form_key = 0
if 'fabric_list' not in st.session_state:
    st.session_state.fabric_list = ["None", "Linen", "Cambric", "Mal", "Cotton", "Rayon", "Georgette", "➕ Add New..."]

# ==========================================
# SECTION 1: THE DASHBOARD (TOP)
# ==========================================
try:
    res = supabase.table("orders").select("*, kurti_catalog(image_url)").execute()
    orders_data = res.data

    if orders_data:
        df = pd.DataFrame(orders_data)
        df['Image'] = df['kurti_catalog'].apply(lambda x: x.get('image_url') if isinstance(x, dict) else None)

        def format_fabric(row):
            parts = []
            if pd.notna(row.get('fabric_36_inch')) and row.get('fabric_36_inch'): parts.append(f"36\": {row['fabric_36_inch']}")
            if pd.notna(row.get('fabric_44_inch')) and row.get('fabric_44_inch'): parts.append(f"44\": {row['fabric_44_inch']}")
            if pd.notna(row.get('fabric_58_inch')) and row.get('fabric_58_inch'): parts.append(f"58\": {row['fabric_58_inch']}")
            return " | ".join(parts) if parts else "None"
            
        df['Fabric Details'] = df.apply(format_fabric, axis=1)
        df['Delivery Date'] = pd.to_datetime(df['delivery_date'])
        
        show_history = st.checkbox("🕰️ Show Past/Delivered Orders (Archive View)")
        
        if show_history:
            filtered_df = df.copy()
        else:
            ten_days_ago = pd.to_datetime(datetime.now().date() - timedelta(days=10))
            filtered_df = df[(df['Delivery Date'].isna()) | (df['Delivery Date'] >= ten_days_ago)].copy()

        filtered_df['Delivery Date'] = filtered_df['Delivery Date'].dt.date
        filtered_df['Order ID'] = filtered_df['order_id']
        filtered_df['Party'] = filtered_df['party_name']
        filtered_df['Order Date'] = pd.to_datetime(filtered_df['order_date'], errors='coerce').dt.date
        filtered_df['Quantity'] = filtered_df['quantity_formula']
        filtered_df['36" Fabric'] = filtered_df['fabric_36_inch']
        filtered_df['44" Fabric'] = filtered_df['fabric_44_inch']
        filtered_df['58" Fabric'] = filtered_df['fabric_58_inch']
        filtered_df['Fabric Date'] = pd.to_datetime(filtered_df['fabric_received_date'], errors='coerce').dt.date
        filtered_df['Remarks'] = filtered_df['remarks']

        display_df = filtered_df[['Order Date', 'Order ID', 'Party', 'Quantity', 'Image', '36" Fabric', '44" Fabric', '58" Fabric', 'Fabric Date', 'Delivery Date', 'Remarks']].copy()
        display_df.insert(0, 'Delete', False)
        
        st.info("💡 **Excel Mode:** Edit cells inline. Check **🗑️** to permanently remove an order.")
        
        editor_key = "history_editor" if show_history else "active_editor"
        
        edited_df = st.data_editor(
            display_df,
            column_config={
                "Delete": st.column_config.CheckboxColumn("🗑️", help="Permanently delete this order", width="small", default=False),
                "Order Date": st.column_config.DateColumn("Date", width="small", format="YYYY-MM-DD"),
                "Order ID": st.column_config.TextColumn("ID", width="small"),
                "Party": st.column_config.TextColumn("Party", width="medium"),
                "Quantity": st.column_config.TextColumn("Qty", width="small"),
                "Image": st.column_config.ImageColumn("Img", width="small"),
                "36\" Fabric": st.column_config.TextColumn("36\"", width="small"),
                "44\" Fabric": st.column_config.TextColumn("44\"", width="small"),
                "58\" Fabric": st.column_config.TextColumn("58\"", width="small"),
                "Fabric Date": st.column_config.DateColumn("Fab Rcv", width="small", format="YYYY-MM-DD"),
                "Delivery Date": st.column_config.DateColumn("Delivery", width="small", format="YYYY-MM-DD"),
                "Remarks": st.column_config.TextColumn("Remarks", width="medium")
            },
            disabled=["Order ID", "Image"], 
            use_container_width=True,
            hide_index=True,
            key=editor_key
        )
        
        if st.button("🔄 Save Dashboard Changes"):
            for index, row in edited_df.iterrows():
                if row['Delete'] == True:
                    supabase.table("orders").delete().eq("order_id", row['Order ID']).execute()
                    continue 
                
                o_date = str(row['Order Date']) if pd.notna(row['Order Date']) else None
                f_date = str(row['Fabric Date']) if pd.notna(row['Fabric Date']) else None
                d_date = str(row['Delivery Date']) if pd.notna(row['Delivery Date']) else None
                new_total = calculate_quantity(str(row['Quantity']))

                update_data = {
                    "order_date": o_date,
                    "party_name": str(row['Party']),
                    "quantity_formula": str(row['Quantity']),
                    "quantity_total": new_total,
                    "fabric_36_inch": str(row['36" Fabric']) if pd.notna(row['36" Fabric']) and str(row['36" Fabric']).strip() != "" else None,
                    "fabric_44_inch": str(row['44" Fabric']) if pd.notna(row['44" Fabric']) and str(row['44" Fabric']).strip() != "" else None,
                    "fabric_58_inch": str(row['58" Fabric']) if pd.notna(row['58" Fabric']) and str(row['58" Fabric']).strip() != "" else None,
                    "fabric_received_date": f_date,
                    "delivery_date": d_date,
                    "remarks": str(row['Remarks']) if pd.notna(row['Remarks']) else ""
                }
                supabase.table("orders").update(update_data).eq("order_id", row['Order ID']).execute()
                
            st.success("Dashboard updated! All edits and deletions saved to the database.")
            st.rerun() 
    else:
        st.info("No active orders in the database.")

except Exception as e:
    st.error(f"Could not load dashboard data: {e}")

st.divider()

# ==========================================
# SECTION 2: DATA ENTRY (BOTTOM)
# ==========================================
fk = st.session_state.form_key

with st.expander("➕ Click Here to Create a New Order", expanded=False):
    col_date, col_id, col_party = st.columns(3)
    with col_date: order_date = st.date_input("Order Date", value=datetime.now(), key=f"odate_{fk}")
    with col_id: order_id = st.text_input("Order ID", key=f"oid_{fk}")
    with col_party: party = st.text_input("Party Name", key=f"party_{fk}")

    col_qty = st.columns(1)[0]
    with col_qty:
        q_input = st.text_input("Quantity (e.g., 180 or 25*4)", key=f"qty_{fk}")
        total_pieces = calculate_quantity(q_input)
        if total_pieces > 0: st.caption(f"Total Calculated Pieces: **{total_pieces}**")

    st.divider()
    st.write("**Fabric Details (Type & Meters)**")

    def get_fabric_string(label, key_suffix):
        col_a, col_b = st.columns([1, 2])
        new_fabric_name = None
        with col_a:
            choice = st.selectbox(f"{label} Fabric", st.session_state.fabric_list, key=f"sel_{key_suffix}_{fk}")
            if choice == "➕ Add New...":
                new_fabric_name = st.text_input(f"New {label} Name", key=f"new_{key_suffix}_{fk}")
                choice = new_fabric_name 
        with col_b: meters = st.text_input(f"{label} Meters", key=f"met_{key_suffix}_{fk}")
        
        formatted_string = f"{meters}mtr {choice}" if meters and choice and choice != "None" else None
        return formatted_string, new_fabric_name

    fab_36, new_36 = get_fabric_string("36\"", "36")
    fab_44, new_44 = get_fabric_string("44\"", "44")
    fab_58, new_58 = get_fabric_string("58\"", "58")

    st.divider()
    c1, c2 = st.columns(2)
    with c1: fabric_received = st.checkbox("✅ Fabric Received in Factory", key=f"frecv_{fk}")
    with c2: fabric_received_date = st.date_input("Fabric Received Date", key=f"frecvdate_{fk}") if fabric_received else None

    st.divider()
    st.write("**Kurti Design Selection**")
    
    search_term = st.text_input("🔍 Search Design ID", placeholder="Type ID to filter images...", key=f"search_{fk}")
    
    response = supabase.table("kurti_catalog").select("design_id, image_url").execute()
    existing_designs = response.data
    selected_design_id = st.session_state.get('selected_design')

    if existing_designs:
        if search_term:
            existing_designs = [d for d in existing_designs if search_term.lower() in str(d['design_id']).lower()]
            
        if not existing_designs:
            st.warning("No designs found matching that search.")
        else:
            cols = st.columns(4)
            for index, design in enumerate(existing_designs):
                with cols[index % 4]:
                    try:
                        if design['image_url'] and "http" in str(design['image_url']): st.image(design['image_url'], width=100)
                        else: st.info("No Image Link")
                    except Exception: st.warning("Image Error")
                    
                    if st.button(f"Select {design['design_id']}", key=f"btn_{design['design_id']}_{fk}"):
                        st.session_state['selected_design'] = design['design_id']
                        selected_design_id = design['design_id'] 
                        
            if selected_design_id: st.success(f"Selected Design: {selected_design_id}")
    else:
        st.info("No designs found in the database.")

    # --- SAVE ORDER BUTTON ---
    if st.button("💾 Save Entire Order", key=f"save_{fk}"):
        if not order_id or not party:
            st.error("Order ID and Party Name are required!")
        else:
            try:
                check_existing = supabase.table("orders").select("order_id").eq("order_id", order_id).execute()
                
                if len(check_existing.data) > 0:
                    st.warning(f"⚠️ Order ID '{order_id}' already exists! If you are trying to edit or delete it, please use the Dashboard table above.")
                else:
                    order_data = {
                        "order_id": order_id,
                        "party_name": party,
                        "order_date": str(order_date),
                        "quantity_formula": q_input,
                        "quantity_total": total_pieces,
                        "design_id": selected_design_id,
                        "fabric_36_inch": fab_36,
                        "fabric_44_inch": fab_44,
                        "fabric_58_inch": fab_58,
                        "fabric_received": fabric_received,
                        "fabric_received_date": str(fabric_received_date) if fabric_received_date else None
                    }
                    supabase.table("orders").insert(order_data).execute()
                    
                    for new_fabric in [new_36, new_44, new_58]:
                        if new_fabric and new_fabric not in st.session_state.fabric_list:
                            st.session_state.fabric_list.insert(-1, new_fabric)
                    
                    st.session_state['selected_design'] = None  
                    st.session_state.form_key += 1              
                    
                    st.success(f"Order {order_id} saved successfully!")
                    st.rerun() 
            except Exception as e:
                st.error(f"Error: {e}")