import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 1. SETUP & STATE MEMORY ---
st.set_page_config(page_title="Shree Nakoda Dashboard", layout="wide")

# Initialize Security State early so the sidebar can use it
if 'admin_unlocked' not in st.session_state:
    st.session_state.admin_unlocked = False

# Branding Setup
if os.path.exists("logo.jpeg"): st.sidebar.image("logo.jpeg", use_container_width=True)
elif os.path.exists("logo.jpg"): st.sidebar.image("logo.jpg", use_container_width=True)

st.sidebar.title("🏢 Shree Nakoda Textiles")
st.sidebar.caption("Enterprise Portal")

# --- NEW: LOGOUT / LOCK BUTTON ---
if st.session_state.admin_unlocked:
    if st.sidebar.button("🔒 Lock Dashboard", type="primary", use_container_width=True):
        st.session_state.admin_unlocked = False
        st.rerun()

st.sidebar.divider()

col_logo, col_title = st.columns([1, 11]) 
with col_logo:
    if os.path.exists("snt_logo.jpeg"): st.image("snt_logo.jpeg", width=70)
    elif os.path.exists("logo.jpeg"): st.image("logo.jpeg", width=70)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", width=70)
    else: st.markdown("<h1 style='text-align: center; margin-top: 0px;'>🏢</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown("<h1 style='margin-top: -15px;'>Active Order Dashboard</h1>", unsafe_allow_html=True)

# Supabase Connection
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ==========================================
# SYSTEM MAINTENANCE (AUTO-CLEANUP)
# ==========================================
try:
    # Tell Supabase to delete any row where delivery_date is older than 250 days
    cutoff_date = (datetime.now() - timedelta(days=250)).date()
    supabase.table("orders").delete().lt("delivery_date", str(cutoff_date)).execute()
except Exception as e:
    pass 

# ==========================================
# 🔒 SECURITY GATEWAY (LOCK SCREEN)
# ==========================================
if 'admin_unlocked' not in st.session_state:
    st.session_state.admin_unlocked = False

# If not unlocked, show the PIN screen and STOP the rest of the code from running
if not st.session_state.admin_unlocked:
    st.markdown("### 🔒 Restricted Access")
    st.info("This dashboard contains sensitive client data. Designers: Please use the sidebar to access the Kurti Identifier.")
    
    col_pin, col_empty = st.columns([1, 2])
    with col_pin:
        pin_input = st.text_input("Enter Admin PIN to unlock:", type="password")
        if st.button("Unlock Dashboard"):
            # Check if what they typed matches your secrets.toml file
            if pin_input == st.secrets["ADMIN_PIN"]:
                st.session_state.admin_unlocked = True
                st.rerun()
            else:
                st.error("❌ Incorrect PIN.")
    
    # st.stop() is the magic trick. It completely halts the app here. 
    # None of your database data below this line will even load!
    st.stop()

def calculate_quantity(input_str):
    try: return int(eval(str(input_str)))
    except: return 0

def parse_fabric_string(fab_str):
    if not fab_str or str(fab_str) == "None" or str(fab_str).strip() == "": return "None", ""
    parts = str(fab_str).split("mtr ")
    if len(parts) == 2: return parts[1].strip(), parts[0].strip() 
    return str(fab_str).strip(), "" 

if 'form_key' not in st.session_state: st.session_state.form_key = 0
if 'table_key' not in st.session_state: st.session_state.table_key = 0
if 'fabric_list' not in st.session_state:
    st.session_state.fabric_list = ["None", "Linen", "Cambric", "Mal", "Cotton", "Rayon", "Georgette", "➕ Add New..."]

# ==========================================
# SECTION 1: THE DASHBOARD 
# ==========================================
try:
    res = supabase.table("orders").select("*, kurti_catalog(image_url)").order("order_date", desc=True).execute()
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
        df['Fab Challan'] = df.get('fab_challan', None)
        df['Delivery Challan'] = df.get('delivery_challan', None)
        df['Hidden Delivery Date'] = pd.to_datetime(df.get('delivery_date'), errors='coerce')
        
        # --- NEW: SEARCH & FILTERS ---
        col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
        with col_f1: show_history = st.checkbox("🕰️ Show Past/Delivered Orders (Archive View)")
        with col_f2: search_order_id = st.text_input("🔍 Search by Order ID", placeholder="e.g. 1100")
        with col_f3: search_del_challan = st.text_input("🔍 Search by Delivery Challan", placeholder="e.g. 152")
        
        if show_history:
            filtered_df = df.copy()
        else:
            three_days_ago = pd.to_datetime(datetime.now().date() - timedelta(days=3))
            cond_no_challan = df['Delivery Challan'].isna() | (df['Delivery Challan'] == "") | (df['Delivery Challan'].str.lower() == "none")
            cond_recently_delivered = df['Hidden Delivery Date'] >= three_days_ago
            filtered_df = df[cond_no_challan | cond_recently_delivered].copy()

        # Apply Search Filters safely
        if search_order_id:
            # Use == for an EXACT match instead of .contains
            filtered_df = filtered_df[filtered_df['order_id'].fillna("").astype(str).str.strip() == str(search_order_id).strip()]
            
        if search_del_challan:
            # Use == for an EXACT match here too, so searching Challan '5' doesn't bring up '152'
            filtered_df = filtered_df[filtered_df['Delivery Challan'].fillna("").astype(str).str.strip() == str(search_del_challan).strip()]

        filtered_df['Order ID'] = filtered_df['order_id']
        filtered_df['Party'] = filtered_df['party_name']
        filtered_df['Order Date'] = pd.to_datetime(filtered_df['order_date'], errors='coerce').dt.date
        filtered_df['Quantity'] = filtered_df['quantity_formula']
        filtered_df['36" Fabric'] = filtered_df['fabric_36_inch']
        filtered_df['44" Fabric'] = filtered_df['fabric_44_inch']
        filtered_df['58" Fabric'] = filtered_df['fabric_58_inch']
        filtered_df['Remarks'] = filtered_df['remarks']

        display_df = filtered_df[['Order Date', 'Order ID', 'Party', 'Quantity', 'Image', '36" Fabric', '44" Fabric', '58" Fabric', 'Fab Challan', 'Delivery Challan', 'Remarks']].copy()
        display_df.insert(0, 'Delete', False)
        display_df.insert(0, 'Edit', False)
        
        st.info("💡 Check the **✏️ Edit** box to load an order into the form below. Check **🗑️ Delete** to permanently remove it.")
        
        editor_key = f"table_{'history' if show_history else 'active'}_{st.session_state.table_key}"
        disabled_cols = display_df.columns.drop(['Edit', 'Delete']).tolist()
        
        edited_df = st.data_editor(
            display_df,
            column_config={
                "Edit": st.column_config.CheckboxColumn("✏️ Edit", width="small", default=False),
                "Delete": st.column_config.CheckboxColumn("🗑️ Delete", width="small", default=False),
                "Order Date": st.column_config.DateColumn("Date", width="small", format="DD/MM/YYYY"),
                "Order ID": st.column_config.TextColumn("ID", width="small"),
                "Party": st.column_config.TextColumn("Party", width="medium"),
                "Quantity": st.column_config.TextColumn("Qty", width="small"),
                "Image": st.column_config.ImageColumn("Img", width="small"),
                "36\" Fabric": st.column_config.TextColumn("36\"", width="small"),
                "44\" Fabric": st.column_config.TextColumn("44\"", width="small"),
                "58\" Fabric": st.column_config.TextColumn("58\"", width="small"),
                "Fab Challan": st.column_config.TextColumn("Fab Challan", width="small"),
                "Delivery Challan": st.column_config.TextColumn("Del Challan", width="small"),
                "Remarks": st.column_config.TextColumn("Remarks", width="medium")
            },
            disabled=disabled_cols, 
            use_container_width=True,
            hide_index=True,
            key=editor_key
        )
        
        if st.button("🗑️ Process Deletions"):
            deletions_made = False
            for index, row in edited_df.iterrows():
                if row['Delete'] == True:
                    supabase.table("orders").delete().eq("order_id", row['Order ID']).execute()
                    deletions_made = True
            if deletions_made:
                st.session_state.table_key += 1
                st.success("Orders deleted successfully.")
                st.rerun()

        selected_order_id = None
        for index, row in edited_df.iterrows():
            if row['Edit'] == True:
                selected_order_id = row['Order ID']
                break 

    else:
        st.info("No active orders in the database.")
        selected_order_id = None

except Exception as e:
    st.error(f"Could not load dashboard data: {e}")
    selected_order_id = None

st.divider()

# ==========================================
# SECTION 2: SMART DATA ENTRY & EDITING FORM
# ==========================================
is_editing = selected_order_id is not None

f_oid = selected_order_id if is_editing else ""
f_party = ""
f_odate = datetime.now()
f_qty = ""
f_fchal = ""
f_dchal = ""
f_rem = ""
f_sel_design = None
existing_del_date = None

f36_choice, f36_met = "None", ""
f44_choice, f44_met = "None", ""
f58_choice, f58_met = "None", ""

if is_editing:
    raw_order = next((o for o in orders_data if str(o['order_id']) == str(selected_order_id)), None)
    if raw_order:
        f_party = raw_order.get('party_name', "")
        f_odate = pd.to_datetime(raw_order.get('order_date')).date() if raw_order.get('order_date') else datetime.now()
        f_qty = raw_order.get('quantity_formula', "")
        f_fchal = raw_order.get('fab_challan', "")
        f_dchal = raw_order.get('delivery_challan', "")
        f_rem = raw_order.get('remarks', "")
        f_sel_design = raw_order.get('design_id', None)
        existing_del_date = raw_order.get('delivery_date', None)
        
        f36_choice, f36_met = parse_fabric_string(raw_order.get('fabric_36_inch'))
        f44_choice, f44_met = parse_fabric_string(raw_order.get('fabric_44_inch'))
        f58_choice, f58_met = parse_fabric_string(raw_order.get('fabric_58_inch'))

fk_id = f"{st.session_state.form_key}_{f_oid}"

expander_title = f"✏️ EDITING ORDER: {selected_order_id}" if is_editing else "➕ Click Here to Create a New Order"
with st.expander(expander_title, expanded=is_editing):
    
    col_date, col_id, col_party = st.columns(3)
    with col_date: order_date = st.date_input("Order Date", value=f_odate, format="DD/MM/YYYY", key=f"odate_{fk_id}")
    with col_id: order_id = st.text_input("Order ID *", value=f_oid, disabled=is_editing, key=f"oid_{fk_id}")
    with col_party: party = st.text_input("Party Name *", value=f_party, key=f"party_{fk_id}")

    col_qty = st.columns(1)[0]
    with col_qty:
        q_input = st.text_input("Quantity (e.g., 180 or 25*4)", value=f_qty, key=f"qty_{fk_id}")
        total_pieces = calculate_quantity(q_input)
        if total_pieces > 0: st.caption(f"Total Calculated Pieces: **{total_pieces}**")

    st.divider()
    st.write("**Fabric Details (Type & Meters)**")

    def get_fabric_string(label, key_suffix, default_choice, default_meters):
        col_a, col_b = st.columns([1, 2])
        new_fabric_name = None
        
        safe_choice = default_choice if default_choice in st.session_state.fabric_list else "None"
        if default_choice and default_choice != "None" and default_choice not in st.session_state.fabric_list:
            st.session_state.fabric_list.insert(-1, default_choice)
            safe_choice = default_choice

        with col_a:
            choice = st.selectbox(f"{label} Fabric", st.session_state.fabric_list, index=st.session_state.fabric_list.index(safe_choice), key=f"sel_{key_suffix}_{fk_id}")
            if choice == "➕ Add New...":
                new_fabric_name = st.text_input(f"New {label} Name", key=f"new_{key_suffix}_{fk_id}")
                choice = new_fabric_name 
        with col_b: 
            meters = st.text_input(f"{label} Meters", value=default_meters, key=f"met_{key_suffix}_{fk_id}")
        
        if choice and choice != "None":
            formatted_string = f"{meters}mtr {choice}" if meters else f"{choice}"
        else:
            formatted_string = None
            
        return formatted_string, new_fabric_name

    fab_36, new_36 = get_fabric_string("36\"", "36", f36_choice, f36_met)
    fab_44, new_44 = get_fabric_string("44\"", "44", f44_choice, f44_met)
    fab_58, new_58 = get_fabric_string("58\"", "58", f58_choice, f58_met)

    st.divider()
    
    c1, c2, c3 = st.columns(3)
    with c1: fab_challan_input = st.text_input("🏭 Fabric Challan No.", value=f_fchal, key=f"fchallan_{fk_id}")
    with c2: del_challan_input = st.text_input("🚚 Delivery Challan No.", value=f_dchal, help="Order stays visible for 3 days after entry.", key=f"dchallan_{fk_id}")
    with c3: remarks_input = st.text_input("📝 Remarks", value=f_rem, key=f"rem_{fk_id}")
    
    st.divider()
    st.write("**Kurti Design Selection**")
    
    search_term = st.text_input("🔍 Search Design ID", placeholder="Type ID to filter images...", key=f"search_{fk_id}")
    
    response = supabase.table("kurti_catalog").select("design_id, image_url").execute()
    existing_designs = response.data
    selected_design_id = st.session_state.get('selected_design', f_sel_design)

    if existing_designs:
        if search_term: existing_designs = [d for d in existing_designs if search_term.lower() in str(d['design_id']).lower()]
            
        if not existing_designs: st.warning("No designs found matching that search.")
        else:
            cols = st.columns(4)
            for index, design in enumerate(existing_designs):
                with cols[index % 4]:
                    try:
                        if design['image_url'] and "http" in str(design['image_url']): st.image(design['image_url'], width=100)
                        else: st.info("No Image Link")
                    except Exception: st.warning("Image Error")
                    
                    if st.button(f"Select {design['design_id']}", key=f"btn_{design['design_id']}_{fk_id}"):
                        st.session_state['selected_design'] = design['design_id']
                        selected_design_id = design['design_id'] 
                        
            if selected_design_id: st.success(f"Selected Design: {selected_design_id}")
    else:
        st.info("No designs found in the database.")

    # --- SAVE OR UPDATE LOGIC ---
    btn_text = f"💾 UPDATE Order {f_oid}" if is_editing else "💾 SAVE New Order"
    
    if st.button(btn_text, key=f"save_{fk_id}"):
        if not order_id or not party:
            st.error("Order ID and Party Name are required!")
        else:
            try:
                # --- FIXED: Safely check for None values to prevent the 'strip' error ---
                save_del_date = None
                if del_challan_input and str(del_challan_input).strip() != "":
                    save_del_date = existing_del_date if existing_del_date else str(datetime.now().date())
                
                order_data = {
                    "party_name": party,
                    "order_date": str(order_date),
                    "quantity_formula": q_input,
                    "quantity_total": total_pieces,
                    "design_id": selected_design_id,
                    "fabric_36_inch": fab_36,
                    "fabric_44_inch": fab_44,
                    "fabric_58_inch": fab_58,
                    "fab_challan": fab_challan_input,
                    "delivery_challan": del_challan_input,
                    "delivery_date": save_del_date, 
                    "remarks": remarks_input
                }
                
                if is_editing:
                    supabase.table("orders").update(order_data).eq("order_id", order_id).execute()
                    st.success(f"Order {order_id} UPDATED successfully!")
                else:
                    check_existing = supabase.table("orders").select("order_id").eq("order_id", order_id).execute()
                    if len(check_existing.data) > 0:
                        st.warning(f"⚠️ Order ID '{order_id}' already exists! Click it in the table above if you want to edit it.")
                        st.stop()
                    else:
                        order_data["order_id"] = order_id
                        supabase.table("orders").insert(order_data).execute()
                        st.success(f"Order {order_id} CREATED successfully!")
                    
                for new_fabric in [new_36, new_44, new_58]:
                    if new_fabric and new_fabric not in st.session_state.fabric_list:
                        st.session_state.fabric_list.insert(-1, new_fabric)
                
                st.session_state['selected_design'] = None  
                st.session_state.form_key += 1
                st.session_state.table_key += 1              
                st.rerun() 
                
            except Exception as e:
                st.error(f"Error: {e}")