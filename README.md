# 🏢 Shree Nakoda Textiles - Enterprise Portal

A custom-built, enterprise-grade web application designed to manage the active order lifecycle, track fabric usage, assign delivery challans, and securely maintain factory floor data for Shree Nakoda Textiles.

## ✨ Key Features

* 🔒 **Secure Gateway (Role-Based Access):** The main dashboard is protected by an Admin PIN. Designers can use the sidebar to access the "Kurti Identifier" without seeing sensitive client order data.

* 📊 **Smart Interactive Dashboard:** Features a clean, click-to-edit table interface. Includes exact-match search filters for quick retrieval by **Order ID** or **Delivery Challan No.**

* 📦 **Automated Smart Archiving:** When a Delivery Challan is assigned, a hidden 3-day timer starts. The order remains on the active screen for 72 hours for easy reference before automatically moving to the "Archive View".

* 🧹 **Self-Cleaning Database:** A built-in auto-maintenance routine runs invisibly every time the app opens, permanently deleting records older than 250 days to ensure lightning-fast loading speeds.

* 🧵 **Dynamic Fabric Tracking:** Track 36", 44", and 58" fabric meters. The system includes a dynamic memory dropdown that remembers newly added custom fabric types.

* 📅 **Localized Formatting:** All dates are standardized to the Indian `DD/MM/YYYY` format for ease of use.

## 🛠️ Tech Stack

* **Frontend & Logic:** [Streamlit](https://streamlit.io/) (Python)
* **Data Processing:** Pandas
* **Backend & Database:** [Supabase](https://supabase.com/) (PostgreSQL)

## 🚀 Local Setup & Installation

Follow these steps to run the portal on your local machine:

**1. Clone the repository:**
```bash
git clone [https://github.com/YourUsername/kurti-identifier.git](https://github.com/YourUsername/kurti-identifier.git)
cd kurti-identifier
```

**2. Install dependencies:**
Make sure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

**3. Configure Environment Variables:**
Create a `.streamlit` folder in the root directory and add a `secrets.toml` file with your secure credentials:
```toml
SUPABASE_URL = "your-supabase-project-url"
SUPABASE_KEY = "your-supabase-anon-key"
ADMIN_PASSWORD ="your-secret-password"
ADMIN_PIN = "your-secret-pin"
```

**4. Run the app:**
```bash
streamlit run app.py
```

## 🗄️ Database Schema Requirements

This application relies on a connected Supabase PostgreSQL database with the following table structures:

### Table: `orders`
* `order_id` (Text / Primary Key)
* `party_name` (Text)
* `order_date` (Date)
* `quantity_formula` (Text)
* `quantity_total` (Numeric)
* `design_id` (Text / Foreign Key to kurti_catalog)
* `fabric_36_inch` (Text)
* `fabric_44_inch` (Text)
* `fabric_58_inch` (Text)
* `fab_challan` (Text)
* `delivery_challan` (Text)
* `delivery_date` (Date) - *Used for the 3-day archive timer and 250-day cleanup*
* `remarks` (Text)

### Table: `kurti_catalog`
* `design_id` (Text / Primary Key)
* `image_url` (Text)

## 👨‍💻 Workflow Guide for Staff

1. **Creating Orders:** Click the expansion panel at the bottom of the dashboard. Fill out the details. If a new fabric type is needed, select "➕ Add New..." from the dropdown.
2. **Editing Orders:** Check the **✏️ Edit** box next to any order in the main table. The form will automatically pop open and pre-fill with the order's data. Make your changes and click Update.
3. **Dispatching:** Enter a Delivery Challan No. to trigger the dispatch logic. The order will remain visible for 3 days before moving to the Archive view.
4. **Locking:** Use the **🔒 Lock Dashboard** button in the sidebar when stepping away from your workstation.
