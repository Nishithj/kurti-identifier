import streamlit as st
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from supabase import create_client, Client
import uuid
import io
import numpy as np
import cv2
import re # regex library for cleaning up extracted text
import pytesseract
# Add this line specifically for Windows:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # <-- NEW: The OCR Library

# --- 1. SETUP & CACHING ---
st.set_page_config(page_title="Kurti Design Identifier", page_icon="👗")

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

@st.cache_resource
def load_model():
    model = models.resnet18(pretrained=True)
    model = torch.nn.Sequential(*(list(model.children())[:-1]))
    model.eval()
    return model

model = load_model()

# --- 2. CORE FUNCTIONS ---
def get_image_embedding(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    input_tensor = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)
    return output.squeeze().numpy().tolist()


def extract_text_from_image(image_bytes):
    """Reads text from the bottom 10% of the image to avoid reading fabric patterns."""
    # 1. Open the image using PIL
    pil_image = Image.open(io.BytesIO(image_bytes))
    open_cv_image = np.array(pil_image)
    # 2. Convert PIL image to OpenCV format (NumPy array)

    # 3. Pre-processing for OCR
    # Convert to grayscale
    if open_cv_image.shape[2] == 4:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
    open_cv_image = open_cv_image[:, :, ::-1].copy() 

    # --- NEW: Crop the image to only the bottom 10% ---
    height, width, _ = open_cv_image.shape
    open_cv_image = open_cv_image[int(height * 0.90):height, :]

    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3,3), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    inverted = 255 - thresh

    # Read the cropped image
    text = pytesseract.image_to_string(inverted, config='--psm 11').replace('\n', ' ').strip()
    return text

# --- 3. USER INTERFACE ---
st.title("👗 Kurti Design Identifier")

# Create a sidebar for navigation
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Go to:", ["🔍 Search Design", "➕ Add New Design"])

# ==========================================
# TAB 1: SEARCH ENGINE
# ==========================================
if app_mode == "🔍 Search Design":
    st.write("Upload a photo of a kurti to find its details.")
    search_file = st.file_uploader("Upload Image to Search", type=['jpg', 'png', 'jpeg'], key="search")
    
    if search_file is not None:
        file_bytes = search_file.getvalue()
        st.image(file_bytes, caption="Uploaded Image", width=250)
        
        with st.spinner("Analyzing fabric patterns..."):
            query_vector = get_image_embedding(file_bytes)
            
            # Fetch top 3 matches to handle multiple parties with the same design
            response = supabase.rpc(
                'match_kurti_designs', 
                {'query_embedding': query_vector, 'match_threshold': 0.7, 'match_count': 3}
            ).execute()
            
            results = response.data
            
            if results:
                st.success(f"Found {len(results)} matching designs!")
                for match in results:
                    st.write("---")
                    st.write(f"**Design ID:** {match['design_id']}")
                    st.write(f"**Party/Designer:** {match['party_name']}")
                    st.write(f"**Confidence:** {match['similarity'] * 100:.1f}%")
                    st.image(match['image_url'], width=250)
            else:
                st.error("No closely matching designs found in the database.")

# ==========================================
# TAB 2: ADMIN PANEL
# ==========================================
elif app_mode == "➕ Add New Design":
    st.write("Add new unstitched suits or catalog pieces to the database.")
    
    # 1. Initialize the "memory" for the login state
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    # 2. If NOT logged in, show the secure login form
    if not st.session_state.is_admin:
        with st.form("login_form"):
            admin_pass = st.text_input("Enter Admin Password to unlock", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if admin_pass == st.secrets.get("ADMIN_PASSWORD", ""):
                    # Save the login state and instantly refresh the UI
                    st.session_state.is_admin = True
                    st.rerun() 
                else:
                    st.error("Incorrect Password.")

    # 3. If LOGGED IN, show the upload tools
    if st.session_state.is_admin:
        # Add a logout button right at the top for easy access
        if st.button("🔒 Lock Admin Panel (Logout)"):
            st.session_state.is_admin = False
            st.rerun()
            
        st.success("Unlocked! You are securely logged in.")
        
        party_name = st.text_input("Party Name *", value="Shree Nakoda Textiles")
        upload_file = st.file_uploader("Upload Catalog Image *", type=['jpg', 'png', 'jpeg'], key="upload")
        
        if st.button("Save to Database"):
            if not party_name or not upload_file:
                st.warning("Please provide both a Party Name and an Image.")
            else:
                with st.spinner("Processing image and extracting text..."):
                    file_bytes = upload_file.getvalue()
                    
                    # --- 1. OCR TEXT EXTRACTION ---
                    raw_text = extract_text_from_image(file_bytes)
                    import re
                    match = re.search(r'([A-Z]{2,}-\d+.*)', raw_text)

                    if match:
                        extracted_text = match.group(1).strip()
                    else:
                        extracted_text = raw_text

                    if len(extracted_text) > 3: 
                        final_design_id = extracted_text
                        st.info(f"AI Detected ID: {final_design_id}")
                    else:
                        safe_party = party_name.replace(" ", "").upper()
                        random_code = str(uuid.uuid4())[:4].upper()
                        final_design_id = f"INT-{safe_party}-{random_code}"
                        st.warning(f"No text detected. Auto-generated ID: {final_design_id}")
                    
                    # --- 2. VECTOR & UPLOAD ---
                    vector = get_image_embedding(file_bytes)
                    file_extension = upload_file.name.split('.')[-1].lower()
                    
                    # --- UPGRADED: Cleaner File Naming ---
                    safe_file_name = re.sub(r'[^a-zA-Z0-9]', '-', final_design_id)
                    safe_file_name = re.sub(r'-+', '-', safe_file_name).strip('-')
                    safe_file_name = safe_file_name[:50]
                    
                    file_name = f"{safe_file_name}.{file_extension}"
                    
                    content_type = f"image/{file_extension}" if file_extension != "jpg" else "image/jpeg"
                    
                    supabase.storage.from_("kurti_designs").upload(
                        file=file_bytes,
                        path=file_name,
                        file_options={"content-type": content_type}
                    )
                    
                    public_url = supabase.storage.from_("kurti_designs").get_public_url(file_name)
                    
                    supabase.table("kurti_catalog").insert({
                        "design_id": final_design_id,
                        "party_name": party_name,
                        "image_url": public_url,
                        "embedding": vector
                    }).execute()
                    
                    st.success(f"Design successfully added!")