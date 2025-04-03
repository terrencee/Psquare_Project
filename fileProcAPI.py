import base64
from fastapi import FastAPI, UploadFile, File, Query, Form, Request, HTTPException
import magic
import fitz  # PyMuPDF for PDFs
import docx2txt
import pytesseract
from PIL import Image
from bs4 import BeautifulSoup
import io
import pdfplumber
from docx import Document
import cv2
import numpy as np
import ollama  # Ollama API integration
import requests # For making HTTP requests to the LLM API
from dotenv import load_dotenv  
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import subprocess
from fastapi.responses import HTMLResponse
import io
from fastapi.responses import StreamingResponse
import subprocess
import logging
from typing import List

#from file_processor import process_reimbursement_form

# Load the .env file explicitly
load_dotenv("huggingFaceAPIKey.env")  #  Specify your actual .env filename

# Get API Key securely
# HF_API_KEY = os.getenv("HF_API_KEY", "your-api-key-here")
HF_API_KEY = os.getenv("HF_API_KEY")  # Replace if not using .env
# print(f"Hugging Face API Key: {HF_API_KEY[:10]}********")  # Print first 10 characters only

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Path to pdflatex (ensure this is correct)
PDFLATEX_PATH = r"C:\Users\chick\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"

models = [
    "llama3-gradient:8b", "llama2:7b", "llama2-uncensored:latest",
    "llama3-gradient:1048k", "qwen:0.5b", "qwen2:0.5b", "qwen2:1.5b",
    "llama3.2:1b", "llama2:latest", "llama2:13b", "deepseek-v2:latest",
    "llama3-chatqa:latest", "deepseek-r1:7b", "qwen2.5:1.5b", "deepseek-r1:1.5b",
    "qwen2.5:0.5b", "qwen:4b", "qwen:1.8b", "mistral-small:24b", "codestral:latest",
    "mistral-small:22b", "mistral-nemo:latest", "dolphin-mistral:latest",
    "samantha-mistral:latest", "mistral:latest", "mistrallite:latest", "phi:latest",
    "qwen2.5:14b", "qwen:14b", "qwen2.5:7b", "qwen2.5:latest", "qwen2:7b",
    "qwen:7b", "deepseek-r1:14b", "deepseek-r1:8b", "llama3.1:latest",
    "llama3:latest", "llama3.2:latest"
]

def detect_file_type(file_bytes):
    """Identify file type based on magic bytes (MIME type)"""
    mime = magic.Magic(mime=True)
    return mime.from_buffer(file_bytes[:2048])  # Check first 2KB for type

#  Extract Tables from PDFs
def extract_pdf_tables(file_bytes):
    tables = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted_tables = page.extract_tables()
            for table in extracted_tables:
                tables.append(table)  # List of table data as lists of lists
    return tables

#  Extract Tables from Word Docs
def extract_docx_tables(file_bytes):
    tables = []
    doc = Document(io.BytesIO(file_bytes))
    
    for table in doc.tables:
        table_data = []
        for row in table.rows:
            table_data.append([cell.text.strip() for cell in row.cells])
        tables.append(table_data)
    
    return tables

#  Extract Tables from Images using OCR
def extract_image_tables(image_bytes):
    """Detect and extract tables from an image using OCR"""
    image = Image.open(io.BytesIO(image_bytes))
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

    # Thresholding to enhance table structure
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Find contours of table cells
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    table_data = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        cropped = gray[y:y+h, x:x+w]
        text = pytesseract.image_to_string(cropped, config='--psm 6')  # OCR for each cell
        table_data.append(text.strip())

    return table_data

#  Extract Tables from HTML
def extract_html_tables(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    tables = []
    
    for table in soup.find_all("table"):
        rows = []
        for row in table.find_all("tr"):
            cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
            rows.append(cells)
        tables.append(rows)
    
    return tables

#  Extract Text and Images from PDFs
def extract_pdf_content(file_bytes):
    text = ""
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    
    for page in pdf:
        text += page.get_text("text")  # Extract text
       # img_list = page.get_images(full=True)  # Extract images
    """
        for img_index, img in enumerate(img_list):
            xref = img[0]
            base_image = pdf.extract_image(xref)
            img_data = base_image["image"]
            images.append(img_data)  # Append image data as bytes
    """
    
    tables = extract_pdf_tables(file_bytes)  # Extract tables
    return {"text": text,  "tables": tables}

#  Extract Text and Tables from Word Docs
def extract_docx_content(file_bytes):
    text = docx2txt.process(io.BytesIO(file_bytes))
    tables = extract_docx_tables(file_bytes)
    return {"text": text, "images": [], "tables": tables}

#  Extract Text from Images
def extract_image_text(file_bytes):
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image)
    tables = extract_image_tables(file_bytes)
    return {"text": text, "tables": tables}


