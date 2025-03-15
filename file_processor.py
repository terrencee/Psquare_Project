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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
}

# Directories
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# OCR Reader
reader = easyocr.Reader(["en"])

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
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            pix = page.get_pixmap()
            extracted_text = reader.readtext(pix.tobytes(), detail=0)
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

    *Instruction for Extracting Reimbursement Data:*

    You are provided with an expense reimbursement form in PDF format. Your task is to *extract only the relevant details* from the form and present them in a structured format. *Do not include any additional text or explanations.*  

    Follow these rules strictly:  
    - Extract only the relevant fields from the document.  
    - If a field is missing or not applicable, write *N/A*.  
    - For numerical fields requiring summation across multiple entries, missing values should be treated as *0*.  
    - Maintain the exact structure and format in your output.  

    Return the extracted data *exactly* in the format of the form provided.
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

    *Instruction for Updating the Reimbursement Form:*

    Your task is to update the existing filled form by adding the details from the new bill. Follow these rules strictly:
    - Only update the fields that pertain to the new bill.
    - If a field is missing or not applicable, write *N/A*.
    - For numerical fields, sum the values across bills (treat missing values as *0*).
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

        1. *LaTeX Formatting Instructions*:
            - {latex_instructions}
            - Ensure that all formatting requirements are strictly followed.
            - Maintain all LaTeX commands, environments, and structures as instructed.

        2. *Source LaTeX Template*:
            - {latex_template}
            - Ensure that the content is inserted into the appropriate sections of the template without altering its structure.

        3. *Filled Reimbursement Text*:
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

def open_latex_editor(latex_filepath):
    """Compiles the LaTeX file into PDF and opens it for interactive editing."""
    logging.info(f"Opening LaTeX document for editing: {latex_filepath}")
    try:
        # Compile the LaTeX file using latexmk with PDF output.
        subprocess.run(["latexmk", "-pdf", latex_filepath], check=True)
        
        system_name = platform.system()
        if system_name == 'Windows':
            # Use os.startfile to open the file on Windows without subprocess
            os.startfile(latex_filepath)
        elif system_name == 'Darwin':  # macOS
            subprocess.run(["open", latex_filepath], check=True)
        else:  # Linux or similar
            subprocess.run(["xdg-open", latex_filepath], check=True)
        
        logging.info("LaTeX document opened for editing.")
    except Exception as e:
        logging.error(f"Error opening LaTeX document: {e}")


def save_to_file(filename, content):
    """Saves content to a file."""
    with open(filename, "w") as f:
        f.write(content)
    logging.info(f"Saved content to {filename}")

def process_reimbursement_form(form_path, receipt_paths, model_name="mistral"):
    """
    Processes a reimbursement form and multiple receipts using AI.
    Args:
        form_path (str): Path to the form PDF.
        receipt_paths (list): List of paths to receipt PDFs.
        model_name (str): The AI model to use.
    Returns:
        str: URL of the generated PDF.
    """

    # Extract text from form
    form_text = get_pdf_text(form_path)

    # Extract text from multiple receipts
    receipts_text = "\n\n".join(get_pdf_text(receipt) for receipt in receipt_paths)

    # AI Processing
    filled_form = update_filled_form_initial(form_text, receipts_text, model_name)

    # Convert to LaTeX
    latex_content = convert_to_latex(filled_form, "Reimbursement_Form_Template.txt", "LaTeX_Formatting_Instructions.txt", model_name)
    latex_path = os.path.join(OUTPUT_FOLDER, "Filled_Reimbursement_Form.tex")

    with open(latex_path, "w", encoding="utf-8") as latex_file:
        latex_file.write(latex_content)

    # Step 1 : open LaTex editor for manual review
    open_latex_editor(latex_path)

    # Step 2 : Convert LaTeX to PDF after manual review
    pdf_url = compile_latex_to_pdf(latex_path)

    return pdf_url

def compile_latex_to_pdf(latex_filepath):
    """Compiles the LaTeX document to PDF using an online API."""
    try:
        with open(latex_filepath, "r", encoding="utf-8") as file:
            latex_content = file.read()
        response = requests.post("https://latexonline.cc/compile", data={"source": latex_content})
        if response.status_code == 200:
            pdf_output_path = os.path.join(OUTPUT_FOLDER, "Filled_Reimbursement_Form.pdf")
            with open(pdf_output_path, "wb") as pdf_file:
                pdf_file.write(response.content)
            return f"http://localhost:8000/download/Filled_Reimbursement_Form.pdf"
        return None
    except Exception as e:
        logging.error(f"Error compiling LaTeX online: {e}")
        return None