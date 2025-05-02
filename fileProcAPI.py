import base64
from fastapi import FastAPI, UploadFile, File, Query, Form, Request, HTTPException
from fastapi.responses import JSONResponse
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
import pandas as pd
import regex as re
from difflib import get_close_matches
from datetime import datetime
from bs4 import BeautifulSoup
import json



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
    #_, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

    # Find contours of table cells
    #contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 50 and h > 20:  # filter out noise
            boxes.append((x, y, w, h))

    # Sort boxes top to bottom, then left to right
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))

    rows = []
    current_row = []
    previous_y = -1

    for box in boxes:
        x, y, w, h = box
        roi = gray[y:y+h, x:x+w]
        text = pytesseract.image_to_string(roi, config='--psm 7').strip()

        if abs(y - previous_y) > 10:
            if current_row:
                rows.append(current_row)
            current_row = []

        current_row.append(text)
        previous_y = y

    if current_row:
        rows.append(current_row)

    return rows



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

# group text by lines and paras
def group_text_blocks(raw_text):
    lines = raw_text.split('\n')
    paragraphs = []
    current_paragraph = ""

    for line in lines:
        line = line.strip()
        if line:
            current_paragraph += " " + line
        else:
            if current_paragraph:
                paragraphs.append(current_paragraph.strip())
                current_paragraph = ""
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())

    return paragraphs



# function to inject json data into html form

def inject_data_into_form(original_html, extracted_data_json):
    soup = BeautifulSoup(original_html, "html.parser")
    extracted_data = json.loads(extracted_data_json)

    for name, value in extracted_data.items():
        if not value:
            continue  # Skip empty values
        
        # Find input fields
        input_element = soup.find("input", {"name": name})
        if input_element:
            input_element["value"] = value
            continue

        # Find textarea fields
        textarea_element = soup.find("textarea", {"name": name})
        if textarea_element:
            textarea_element.string = value

    return str(soup)



# generating preview without llm

def generate_html_form(text_blocks, tables):
    today = datetime.today().strftime('%Y-%m-%d')

    html = """
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
                background-color: #fdfdfd;
                color: #333;
            }
            .header {
                text-align: center;
                font-weight: bold;
                margin-bottom: 20px;
            }
            .flex-space-between {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
            }
            .left-align {
                text-align: left;
                margin-bottom: 5px;
                font-weight: bold;
            }
            .paragraph {
                margin-bottom: 20px;
                text-align: justify;
            }
            input[type="text"], input[type="date"], input[type="number"], textarea {
                border: none;
                border-bottom: 1px solid #333;
                background: transparent;
                font-size: 14px;
            }
            .signature-section {
                margin-top: 40px;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
            }
            .signature-line {
                margin-bottom: 8px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            table, th, td {
                border: 1px solid black;
            }
            th, td {
                padding: 10px;
                text-align: left;
                vertical-align: middle;
            }
            .add-row-btn, .remove-row-btn {
                margin: 4px;
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .add-row-btn {
                background-color: #4CAF50;
                color: white;
            }
            .remove-row-btn {
                background-color: #f44336;
                color: white;
            }
        </style>
    </head>
    <body>
    """

    # Department + Institute
    html += """
    <div class="header" contenteditable = "true">Department of Electrical Engineering</div>
    <div class="header" contenteditable = "true">Indian Institute of Technology Roorkee</div>
    """

    # Flex: Form Number + Date
    html += f"""
    <div class="flex-space-between">
        <div contenteditable = "true">No. EED / Reimbursement : <input type="text" /></div>
        <div contenteditable = "true">Dated: <input type="date" value="{today}" /></div>
    </div>
    """

    # Two lines under header left aligned
    html += """
    <div class="left-align" contenteditable = "true">Dean (F&P)/SRIC: <input type="text" /> </div>
    <div class="left-align" contenteditable = "true">IIT Roorkee</div>
    """

    # Function to replace blanks with inputs (for dotted lines, underscores, etc.)
    def replace_blanks(text):
        return re.sub(r'([_.:\-]{3,}|\\n)', '<input type="text" />', text)

    # Process paragraph (join text blocks into one big paragraph)
    full_paragraph = " ".join(text_blocks)
    processed_paragraph = replace_blanks(full_paragraph)

    html += f'<div class="paragraph" contenteditable = "true">{processed_paragraph}</div>'

    # Hardcoded Table (Already good, adding 10 rows initially)
    html += """
    <div style="overflow-x: auto;">
        <table id="cash-memo-table">
            <thead>
                <tr>
                    <th rowspan="2">S.N.</th>
                    <th colspan="2">Cash Memo</th>
                    <th rowspan="2">Name of the Firms</th>
                    <th rowspan="2">Amount</th>
                    <th rowspan="2">Actions</th>
                </tr>
                <tr>
                    <th>No.</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
    """

    for i in range(1, 11):
        html += f"""
            <tr>
                <td>{i}</td>
                <td><input type="text" name="cash_memo_no_{i}" /></td>
                <td><input type="date" name="cash_memo_date_{i}" value="{today}" /></td>
                <td><input type="text" name="firm_name_{i}" /></td>
                <td><input type="number" name="amount_{i}" step="0.01" /></td>
                <td><button type="button" class="remove-row-btn" onclick="removeRow(this)">Remove</button></td>
            </tr>
        """

    html += """
            </tbody>
        </table>
        <button type="button" class="add-row-btn" onclick="addRow()">Add Row</button>
    </div>
    """

    # Signature Section
    html += """
    <div class="signature-section">
        <div class="signature-line">Signature: <input type="text" /></div>
        <div class="signature-line">Name: <input type="text" /></div>
        <div class="signature-line">Designation: <input type="text" /></div>
        <div class="signature-line">Department of Electrical Engineering</div>
    </div>
    """

    # Add row/remove row JS
    html += """
    <script>
        function addRow() {
            const table = document.getElementById("cash-memo-table").getElementsByTagName('tbody')[0];
            const rowCount = table.rows.length + 1;
            const newRow = table.insertRow();

            newRow.innerHTML = `
                <td>${rowCount}</td>
                <td><input type="text" name="cash_memo_no_${rowCount}" /></td>
                <td><input type="date" name="cash_memo_date_${rowCount}" value="${new Date().toISOString().split('T')[0]}" /></td>
                <td><input type="text" name="firm_name_${rowCount}" /></td>
                <td><input type="number" name="amount_${rowCount}" step="0.01" /></td>
                <td><button type="button" class="remove-row-btn" onclick="removeRow(this)">Remove</button></td>
            `;
        }

        function removeRow(button) {
            const row = button.closest("tr");
            row.remove();
        }
    </script>
    """

    html += "</body></html>"

    return html







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
You are an AI assistant designed to fill HTML forms **without changing their structure**.
Your task is to **accurately insert the receipt data into the given editable HTML form**, especially focusing on table rows.

