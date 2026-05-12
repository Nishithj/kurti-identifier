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
    orders_data = [] 

    # 1. Fetch all orders normally
    res_orders = supabase.table("orders").select("*").order("order_date", desc=True).execute()
    orders_data = res_orders.data
    
    # 2. Fetch the catalog images separately
    res_catalog = supabase.table("kurti_catalog").select("design_id, image_url").execute()
    img_dict = {item['design_id']: item['image_url'] for item in res_catalog.data}
    
    # 3. DYNAMIC IMAGE SCANNER: Find the max number of designs attached to any single order
    max_images = 1 # Always guarantee at least an "Img 1" column
    for order in orders_data:
        d_ids = str(order.get('design_id', ''))
        order['image_urls_list'] = [] 
        
        if d_ids and d_ids.lower() not in ['none', 'nan', '']:
            for d_id in d_ids.split(','):
                clean_id = d_id.strip()
                if clean_id in img_dict and img_dict[clean_id]:
                    order['image_urls_list'].append(img_dict[clean_id])
                    
        # Update our max column count if this order has more images than previous ones
        if len(order['image_urls_list']) > max_images:
            max_images = len(order['image_urls_list'])

    if orders_data:
        df = pd.DataFrame(orders_data)
        
        # --- SMART FINANCIAL YEAR & ID SORTING ---
        if not df.empty:
            df['temp_date'] = pd.to_datetime(df['order_date'], errors='coerce')
            def get_financial_year(date_obj):
                if pd.isna(date_obj): return 0
                return date_obj.year if date_obj.month >= 4 else date_obj.year - 1
                
            df['fin_year'] = df['temp_date'].apply(get_financial_year)
            df['num_id'] = pd.to_numeric(df['order_id'], errors='coerce').fillna(0)
            df = df.sort_values(by=['fin_year', 'num_id'], ascending=[False, False])
            df = df.drop(columns=['temp_date', 'fin_year', 'num_id'])

        df['Fab Challan'] = df.get('fab_challan', None)
        df['Delivery Challan'] = df.get('delivery_challan', None)
        df['Hidden Delivery Date'] = pd.to_datetime(df.get('delivery_date'), errors='coerce')
        
        col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
        with col_f1: show_history = st.checkbox("🕰️ Show Past/Delivered Orders (Archive View)")
        with col_f2: search_order_id = st.text_input("🔍 Search by Order ID", placeholder="e.g. 1")
        with col_f3: search_del_challan = st.text_input("🔍 Search by Delivery Challan", placeholder="e.g. 152")
        
        if show_history:
            cond_has_challan = df['Delivery Challan'].notna() & (df['Delivery Challan'] != "") & (df['Delivery Challan'].str.lower() != "none")
            filtered_df = df[cond_has_challan].copy()
        else:
            three_days_ago = pd.to_datetime(datetime.now().date() - timedelta(days=3))
            cond_no_challan = df['Delivery Challan'].isna() | (df['Delivery Challan'] == "") | (df['Delivery Challan'].str.lower() == "none")
            cond_recently_delivered = df['Hidden Delivery Date'] >= three_days_ago
            filtered_df = df[cond_no_challan | cond_recently_delivered].copy()

        if search_order_id:
            filtered_df = filtered_df[filtered_df['order_id'].fillna("").astype(str).str.strip() == str(search_order_id).strip()]
        if search_del_challan:
            filtered_df = filtered_df[filtered_df['Delivery Challan'].fillna("").astype(str).str.strip() == str(search_del_challan).strip()]

        filtered_df['Order ID'] = filtered_df['order_id']
        filtered_df['Party'] = filtered_df['party_name']
        filtered_df['Order Date'] = pd.to_datetime(filtered_df['order_date'], errors='coerce').dt.date
        filtered_df['Quantity'] = filtered_df['quantity_formula']
        filtered_df['Designs'] = filtered_df['design_id'] 
        
        # --- DYNAMIC IMAGE COLUMNS: Create Img 1, Img 2, etc. based on max_images ---
        img_column_names = []
        for i in range(max_images):
            col_name = f'Img {i+1}'
            img_column_names.append(col_name)
            # Safely grab the corresponding image URL for this slot, or leave it blank
            filtered_df[col_name] = filtered_df['image_urls_list'].apply(lambda x: x[i] if isinstance(x, list) and len(x) > i else None)

        filtered_df['36" Fabric'] = filtered_df['fabric_36_inch']
        filtered_df['44" Fabric'] = filtered_df['fabric_44_inch']
        filtered_df['58" Fabric'] = filtered_df['fabric_58_inch']
        filtered_df['Remarks'] = filtered_df['remarks']

        # --- UPDATE 1: Moved 'Designs' to the very end of the list! ---
        display_cols = ['Order Date', 'Order ID', 'Party', 'Quantity'] + img_column_names + ['36" Fabric', '44" Fabric', '58" Fabric', 'Fab Challan', 'Delivery Challan', 'Remarks', 'Designs']
        
        display_df = filtered_df[display_cols].copy()
        display_df.insert(0, 'Delete', False)
        display_df.insert(0, 'Edit', False)
        
        def highlight_rows(row):
            if pd.notna(row['Delivery Challan']) and str(row['Delivery Challan']).strip() != "":
                return ['background-color: rgba(40, 167, 69, 0.15)'] * len(row) 
            elif pd.notna(row['Remarks']) and str(row['Remarks']).strip() != "":
                return ['background-color: rgba(255, 193, 7, 0.15)'] * len(row) 
            return [''] * len(row)
            
        styled_df = display_df.style.apply(highlight_rows, axis=1)
        
        st.info("💡 You can now edit Challans and Remarks directly in the table! Click 'Save Table Edits' below to lock them in.")
        
        editor_key = f"table_{'history' if show_history else 'active'}_{st.session_state.table_key}"
        disabled_cols = display_df.columns.drop(['Edit', 'Delete', 'Fab Challan', 'Delivery Challan', 'Remarks']).tolist()
        
        # --- UPDATE 2: Shrunk headers and forced smaller widths ---
        col_config = {
            "Edit": st.column_config.CheckboxColumn("✏️", width="small", default=False),
            "Delete": st.column_config.CheckboxColumn("🗑️", width="small", default=False),
            "Order Date": st.column_config.DateColumn("Date", width="small", format="DD/MM/YYYY"),
            "Order ID": st.column_config.TextColumn("ID", width="small"),
            "Party": st.column_config.TextColumn("Party", width="small"), 
            "Quantity": st.column_config.TextColumn("Qty", width="small"),
            "36\" Fabric": st.column_config.TextColumn("36\"", width="small"),
            "44\" Fabric": st.column_config.TextColumn("44\"", width="small"),
            "58\" Fabric": st.column_config.TextColumn("58\"", width="small"),
            "Fab Challan": st.column_config.TextColumn("Fab", width="small"), # Shortened header
            "Delivery Challan": st.column_config.TextColumn("Del", width="small"), # Shortened header
            "Remarks": st.column_config.TextColumn("Remarks", width="medium"), # Shrunk from large
            "Designs": st.column_config.TextColumn("Design Names", width="large") # Added to end
        }
        
        for col_name in img_column_names:
            col_config[col_name] = st.column_config.ImageColumn(col_name, width="small")

        # --- NEW: CLEAN EXPORT DOWNLOAD BUTTON ---
        st.write("  ") # Adds a little spacing
        
        # 1. Extract ONLY the specific columns you requested from the database
        clean_export_df = filtered_df[[
            'order_date', 'order_id', 'party_name', 'quantity', 
            'fabric_36_inch', 'fabric_44_inch', 'fabric_58_inch', 
            'fab_challan', 'Delivery Challan', 'remarks'
        ]].copy()
        
        # 2. Rename the columns so they look beautiful and professional in Excel
        clean_export_df.columns = [
            'Order Date', 'Order ID', 'Party', 'Quantity', 
            '36" Fabric', '44" Fabric', '58" Fabric', 
            'Fab Challan', 'Del Challan', 'Remarks'
        ]
        
        # 3. Convert dates to plain text to prevent Excel from formatting them weirdly
        clean_export_df['Order Date'] = clean_export_df['Order Date'].astype(str)
        
        # 4. Generate the CSV file in the background
        csv_data = clean_export_df.to_csv(index=False).encode('utf-8')
        
        # 5. Draw the prominent download button
        st.download_button(
            label="📥 Download Clean Report (Excel/CSV)",
            data=csv_data,
            file_name=f"Shree_Nakoda_Orders_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            type="primary" # Makes the button red/highlighted so it's easy to find
        )
        # -----------------------------------------
        
        edited_df = st.data_editor(
            styled_df,
            column_config=col_config,
            disabled=disabled_cols, 
            use_container_width=True,
            hide_index=True,
            key=editor_key
        )
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🗑️ Process Deletions", use_container_width=True):
                deletions_made = False
                for index, row in edited_df.iterrows():
                    if row['Delete'] == True:
                        supabase.table("orders").delete().eq("order_id", row['Order ID']).execute()
                        deletions_made = True
                if deletions_made:
                    st.session_state.table_key += 1
                    st.success("Orders deleted successfully.")
                    st.rerun()
                    
        with col_btn2:
            if st.button("💾 Save Inline Table Edits", type="primary"):
                for index, row in edited_df.iterrows():
                    # Update the database with any direct text edits made in the table
                    update_data = {
                        "fab_challan": str(row['Fab Challan']) if pd.notna(row['Fab Challan']) else "",
                        "delivery_challan": str(row['Delivery Challan']) if pd.notna(row['Delivery Challan']) else "",
                        "remarks": str(row['Remarks']) if pd.notna(row['Remarks']) else ""
                    }
                    # Trigger the hidden date if delivery challan was just filled
                    if update_data["delivery_challan"].strip() != "":
                        check_existing = next((o for o in orders_data if str(o['order_id']) == str(row['Order ID'])), None)
                        if check_existing and not check_existing.get('delivery_date'):
                            update_data["delivery_date"] = str(datetime.now().date())
                            
                    supabase.table("orders").update(update_data).eq("order_id", row['Order ID']).execute()
                st.session_state.table_key += 1
                st.success("Table edits saved successfully!")
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
f_sel_designs = [] # Changed to a list!
existing_del_date = None

