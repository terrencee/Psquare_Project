import os
import logging
import subprocess
import platform
from pathlib import Path
from PyPDF2 import PdfReader
import fitz  # pymupdf
import easyocr
from ollama import chat
import requests
import pypandoc
from docx2pdf import convert

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the base directory where output files should be stored
BASE_DIR = r"D:\Making LLMs fill Reimbursement form"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Ensure the directory exists before using it
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Available models with more descriptive names
AVAILABLE_MODELS = {
    1: "llama3-gradient:8b",
    2: "llama2:7b",
    3: "llama2-uncensored:latest",
    4: "llama3-gradient:1048k",
    5: "qwen:0.5b",
    6: "qwen2:0.5b",
    7: "qwen2:1.5b",
    8: "llama3.2:1b",
    9: "llama2:latest",
    10: "llama2:13b",
    11: "deepseek-v2:latest",
    12: "llama3-chatqa:latest",
    13: "deepseek-r1:7b",
    14: "qwen2.5:1.5b",
    15: "deepseek-r1:1.5b",
    16: "qwen2.5:0.5b",
    17: "qwen:4b",
    18: "qwen:1.8b",
    19: "mistral-small:24b",
    20: "codestral:latest",
    21: "mistral-small:22b",
    22: "mistral-nemo:latest",
    23: "dolphin-mistral:latest",
    24: "samantha-mistral:latest",
    25: "mistral:latest",
    26: "mistrallite:latest",
    27: "phi:latest",
    28: "qwen2.5:14b",
    29: "qwen:14b",
    30: "qwen2.5:7b",
    31: "qwen2.5:latest",
    32: "qwen2:7b",
    33: "qwen:7b",
    34: "deepseek-r1:14b",
    35: "deepseek-r1:8b",
    36: "llama3.1:latest",
    37: "llama3:latest",
    38: "llama3.2:latest",
    39: "qwq"
}