### Instructions:
1. **Only insert relevant receipt data** in appropriate fields.
2. **Do not modify the HTML structure**.  
3. **Do not modify, add or remove the HTML tags, text, attributes, or layout.**
4. **Do not change existing labels or table structure**.
5. **Ensure numbers match correctly in amount fields**.
6. **Ensure the form remains fully editable** for review.
7. **Only insert the extracted receipt data as values into existing form fields.**
8. **Preserve all class names, ids, and HTML attributes.**
9. - **Reiterating** : **Only** insert data into the `value` attributes of `<input>` or `<textarea>` fields.
    - Leave all other elements, tags, and structure exactly as they are.
    - If no matching receipt data exists for a field, **leave it empty**.
    - Preserve all `class`, `id`, and `name` attributes exactly as they are.
    - **Do not** generate new buttons, scripts, or styles.
    - **Do not** return any extra text, explanation, or formatting — **only return the modified HTML string.**
    - **No code fences**, no explanations.
10. **Do not hallucinate or guess fields. If unsure, leave them empty.**

### Important:
- **Do not generate new table rows** or signature sections.
- **Preserve dynamic buttons and scripts** (like "Add Row", "Remove Row").
- Work strictly inside the existing HTML template provided.
- Maintain any existing empty rows for future user inputs.
- The form structure is that it has 2 lines of headings,
    - followed by a next line of "No. EED / Reimbursement : <input type="text" />" and "Dated: <input type="date" value="current date" />"
    - then a line of "Dean (F&P)/SRIC: <input type="text" />" and "IIT Roorkee"
    - then a paragraph of text, followed by a table with 5 columns and 10 rows.
    - then a signature section with 4 lines of inputs.
    - The table has 5 columns: "S.N.", "Cash Memo No.", "Date", "Name of the Firms", and "Amount".
    - The table has a number rows, each with an "Add Row" button at the end.
- **This structure of the form must be absolutely maintained when returning the filled form**.
- The **keys and blanks filled with values** must be returned
- Change the **dates only in the table** based on dates in the cash memos/receipts.
- The **other elements of the form**, the **paragraphs and tables with borders intact** must also be returned.
- The form must be **fully editable**, meaning **all fields** should be **editable by the user**.

### Method:
- Update input fields like this: <input name="amount" value="123.45" />
- Update textarea fields by placing text between the tags: <textarea name="description">Taxi from airport</textarea>

### Data:
- **HTML Form ( DO NOT CHANGE STRUCTURE ):**  
{html_form}

- **Receipt Text:**  
{receipt_text}