if is_editing:
    raw_order = next((o for o in orders_data if str(o['order_id']) == str(selected_order_id)), None)
    if raw_order:
        f_party = raw_order.get('party_name', "")
        f_odate = pd.to_datetime(raw_order.get('order_date')).date() if raw_order.get('order_date') else datetime.now()
        f_qty = raw_order.get('quantity_formula', "")
        f_fchal = raw_order.get('fab_challan', "")
        f_dchal = raw_order.get('delivery_challan', "")
        f_rem = raw_order.get('remarks', "")
        existing_del_date = raw_order.get('delivery_date', None)
        
        # --- NEW: Convert saved comma-separated designs back into a list ---
        raw_design = raw_order.get('design_id')
        if raw_design and str(raw_design).lower() not in ['none', 'nan', '']:
            f_sel_designs = [d.strip() for d in str(raw_design).split(",") if d.strip()]

# --- SMART STATE MEMORY LOCK (Updated for multiple designs) ---
if 'loaded_order_id' not in st.session_state:
    st.session_state['loaded_order_id'] = None
if 'selected_designs' not in st.session_state:
    st.session_state['selected_designs'] = []

if is_editing and st.session_state['loaded_order_id'] != selected_order_id:
    st.session_state['selected_designs'] = f_sel_designs
    st.session_state['loaded_order_id'] = selected_order_id