def get_pdf_text(pdf_path):
    """Extracts text from a PDF. Uses OCR if normal extraction fails."""
    logging.info(f"Extracting text from PDF: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if text.strip():
            return text.strip()
        else:
            return perform_ocr_on_pdf(pdf_path)
    except Exception as e:
        logging.error(f"Error reading PDF {pdf_path}: {e}")
        return perform_ocr_on_pdf(pdf_path)

def perform_ocr_on_pdf(pdf_path):
    """Extracts text using OCR for scanned PDFs."""
    try:
        ocr_reader = easyocr.Reader(['en'])
        doc = fitz.open(pdf_path)
        text = ""
        for page_index in range(len(doc)):
            pix = doc[page_index].get_pixmap()
            extracted_text = ocr_reader.readtext(pix.tobytes(), detail=0)
            text += "\n".join(extracted_text) + "\n"
        return text.strip() if text else "[OCR Extraction Failed]"
    except Exception as e:
        logging.error(f"OCR processing error: {e}")
        return "[OCR Processing Failed]"

def update_filled_form_initial(form_text, bill_text, model_name):
    """
    Processes the reimbursement form and the first bill to produce the initial filled form.
    """
    query = f"""
    You are an AI trained to process reimbursement forms.
    Given the extracted reimbursement form:
    {form_text}

    And the parsed bill data:
    {bill_text}

    **Instruction for Extracting Reimbursement Data:**

    You are provided with an expense reimbursement form in PDF format. Your task is to **extract only the relevant details** from the form and present them in a structured format. **Do not include any additional text or explanations.**  

    Follow these rules strictly:  
    - Extract only the relevant fields from the document.  
    - If a field is missing or not applicable, write **N/A**.  
    - For numerical fields requiring summation across multiple entries, missing values should be treated as **0**.  
    - Maintain the exact structure and format in your output.  

    Return the extracted data **exactly** in the format of the form in {form_text} provided.
    """
    try:
        response = chat(
            model=model_name,
            messages=[{"role": "user", "content": query}]
        )
        return response['message']['content']
    except Exception as e:
        logging.error(f"Error processing initial filled form with AI: {e}")
        return "[AI Processing Failed]"

def update_filled_form_iterative(current_filled_form, new_bill_text, model_name):
    """
    Updates the already filled reimbursement form by adding the details from the new bill.
    """
    query = f"""
    You are an AI trained to update expense reimbursement forms.
    Given the current filled reimbursement form:
    {current_filled_form}

    And the parsed new bill data:
    {new_bill_text}

    **Instruction for Updating the Reimbursement Form:**

    Your task is to update the existing filled form by adding the details from the new bill. Follow these rules strictly:
    - Only update the fields that pertain to the new bill.
    - If a field is missing or not applicable, write **N/A**.
    - For numerical fields, sum the values across bills (treat missing values as **0**).
    - Maintain the exact structure and format in your output.

    Return only the updated filled form in the same format.
    """
    try:
        response = chat(
            model=model_name,
            messages=[{"role": "user", "content": query}]
        )
        return response['message']['content']
    except Exception as e:
        logging.error(f"Error updating filled form with AI: {e}")
        return "[AI Update Failed]"

def prompt_for_files():
    """Handles user input for reimbursement form and bills."""
    while True:
        reimbursement_pdf = input("Enter reimbursement form PDF filename: ").strip()
        if os.path.exists(reimbursement_pdf):
            break
        else:
            print("Reimbursement form PDF not found! Please enter a valid file path.")

    while True:
        num_bills = input("Enter the number of bill PDFs: ").strip()
        if num_bills.isdigit() and int(num_bills) > 0:
            num_bills = int(num_bills)
            break
        else:
            print("Please enter a valid positive integer for the number of bill PDFs.")

    bill_pdfs = []
    for i in range(num_bills):
        while True:
            bill_file = input(f"Enter bill PDF filename #{i + 1}: ").strip()
            if os.path.exists(bill_file):
                bill_pdfs.append(bill_file)
                break
            else:
                print(f"Bill PDF '{bill_file}' not found! Please enter a valid file path.")

    return reimbursement_pdf, bill_pdfs


def convert_to_latex(filled_data, template_file, instructions_file, model_name):
    """Converts the filled reimbursement data to LaTeX format."""
    try:
        with open(template_file, "r") as tpl_file:
            latex_template = tpl_file.read()
        with open(instructions_file, "r") as instr_file:
            latex_instructions = instr_file.read()

        query = f"""
        You are an advanced AI trained to convert plain text into LaTeX format for a reimbursement form.

        Your task is to take the provided filled reimbursement data and convert it into a well-structured LaTeX document.

        Follow these specific guidelines:

        1. **LaTeX Formatting Instructions**:
            - {latex_instructions}
            - Ensure that all formatting requirements are strictly followed.
            - Maintain all LaTeX commands, environments, and structures as instructed.

        2. **Source LaTeX Template**:
            - {latex_template}
            - Ensure that the content is inserted into the appropriate sections of the template without altering its structure.

        3. **Filled Reimbursement Text**:
            - {filled_data}
            - Convert the data in this text into a LaTeX format, ensuring that:
                - All fields from the reimbursement form are represented correctly.
                - Data is placed in the correct LaTeX environment (e.g., tables, sections).
                - The content should be presented in a way that adheres to the formatting conventions of the provided template.

        Return only the updated LaTeX code that directly reflects the changes made.
        """
        response = chat(
            model=model_name,
            messages=[{"role": "user", "content": query}]
        )
        return response['message']['content']
    except Exception as e:
        logging.error(f"Error converting to LaTeX: {e}")
        return "[LaTeX Conversion Failed]"

def save_to_file(filename, content):
    """Saves content to a file."""
    with open(filename, "w") as f:
        f.write(content)
    logging.info(f"Saved content to {filename}")

def ensure_pandoc():
    try:
        pypandoc.convert_text("test", "plain", format="md")
    except OSError:
        logging.info("Pandoc not found. Downloading Pandoc...")
        pypandoc.download_pandoc()

def convert_latex_to_docx(latex_file, docx_file):
    """
    Convert a LaTeX file to DOCX using pypandoc.
    """
    ensure_pandoc()
    try:
        pypandoc.convert_file(
            source_file=latex_file,
            to="docx",
            format="latex",  # <--- explicitly specify the format
            outputfile=docx_file,
            extra_args=["--standalone"]  # often helps produce a full .docx
        )

        logging.info(f"Conversion from LaTeX to DOCX successful! DOCX saved as {docx_file}")
    except Exception as e:
        logging.error("An error occurred during LaTeX to DOCX conversion:")
        logging.error(e)
        raise

def open_docx_editor(docx_file):
    """Opens the DOCX file using the system default application."""
    logging.info(f"Opening DOCX document for editing: {docx_file}")
    try:
        system_name = platform.system()
        if system_name == 'Windows':
            os.startfile(docx_file)
        elif system_name == 'Darwin':  # macOS
            subprocess.run(["open", docx_file], check=True)
        else:  # Linux or similar
            subprocess.run(["xdg-open", docx_file], check=True)
    except Exception as e:
        logging.error(f"Error opening DOCX document: {e}")

def convert_docx_to_pdf(docx_file, pdf_file):
    """
    Convert a DOCX file to PDF using docx2pdf.
    Note: On Windows/macOS, Microsoft Word must be installed.
    """
    if not os.path.exists(docx_file):
        logging.error(f"Input DOCX file '{docx_file}' not found!")
        return
    try:
        convert(docx_file, pdf_file)
        logging.info(f"Conversion from DOCX to PDF successful! PDF saved as {pdf_file}")
    except Exception as e:
        logging.error("An error occurred during DOCX to PDF conversion:")
        logging.error(e)
        raise

def process_reimbursement_form(form_path, receipt_paths, model_name):
    """
    Processes the reimbursement form and receipts, then generates a filled PDF.
    """
    # Extract text from the reimbursement form
    form_text = get_pdf_text(form_path)
    if not form_text:
        return None

    # Extract text from the first receipt
    first_receipt_text = get_pdf_text(receipt_paths[0])
    filled_form = update_filled_form_initial(form_text, first_receipt_text, model_name)

    # Process additional receipts iteratively
    for receipt_path in receipt_paths[1:]:
        receipt_text = get_pdf_text(receipt_path)
        filled_form = update_filled_form_iterative(filled_form, receipt_text, model_name)

    latex_filename = os.path.join(OUTPUT_DIR, "Filled_Reimbursement_Form.tex")
    docx_filename = os.path.join(OUTPUT_DIR, "Filled_Reimbursement_Form.docx")
    pdf_filename = os.path.join(OUTPUT_DIR, "Filled_Reimbursement_Form.pdf")


    # Convert to LaTeX
    latex_code = convert_to_latex(filled_form, "Reimbursement_Form_Template.txt", "LaTeX_Formatting_Instructions.txt", model_name)
    save_to_file(latex_filename, latex_code)

    # Convert LaTeX to DOCX and then to PDF
    convert_latex_to_docx(latex_filename, docx_filename)
    convert_docx_to_pdf(docx_filename, pdf_filename)

    return pdf_filename  # Return the final PDF path
