# 🏢 Shree Nakoda Textiles - Enterprise Portal

A custom-built, enterprise-grade web application designed to manage the active order lifecycle, track complex fabric usage, assign delivery challans, and securely maintain factory floor data for Shree Nakoda Textiles.

## ✨ Key Features & Upgrades

### 📊 Smart Interactive Dashboard
* 🔒 **Secure Gateway:** The main dashboard and analytics are protected by an Admin PIN. Includes a quick **🔒 Lock Dashboard** sidebar button for stepping away from the desk. 

* ✍️ **Inline Table Editing:** Update `Fab Challan`, `Delivery Challan`, and `Remarks` directly from the active table without opening the order form.

* 🚦 **Color-Coded Status:** Rows automatically highlight **Green** when dispatched (Delivery Challan assigned) and **Yellow** when Remarks are added.

* 🔍 **Dual Exact-Match Search:** Instantly retrieve specific orders using the dedicated `Order ID` or `Delivery Challan` search bars.

* 📦 **Smart Archiving:** Dispatched orders remain visible for 3 days before automatically moving to the "Archive View" (which can be toggled via checkbox).

* 🧹 **Self-Cleaning Database:** Built-in auto-maintenance permanently deletes records older than 250 days to ensure lightning-fast load speeds.

### 🧵 Dynamic Order Entry & Design Selection
* **Smart Fabric Table:** A dynamic data grid allows staff to log multiple fabrics under the same width (e.g., mixing two 44" fabrics). Automatically formats and saves data as strings (e.g., `100.00mtr Linen + 50.00mtr Mal`).

* **Auto-Learning Dropdowns:** Staff can type new fabric names directly into the form, which instantly updates the master selection dropdowns.

* **Visual Popover Selection:** Replaced bulky image grids with a clean, searchable popover menu. Newest designs (`design_id` descending) automatically populate at the top of the list.

### 📈 Business Intelligence (Analytics Page)
A dedicated `2_Analytics.py` page powered by Plotly for real-time factory insights:
* 🚨 **Smart Data Audit:** Automatically scans the database and flags specific `Order IDs` where staff forgot to enter meterage (`mtr`), ensuring charts remain 100% accurate.
* **Stacked Fabric Consumption:** Large, interactive bar charts group fabric by base material (e.g., Total Linen) and segment them by specific variants (36", 44"). Hovering over a block reveals the exact Order ID tied to that fabric.
* **Pending vs. Delivered:** Real-time pie chart of the current factory backlog.
* **Volume Trends:** Area chart tracking total pieces ordered over time.

## 🛠️ Tech Stack

* **Frontend & Logic:** [Streamlit](https://streamlit.io/) (Python)
* **Data Processing:** Pandas
* **Charting Engine:** Plotly Express
* **Backend & Database:** [Supabase](https://supabase.com/) (PostgreSQL)

## 🚀 Local Setup & Installation

**1. Clone the repository:**
```bash
git clone [https://github.com/YourUsername/kurti-identifier.git](https://github.com/YourUsername/kurti-identifier.git)
cd kurti-identifier
```

**2. Install dependencies:**
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```
*(Ensure `streamlit>=1.35.0` and `plotly>=5.20.0` are included).*

**3. Configure Environment Variables:**
Create a `.streamlit` folder in the root directory and add a `secrets.toml` file with your secure credentials:
```toml
SUPABASE_URL = "your-supabase-project-url"
SUPABASE_KEY = "your-supabase-anon-key"
ADMIN_PIN = "your-secret-pin"
```

**4. Run the app:**
```bash
streamlit run app.py
```

## 🗄️ Database Schema Requirements

This application relies on a connected Supabase PostgreSQL database. 

### Table: `orders`
* `order_id` (Text / Primary Key)
* `party_name` (Text)
* `order_date` (Date)
* `quantity_formula` (Text)
* `quantity_total` (Numeric)
* `design_id` (Text / Foreign Key to kurti_catalog)
* `fabric_36_inch` (Text) - *Parses concatenated strings (e.g., "50mtr Linen + 20mtr Mal")*
* `fabric_44_inch` (Text) 
* `fabric_58_inch` (Text)
* `fab_challan` (Text)
* `delivery_challan` (Text)
* `delivery_date` (Date) 
* `remarks` (Text)

### Table: `kurti_catalog`
* `design_id` (Text / Primary Key)
* `image_url` (Text)
```