elif not is_editing and st.session_state['loaded_order_id'] is not None:
    st.session_state['selected_designs'] = []
    st.session_state['loaded_order_id'] = None
# --------------------------------------------------------------
fk_id = f"{st.session_state.form_key}_{f_oid}"

# --- NEW: FETCH STRICTLY FROM FABRIC MASTER DATABASE BY WIDTH ---
try:
    fab_res = supabase.table("fabric_master").select("width, fabric_name").execute()
    fab_data = fab_res.data if fab_res.data else []
    
    # --- FIX: We added ["None"] + to the very front of the lists! ---
    fabrics_36 = ["None"] + sorted(list(set([f['fabric_name'] for f in fab_data if f['width'] == '36"'])))
    fabrics_44 = ["None"] + sorted(list(set([f['fabric_name'] for f in fab_data if f['width'] == '44"'])))
    fabrics_58 = ["None"] + sorted(list(set([f['fabric_name'] for f in fab_data if f['width'] == '58"'])))
except:
    fabrics_36, fabrics_44, fabrics_58 = ["None"], ["None"], ["None"]

# Failsafes
if not fabrics_36: fabrics_36 = ["None"]
if not fabrics_44: fabrics_44 = ["None"]
if not fabrics_58: fabrics_58 = ["None"]
# ----------------------------------------------------------------
# ----------------------------------------------------------------

