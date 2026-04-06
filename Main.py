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
        
        col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
        with col_f1: show_history = st.checkbox("🕰️ Show Past/Delivered Orders (Archive View)")
        with col_f2: search_order_id = st.text_input("🔍 Search by Order ID", placeholder="e.g. 1")
        with col_f3: search_del_challan = st.text_input("🔍 Search by Delivery Challan", placeholder="e.g. 152")
        
        if show_history:
            # ONLY show delivered orders
            cond_has_challan = df['Delivery Challan'].notna() & (df['Delivery Challan'] != "") & (df['Delivery Challan'].str.lower() != "none")
            filtered_df = df[cond_has_challan].copy()
        else:
            # Active orders logic
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
        filtered_df['36" Fabric'] = filtered_df['fabric_36_inch']
        filtered_df['44" Fabric'] = filtered_df['fabric_44_inch']
        filtered_df['58" Fabric'] = filtered_df['fabric_58_inch']
        filtered_df['Remarks'] = filtered_df['remarks']

        display_df = filtered_df[['Order Date', 'Order ID', 'Party', 'Quantity', 'Image', '36" Fabric', '44" Fabric', '58" Fabric', 'Fab Challan', 'Delivery Challan', 'Remarks']].copy()
        display_df.insert(0, 'Delete', False)
        display_df.insert(0, 'Edit', False)
        
        # --- COLOR CODING LOGIC ---
        def highlight_rows(row):
            if pd.notna(row['Delivery Challan']) and str(row['Delivery Challan']).strip() != "":
                return ['background-color: rgba(40, 167, 69, 0.15)'] * len(row) # Green
            elif pd.notna(row['Remarks']) and str(row['Remarks']).strip() != "":
                return ['background-color: rgba(255, 193, 7, 0.15)'] * len(row) # Yellow
            return [''] * len(row)
            
        styled_df = display_df.style.apply(highlight_rows, axis=1)
        
        st.info("💡 You can now edit Challans and Remarks directly in the table! Click 'Save Table Edits' below to lock them in.")
        
        editor_key = f"table_{'history' if show_history else 'active'}_{st.session_state.table_key}"
        
        # Make Fab Challan, Del Challan, and Remarks editable by removing them from disabled_cols
        disabled_cols = display_df.columns.drop(['Edit', 'Delete', 'Fab Challan', 'Delivery Challan', 'Remarks']).tolist()
        
        edited_df = st.data_editor(
            styled_df,
            column_config={
                "Edit": st.column_config.CheckboxColumn("✏️", width="small", default=False),
                "Delete": st.column_config.CheckboxColumn("🗑️", width="small", default=False),
                "Order Date": st.column_config.DateColumn("Date", width="small", format="DD/MM/YYYY"),
                "Order ID": st.column_config.TextColumn("ID", width="small"),
                "Party": st.column_config.TextColumn("Party", width="medium"),
                "Quantity": st.column_config.TextColumn("Qty", width="small"),
                "Image": st.column_config.ImageColumn("Img", width="small"),
                "36\" Fabric": st.column_config.TextColumn("36\"", width="small"),
                "44\" Fabric": st.column_config.TextColumn("44\"", width="small"),
                "58\" Fabric": st.column_config.TextColumn("58\"", width="small"),
                "Fab Challan": st.column_config.TextColumn("Fab Challan", width="medium"),
                "Delivery Challan": st.column_config.TextColumn("Del Challan", width="medium"),
                "Remarks": st.column_config.TextColumn("Remarks", width="large")
            },
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
f_sel_design = None
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
        f_sel_design = raw_order.get('design_id', None)
        existing_del_date = raw_order.get('delivery_date', None)

fk_id = f"{st.session_state.form_key}_{f_oid}"

# 1. Fetch all unique fabric names to populate the dropdown dynamically
def get_known_fabrics(data):
    fabrics = {"Linen", "Mal", "Cambric", "Linen Butti", "Linen Shimmer", "Maslin", "Linen Jari Patta" , "Lo" , "Georgette"} 
    if data:
        for row in data:
            for col in ['fabric_36_inch', 'fabric_44_inch', 'fabric_58_inch']:
                val = str(row.get(col, ""))
                if val and val.lower() not in ["none", "nan"]:
                    for part in val.split("+"):
                        if "mtr " in part.lower():
                            try: fabrics.add(part.lower().split("mtr ")[1].strip().title())
                            except: pass
                        else:
                            try: fabrics.add(part.strip().title())
                            except: pass
    return sorted(list(fabrics))

known_fabrics = get_known_fabrics(orders_data)

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
    st.write("**🧵 Fabric Details**")
    st.caption("Click the empty row at the bottom to add a new fabric. Double-click cells to edit. Type pure numbers for meters (e.g., 50).")

    # --- MOVED ABOVE THE TABLE ---
    new_fabric_type = st.text_input("➕ Need a fabric not in the list? Type it here to instantly add it to the dropdowns below:", placeholder="e.g. Linen Butti", key=f"new_fab_input_{fk_id}")

    if new_fabric_type:
        new_fab_clean = new_fabric_type.strip().title()
        if new_fab_clean not in known_fabrics:
            known_fabrics.append(new_fab_clean)
            known_fabrics = sorted(known_fabrics)
            st.success(f"✨ '{new_fab_clean}' added! You can now select it in the table below.")
    # -----------------------------

    # Convert existing string data back into a table for editing
    existing_fab_rows = []
    if is_editing and raw_order:
        for w_col, w_label in [('fabric_36_inch', '36"'), ('fabric_44_inch', '44"'), ('fabric_58_inch', '58"')]:
            val = raw_order.get(w_col)
            if val and str(val).lower() not in ["none", "nan"]:
                for part in str(val).split("+"):
                    part = part.strip()
                    if not part: continue
                    if "mtr" in part.lower():
                        try:
                            m = float(part.lower().split("mtr")[0].strip())
                            t = part[part.lower().find("mtr")+3:].strip().title()
                            existing_fab_rows.append({"Width": w_label, "Fabric": t, "Meters": m})
                        except: pass
                    else:
                        existing_fab_rows.append({"Width": w_label, "Fabric": part.title(), "Meters": 0.0})

    # The Structured Table Editor
    edited_fab_df = st.data_editor(
        pd.DataFrame(existing_fab_rows if existing_fab_rows else [{"Width": '44"', "Fabric": "Linen", "Meters": 0.0}]),
        column_config={
            "Width": st.column_config.SelectboxColumn("Width", options=['36"', '44"', '58"'], required=True),
            "Fabric": st.column_config.SelectboxColumn("Fabric Type", options=known_fabrics, required=True),
            "Meters": st.column_config.NumberColumn("Meters", min_value=0.0, format="%.2f")
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"fab_table_{fk_id}"
    )

    st.divider()
    
    c1, c2, c3 = st.columns(3)
    with c1: fab_challan_input = st.text_input("🏭 Fabric Challan No.", value=f_fchal, key=f"fchallan_{fk_id}")
    with c2: del_challan_input = st.text_input("🚚 Delivery Challan No.", value=f_dchal, help="Order stays visible for 3 days after entry.", key=f"dchallan_{fk_id}")
    with c3: remarks_input = st.text_input("📝 Remarks", value=f_rem, key=f"rem_{fk_id}")
    
    st.divider()
    st.write("**Kurti Design Selection**")
    
    response = supabase.table("kurti_catalog").select("design_id, image_url").order("design_id", desc=True).execute()
    existing_designs = response.data
    selected_design_id = st.session_state.get('selected_design', f_sel_design)

    if existing_designs:
        search_design = st.text_input("🔍 Search Design ID", placeholder="Type to filter images...", key=f"search_design_{fk_id}")
        
        if search_design:
            filtered_designs = [d for d in existing_designs if search_design.lower() in str(d['design_id']).lower()]
        else:
            filtered_designs = existing_designs

        if filtered_designs:
            with st.popover(f"🖼️ Click to Select Design Image ({len(filtered_designs)} found)", use_container_width=True):
                st.caption("Scroll down to see all designs")
                
                for i in range(0, len(filtered_designs), 3):
                    row_designs = filtered_designs[i:i+3]
                    cols = st.columns(3)
                    
                    for j, design in enumerate(row_designs):
                        with cols[j]:
                            # --- THE FIX: We moved the button ABOVE the image! ---
                            # We also made it wide so it acts like a title bar
                            if st.button(f"Pick {design['design_id']}", key=f"vpick_{design['design_id']}_{fk_id}_{i}_{j}", use_container_width=True):
                                st.session_state['selected_design'] = design['design_id']
                                st.rerun()
                                
                            try:
                                if design.get('image_url'): 
                                    st.image(design['image_url'], use_container_width=True)
                            except: 
                                st.caption("No image available")
                            
                            st.write("") # Adds a clean little gap before the next row starts
        else:
            st.warning(f"No designs found matching '{search_design}'.")

        if selected_design_id:
            st.success(f"Selected Design: {selected_design_id}")
            selected_img = next((d['image_url'] for d in existing_designs if d['design_id'] == selected_design_id), None)
            if selected_img: st.image(selected_img, width=150)
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
                
                # --- COMPRESS TABLE BACK TO STRINGS ---
                fab_36_list, fab_44_list, fab_58_list = [], [], []
                for _, row in edited_fab_df.iterrows():
                    w = row['Width']
                    m = row['Meters']
                    t = row['Fabric']

                    if pd.notna(w) and pd.notna(m) and pd.notna(t) and str(t).strip() != "":
                        # Rebuild the string e.g. "50.0mtr Linen"
                        val = f"{m}mtr {t}"
                        if w == '36"': fab_36_list.append(val)
                        elif w == '44"': fab_44_list.append(val)
                        elif w == '58"': fab_58_list.append(val)

                order_data = {
                    "party_name": party,
                    "order_date": str(order_date),
                    "quantity_formula": q_input,
                    "quantity_total": total_pieces,
                    "design_id": selected_design_id,
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
                    
                st.session_state['selected_design'] = None  
                st.session_state.form_key += 1
                st.session_state.table_key += 1              
                st.rerun() 
                
            except Exception as e:
                st.error(f"Error: {e}")