#  Extract Text and Tables from HTML
def extract_html_content(file_bytes):
    soup = BeautifulSoup(file_bytes.decode("utf-8"), "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    tables = extract_html_tables(file_bytes.decode("utf-8"))
    return {"text": text, "images": [], "tables": tables}

# LLM Processing Function
def process_with_llm(model_name, text, tables):
    """Send extracted content to the LLM and get an HTML form back."""
    
    prompt = f"""
You are given a form document. Your task is to **accurately convert** it into an **interactive HTML form** 
that visually and structurally resembles the original document as closely as possible.

### Rules:
1. **Retain all headings, labels, and sections** exactly as in the document.
2. **Tables must be formatted** with proper `<table>`, `<tr>`, and `<td>` elements, ensuring correct structure.
3. Ensure **tables are formatted correctly** with borders.
4. **Blank fields (for user input)** should be converted into `<input>` or `<textarea>` elements for tables and elsewhere as well.
5. **ALL TEXT in the document must be editable.**  
   - Use `<span contenteditable="true">` for every non-input text field.  
   - Example: `<h2 contenteditable="true">Title</h2>`
6. **Tables should be fully editable** - every `<td>` must have `contenteditable="true"`. 
7. **Even the text must be editable everywhere on the form.**
8. **Blank fields (for user input)** should be converted into `<input>` or `<textarea>` elements.
9. **Use CSS to match original formatting** such as bold text (`<b>`), underlines, and alignment.
10. **Ensure proper spacing** between sections, keeping the logical flow.
11. **Ensure that no matter what the file format is, they need to be rendered in html with similar care**
12. **Ensure that you do not fill any part of the form with any data.**
13. **Do not insert placeholder text or sample data.** Leave all fields empty.
14. **Ensure all sections, including signature and remarks, are also editable.**
15. **Ensure that the form is fully editable by the user.**
16. **Even pre-filled sections should be editable**.
17. - All `<input>`, `<textarea>`, and table cells are editable.
    - No fields are set to `readonly` or `disabled`.
    - The form structure allows users to input data without restrictions.

### Extracted Content:
**Text:**
{text}

**Tables:**
{tables}

Generate a **complete** HTML page that faithfully represents this form.
"""

    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    
    return response["message"]["content"]



# function for huggingface API
def process_with_huggingface(model_name, text, tables):
    """Send extracted content to a Hugging Face model for processing."""

    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}  # FIXED API KEY


    prompt = f"""
    You are given a form document. Convert it into an **interactive HTML form** 
    that visually and structurally resembles the original.

    ### Rules:
    - Keep **headings, labels, and sections** intact.
    - Convert **blank fields into `<input>` or `<textarea>` elements**.
    - Ensure **tables are formatted correctly** with borders.
    - Use **CSS styling** for spacing and alignment.

    ### Extracted Content:
    **Text:**
    {text}

    **Tables:**
    {tables}

    Generate a **full HTML page** preserving the form's structure.
    """

    payload = {"inputs": prompt}
    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["generated_text"]
    else:
        return f"Error: {response.text}"
    

#  Fill Form with LLM ( ollama )    
    
def fill_form_with_llm(model_name, html_form, receipt_text):
    """Uses Ollama to fill the editable HTML form with receipt data."""
    
    prompt = f"""
You are an advanced AI assistant that fills expense reimbursement forms.  
Your task is to **accurately insert** the receipt data into the given **editable HTML form**.

### Instructions:
1. **Only insert relevant receipt data** in appropriate fields.
2. **Do not modify the HTML structure**.  
3. **Do not change existing labels or table structure**.
4. **Ensure numbers match correctly in amount fields**.
5. **Ensure the form remains fully editable** for review.

### Data:
- **HTML Form:**  
{html_form}

- **Receipt Text:**  
{receipt_text}

Now, fill in the missing fields and return the updated HTML.
"""
    logger.info(f"Prompt: {prompt}")

    # response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    try:
        response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
        logger.info(f"Response object: {response}")
        logger.info(f"Type of response: {type(response)}")

        # Validate response structure
        return response.get("message", {}).get("content", "Error: No content returned")

    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return f"Error: {str(e)}"


   




#  Fill Form with Hugging Face API
# GET THE API KEY

