import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Fabric Master", layout="wide")

# --- 🔒 SECURITY GATEWAY ---
if 'admin_unlocked' not in st.session_state or not st.session_state.admin_unlocked:
    st.warning("🔒 Please unlock the dashboard on the Main page first.")
    st.stop()

st.title("🧵 Master Fabric Manager")
st.caption("Add or remove fabrics here. These lists will automatically power the dropdown menus on the main order form.")

# --- DATABASE CONNECTION ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- FETCH CURRENT FABRICS ---
res = supabase.table("fabric_master").select("*").execute()
df = pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["id", "width", "fabric_name"])

# --- UI: 3 SEPARATE TABS FOR THE PANNAS ---
tab36, tab44, tab58 = st.tabs(['36" Panna', '44" Panna', '58" Panna'])

def render_fabric_manager(width_label, tab):
    with tab:
        st.subheader(f"Manage {width_label} Fabrics")
        
        # 1. ADD NEW FABRIC SECTION
        col1, col2 = st.columns([3, 1])
        with col1:
            new_fab = st.text_input(f"➕ Add New {width_label} Fabric", placeholder="e.g. Linen Butti", key=f"add_{width_label}")
        with col2:
            st.write("") 
            st.write("") # Alignment spacing
            if st.button("Save to Master List", key=f"btn_{width_label}", type="primary", use_container_width=True):
                if new_fab:
                    # Prevent duplicates
                    existing = df[(df['width'] == width_label) & (df['fabric_name'].str.lower() == new_fab.strip().lower())]
                    if not existing.empty:
                        st.warning(f"'{new_fab}' already exists in the {width_label} list!")
                    else:
                        supabase.table("fabric_master").insert({"width": width_label, "fabric_name": new_fab.strip().title()}).execute()
                        st.success("Fabric Added!")
                        st.rerun()

        st.divider()
        
        # 2. DELETE EXISTING FABRICS SECTION
        width_df = df[df['width'] == width_label].copy()
        if not width_df.empty:
            width_df.insert(0, 'Delete', False)
            st.write("**Current Active Fabrics**")
            
            edited = st.data_editor(
                width_df[['Delete', 'fabric_name', 'id']],
                column_config={
                    "Delete": st.column_config.CheckboxColumn("🗑️", width="small"),
                    "fabric_name": st.column_config.TextColumn("Fabric Name", width="large", disabled=True),
                    "id": None # We hide the database ID from the user
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_{width_label}"
            )
            
            if st.button(f"🗑️ Delete Selected {width_label} Fabrics", key=f"del_{width_label}"):
                to_delete = edited[edited['Delete'] == True]['id'].tolist()
                if to_delete:
                    for fab_id in to_delete:
                        supabase.table("fabric_master").delete().eq("id", fab_id).execute()
                    st.success("Fabrics permanently removed from dropdowns!")
                    st.rerun()
        else:
            st.info(f"No fabrics added for {width_label} yet.")

# Render the layout for all three tabs
render_fabric_manager('36"', tab36)
render_fabric_manager('44"', tab44)
render_fabric_manager('58"', tab58)