expander_title = f"✏️ EDITING ORDER: {selected_order_id}" if is_editing else "➕ Click Here to Create a New Order"
with st.expander(expander_title, expanded=is_editing):
    
    col_date, col_id, col_party = st.columns(3)
    with col_date: order_date = st.date_input("Order Date", value=f_odate, format="DD/MM/YYYY", key=f"odate_{fk_id}")
    with col_id: order_id = st.text_input("Order ID *", value=f_oid, disabled=is_editing, key=f"oid_{fk_id}")
    with col_party: party = st.text_input("Party Name *", value=f_party, key=f"party_{fk_id}")

    col_qty = st.columns(1)[0]
    with col_qty:
        q_input = st.text_input("Quantity (e.g., 180 or 25*4)", value=f_qty, key=f"qty_{fk_id}")
        try:
            total_pieces = eval(str(q_input)) if q_input else 0
            if total_pieces > 0: st.caption(f"Total Calculated Pieces: **{total_pieces}**")
        except:
            total_pieces = 0

    st.divider()
    st.write("**🧵 Fabric Details (Separated by Panna)**")
    st.caption("Add rows independently for each width. Type pure numbers for meters (e.g., 50).")

    # Parse existing data into 3 separate lists for editing
    rows_36, rows_44, rows_58 = [], [], []
    if is_editing and raw_order:
        for w_col, row_list in [('fabric_36_inch', rows_36), ('fabric_44_inch', rows_44), ('fabric_58_inch', rows_58)]:
            val = raw_order.get(w_col)
            if val and str(val).lower() not in ["none", "nan"]:
                for part in str(val).split("+"):
                    part = part.strip()
                    if not part: continue
                    if "mtr" in part.lower():
                        try:
                            m = float(part.lower().split("mtr")[0].strip())
                            t = part[part.lower().find("mtr")+3:].strip().title()
                            row_list.append({"Fabric": t, "Meters": m})
                        except: pass
                    else:
                        row_list.append({"Fabric": part.title(), "Meters": 0.0})

    # --- THREE SEPARATE FABRIC TABLES (WITH INBUILT SMART MATH) ---
    import math
    c36, c44, c58 = st.columns(3)
    
    with c36:
        st.markdown('**36" Panna**')
        # 1. The calculator input lives right above the table now
        req_36 = st.number_input("✂️ Avg Meter/Pc", value=2.35, step=0.05, format="%.2f", key=f"req36_{fk_id}")
        calc_36 = total_pieces * req_36
        
        # 2. If it's a new order, auto-fill the table with the exact math!
        init_36 = calc_36 if (not is_editing and total_pieces > 0) else 0.0
        
        df_36 = st.data_editor(
            pd.DataFrame(rows_36 if rows_36 else [{"Fabric": fabrics_36[0], "Meters": init_36}]),
            column_config={
                "Fabric": st.column_config.SelectboxColumn("Fabric Type", options=fabrics_36, required=True, default=fabrics_36[0]),
                "Meters": st.column_config.NumberColumn("Meters", min_value=0.0, format="%.2f", default=0.0)
            },
            num_rows="dynamic", use_container_width=True, hide_index=True, key=f"fab36_{fk_id}"
        )
        if total_pieces > 0: st.caption(f"📐 Auto-calculated: {calc_36:.2f} mtr")

    with c44:
        st.markdown('**44" Panna**')
        req_44 = st.number_input("✂️ Avg Meter/Pc", value=2.55, step=0.05, format="%.2f", key=f"req44_{fk_id}")
        calc_44 = total_pieces * req_44
        
        init_44 = calc_44 if (not is_editing and total_pieces > 0) else 0.0
        
        df_44 = st.data_editor(
            pd.DataFrame(rows_44 if rows_44 else [{"Fabric": fabrics_44[0], "Meters": init_44}]),
            column_config={
                "Fabric": st.column_config.SelectboxColumn("Fabric Type", options=fabrics_44, required=True, default=fabrics_44[0]),
                "Meters": st.column_config.NumberColumn("Meters", min_value=0.0, format="%.2f", default=0.0)
            },
            num_rows="dynamic", use_container_width=True, hide_index=True, key=f"fab44_{fk_id}"
        )
        if total_pieces > 0: st.caption(f"📐 Auto-calculated: {calc_44:.2f} mtr")

    with c58:
        st.markdown('**58" Panna**')
        req_58 = st.number_input("✂️ Meter per 2 Pcs", value=2.55, step=0.05, format="%.2f", key=f"req58_{fk_id}")
        
        # Apply the divide by 2 and round up rule specifically for 58"
        raw_58 = (total_pieces / 2) * req_58
        calc_58 = float(math.ceil(raw_58)) if total_pieces > 0 else 0.0
        
        init_58 = calc_58 if (not is_editing and total_pieces > 0) else 0.0
        
        df_58 = st.data_editor(
            pd.DataFrame(rows_58 if rows_58 else [{"Fabric": fabrics_58[0], "Meters": init_58}]),
            column_config={
                "Fabric": st.column_config.SelectboxColumn("Fabric Type", options=fabrics_58, required=True, default=fabrics_58[0]),
                "Meters": st.column_config.NumberColumn("Meters", min_value=0.0, format="%.2f", default=0.0)
            },
            num_rows="dynamic", use_container_width=True, hide_index=True, key=f"fab58_{fk_id}"
        )
        if total_pieces > 0: st.caption(f"📐 Auto-calculated: {calc_58:.2f} mtr (Exact: {raw_58:.2f})")
    
    c1, c2, c3 = st.columns(3)
    with c1: fab_challan_input = st.text_input("🏭 Fabric Challan No.", value=f_fchal, key=f"fchallan_{fk_id}")
    with c2: del_challan_input = st.text_input("🚚 Delivery Challan No.", value=f_dchal, help="Order stays visible for 3 days after entry.", key=f"dchallan_{fk_id}")
    with c3: remarks_input = st.text_input("📝 Remarks", value=f_rem, key=f"rem_{fk_id}")
    
    st.divider()
    st.write("**Kurti Design Selection (Multi-Select)**")
    
    response = supabase.table("kurti_catalog").select("design_id, image_url").order("design_id", desc=True).execute()
    existing_designs = response.data

    if existing_designs:
        search_design = st.text_input("🔍 Search Design ID", placeholder="Type to filter images...", key=f"search_design_{fk_id}")
        
        if search_design:
            filtered_designs = [d for d in existing_designs if search_design.lower() in str(d['design_id']).lower()]
        else:
            filtered_designs = existing_designs

        if filtered_designs:
            with st.popover(f"🖼️ Click to Select Designs ({len(filtered_designs)} found)", use_container_width=True):
                st.caption("Click a button to select it. Click it again to deselect.")
                
                for i in range(0, len(filtered_designs), 3):
                    row_designs = filtered_designs[i:i+3]
                    cols = st.columns(3)
                    
                    for j, design in enumerate(row_designs):
                        with cols[j]:
                            d_id = design['design_id']
                            is_selected = d_id in st.session_state['selected_designs']
                            btn_label = f"✅ Selected: {d_id}" if is_selected else f"Pick {d_id}"
                            btn_type = "primary" if is_selected else "secondary"
                            
                            if st.button(btn_label, key=f"vpick_{d_id}_{fk_id}_{i}_{j}", type=btn_type, use_container_width=True):
                                if is_selected:
                                    st.session_state['selected_designs'].remove(d_id)
                                else:
                                    st.session_state['selected_designs'].append(d_id)
                                st.rerun()
                                
                            try:
                                if design.get('image_url'): 
                                    st.image(design['image_url'], use_container_width=True)
                            except: 
                                st.caption("No image available")
                            st.write("") 
        else:
            st.warning(f"No designs found matching '{search_design}'.")

        if st.session_state['selected_designs']:
            st.success(f"Selected Designs: {', '.join(st.session_state['selected_designs'])}")
            display_images, display_captions = [], []
            for sel_id in st.session_state['selected_designs']:
                img_url = next((d['image_url'] for d in existing_designs if d['design_id'] == sel_id), None)
                if img_url:
                    display_images.append(img_url)
                    display_captions.append(sel_id)
            if display_images:
                st.image(display_images, width=150, caption=display_captions)
    else:
        st.info("No designs found in the catalog.")

    # --- SAVE OR UPDATE LOGIC ---
    btn_text = f"💾 UPDATE Order {f_oid}" if is_editing else "💾 SAVE New Order"
    
    if st.button(btn_text, key=f"save_{fk_id}", type="primary"):
        if not order_id or not party:
            st.error("Order ID and Party Name are required!")
        else:
            try:
                save_del_date = None
                if del_challan_input and str(del_challan_input).strip() != "":
                    save_del_date = existing_del_date if existing_del_date else str(datetime.now().date())
                
                fab_36_list, fab_44_list, fab_58_list = [], [], []
                
               # --- NEW: Helper function with Blank/None Protection ---
               # --- UPDATED: Helper function that ALLOWS 0.0 meters for planning ---
                def process_fab_df(df_target, target_list):
                    for _, row in df_target.iterrows():
                        m, t = row['Meters'], row['Fabric']
                        
                        if pd.isna(m): 
                            m = 0.0
                            
                        # Save the fabric as long as it is NOT "None", even if meters are 0.0!
                        if pd.notna(t) and str(t).strip() != "" and str(t).strip().lower() != "none":
                            target_list.append(f"{m}mtr {t}")

                process_fab_df(df_36, fab_36_list)
                process_fab_df(df_44, fab_44_list)
                process_fab_df(df_58, fab_58_list)
                
                final_designs_str = ", ".join(st.session_state['selected_designs']) if st.session_state['selected_designs'] else None
                        
                order_data = {
                    "party_name": party,
                    "order_date": str(order_date),
                    "quantity_formula": q_input,
                    "quantity_total": total_pieces,
                    "design_id": final_designs_str,  
                    "fabric_36_inch": " + ".join(fab_36_list) if fab_36_list else None,
                    "fabric_44_inch": " + ".join(fab_44_list) if fab_44_list else None,
                    "fabric_58_inch": " + ".join(fab_58_list) if fab_58_list else None,
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
                        st.warning(f"⚠️ Order ID '{order_id}' already exists!")
                        st.stop()
                    else:
                        order_data["order_id"] = order_id
                        supabase.table("orders").insert(order_data).execute()
                        st.success(f"Order {order_id} CREATED successfully!")
                    
                st.session_state['selected_designs'] = []  
                st.session_state['loaded_order_id'] = None
                st.session_state.form_key += 1
                st.session_state.table_key += 1              
                st.rerun() 
                
            except Exception as e:
                st.error(f"Error: {e}")