HF_API_KEY2 = os.getenv("HF_API_KEY2")

def fill_form_with_huggingface(model_name, html_form, receipt_text):
    """Uses Hugging Face API to fill the form with receipt data."""

    API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_KEY2}"}

    prompt = f"""
You are an AI assistant that fills expense reimbursement forms.  
Your task is to **accurately insert** the receipt data into the given **editable HTML form**.

### Instructions:
1. **Only insert relevant receipt data** in appropriate fields.
2. **Do not modify the HTML structure**.  
3. **Do not change existing labels or table structure**.
4. **Ensure numbers match correctly in amount fields**.
5. **Ensure the form remains fully editable** for review.

### Data:
- **HTML Form:**  
{html_form}

- **Receipt Text:**  
{receipt_text}

Now, fill in the missing fields and return the updated HTML.
"""

    payload = {"inputs": prompt, "parameters": {"return_full_text": False}}

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        return f"Error: {response.json()}"


    

#  FastAPI Route: Process File and Extract Content
@app.post("/process-file/")
async def process_file(file: UploadFile = File(...), 
                       model: str = Query("llama3.2:latest", description="Select an LLM model"),
                       llm_source: str = Query("ollama", description="Choose 'ollama' or 'huggingface'")):
    file_bytes = await file.read()
    mime_type = detect_file_type(file_bytes)
    logger.info(f"Processing file: {file.filename} ({mime_type})")
    logger.info(f"Selected model: {model}")

    if "pdf" in mime_type:
        content = extract_pdf_content(file_bytes)
    elif "wordprocessingml" in mime_type or "msword" in mime_type:
        content = extract_docx_content(file_bytes)
    elif mime_type.startswith("image/"):
        content = extract_image_text(file_bytes)
    elif "html" in mime_type:
        content = extract_html_content(file_bytes)
    else:
        return {"error": "Unsupported file type"}
    
    #  Convert image bytes to Base64 for JSON-safe encoding
    # encoded_images = [base64.b64encode(img).decode('utf-8') for img in content["images"]]
    
    # Send extracted content to the selected LLM to get json

    #llm_response = process_with_llm(model, content["text"], content["tables"])

    if llm_source == "ollama":
        html_form = process_with_llm(model, content["text"], content["tables"])
    else:
        html_form = process_with_huggingface(model, content["text"], content["tables"])

    # Send extracted content to the selected LLM for HTML generation
    # html_form = process_with_llm(model, content["text"], content["tables"])

    return {"filename": file.filename, "html_form": html_form}  

"""
    return {
        "filename": file.filename,
        "text": content["text"],
        "tables": content["tables"],  # Now returning extracted tables
       # "images": encoded_images  # Now returning encoded images
    }"
"""




# FastAPI Route: Fill Form with Receipts
@app.post("/fill-form/")
async def fill_form_with_receipts(
    request: Request,
    html_form: str = Form(...),  # The already generated editable HTML form
    receipt_files: List[UploadFile] = File(...),  # List of receipts
    model_name: str = Form("llama3.2:latest"),  # Selected model
    llm_source: str = Form("ollama")  # Ollama or Hugging Face
):
    """Receives the editable HTML form + receipts and fills the form with receipt data."""

    logger.info(f"Received {len(receipt_files)} receipt files")
    logger.info(f"Selected model: {model_name} (Source: {llm_source})")
    logger.info(f"HTML Form: {html_form}")
    
    receipt_texts = []
    
    # Extract text from each receipt
    for receipt_file in receipt_files:
        receipt_bytes = await receipt_file.read()
        mime_type = detect_file_type(receipt_bytes)
        
        if "pdf" in mime_type:
            receipt_text = extract_pdf_content(receipt_bytes)["text"]
        elif "wordprocessingml" in mime_type or "msword" in mime_type:
            receipt_text = extract_docx_content(receipt_bytes)["text"]
        elif mime_type.startswith("image/"):
            receipt_text = extract_image_text(receipt_bytes)["text"]
        else:
            return {"error": f"Unsupported file type: {receipt_file.filename}"}
        
        receipt_texts.append(receipt_text)
    
    # Combine all extracted receipt data
    combined_receipt_text = "\n".join(receipt_texts)

    # Process with LLM (Choose between Ollama and Hugging Face)
    if llm_source == "ollama":
        filled_html = fill_form_with_llm(model_name, html_form, combined_receipt_text)
    else:
        filled_html = fill_form_with_huggingface(model_name, html_form, combined_receipt_text)

    return {"message": "Form filled successfully", "filled_html_form": filled_html}