### Output:
- Return only the updated HTML form, keeping the original structure intact.
- i.e Return the same HTML form with values filled in the appropriate input fields.
- Keep the borders of tables, paragraphs, heading present in the original form intact.
- Do not wrap your response in code fences.
- Do not add explanations or extra comments.


Now, proceed carefully and fill in the missing fields and return the updated HTML.
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

###############################

# fill form with llm - return json with only key val pairs of filled data. Then set them as values in the html form.


def fill_form_llm_json(model_name, html_form, receipt_text):
    """Uses Ollama to extract values and inject into original HTML form."""

    # Step 1: LLM Prompt to extract key-value pairs
    prompt = f"""
You are an AI assistant. Extract values from the receipt text and return them as JSON. Do not return HTML.
You are assisting in automatically filling out a financial reimbursement form using extracted receipt data.

### Instructions:
Task:
1. Fill all the table rows:
   - Cash Memo No.: Use receipt numbers.
   - Date: Use the corresponding date of each receipt.
   - Name of the Firm: Use the firm name from each receipt.
   - Amount: Use the amount from each receipt.

2. Fill form fields outside the table:
   - "No. EED / Reimbursement": Enter the total number of receipts.
   - In the paragraph above the table:
     - "____ no. of cash memo(s)": Enter the total number of receipts.
     - "for the total amount of Rs. ____": Enter the sum of all amounts.
     - "Dr. ____": Use the name from the receipts if available.

3. At the bottom of the form:
   - "Name": Use the name from the receipts if available.
   - "Designation": Use designation from the receipts, if available.

4. Notes:
- Keep the top-right date unchanged (current date).
- Do not fill the signature field.

Input Data:
[List of receipt numbers, dates, firm names, amounts, and any names/designations from the receipts.]

### Receipt Data:
{receipt_text}

Goal:
Accurately and intelligently fill out the form based on its layout and labels without needing to hardcode specific field names.


Output:
Fill the form fields accordingly.

Return ONLY the JSON. No code block, no extra explanation.

"""

    logger.info(f"Prompt: {prompt}")

    # Send to your LLM
    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    extracted_data = response['message']['content'].strip()

    logger.info(f"Extracted Data: {extracted_data}")

    # Step 2: Parse JSON response
    '''
    try:
        extracted_fields = json.loads(extracted_data)
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from LLM response")
        return html_form  # Return original form unchanged if error

    # Step 3: Inject values into original HTML form
    soup = BeautifulSoup(html_form, 'html.parser')

    # Fill <input> fields
    for input_tag in soup.find_all('input'):
        field_name = input_tag.get('name')
        if field_name and field_name in extracted_fields:
            input_tag['value'] = extracted_fields[field_name]

    # Fill <textarea> fields
    for textarea_tag in soup.find_all('textarea'):
        field_name = textarea_tag.get('name')
        if field_name and field_name in extracted_fields:
            textarea_tag.string = extracted_fields[field_name]

    # Step 4: Return updated HTML form as string
    return str(soup)

   '''




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


# api for preview without AI
@app.post("/preview-form/")
async def process_file(file: UploadFile = File(...)):
    try :
        file_bytes = await file.read()
        mime_type = detect_file_type(file_bytes)
        logger.info(f"Processing file: {file.filename} ({mime_type})")

        if "pdf" in mime_type:
            content = extract_pdf_content(file_bytes)
        elif "wordprocessingml" in mime_type or "msword" in mime_type:
            content = extract_docx_content(file_bytes)
        elif mime_type.startswith("image/"):
            content = extract_image_text(file_bytes)
        elif "html" in mime_type:
            content = extract_html_content(file_bytes)
        else:
            return JSONResponse(content={"error": "Unsupported file type"}, status_code=400)
        
        # Check extracted content
        if not content or "text" not in content or "tables" not in content:
            logger.error("Extraction failed or incomplete content")
            return JSONResponse(content={"error": "Extraction failed or incomplete content"}, status_code=500)
        
        grouped_text = group_text_blocks(content["text"])
        html_form = generate_html_form(grouped_text, content["tables"])

        logger.info(f"Generated HTML form: {html_form}")

        return {"filename": file.filename, "html_form": html_form}  
    except Exception as e :
        logger.exception("An error occurred while processing the file.")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    

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

    # Process with LLM (Choose between Ollama and Hugging Face) fill_form_llm_json
    if llm_source == "ollama":
        # filled_html = fill_form_with_llm(model_name, html_form, combined_receipt_text)
        filled_html = fill_form_llm_json(model_name, html_form, combined_receipt_text)
    else:
        filled_html = fill_form_with_huggingface(model_name, html_form, combined_receipt_text)

    return {"message": "Form filled successfully", "filled_html_form": filled_html}

