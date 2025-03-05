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

    Return the extracted data **exactly** in the format of the form provided.
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
        if not os.path.exists(reimbursement_pdf):
            logging.error("Reimbursement form PDF not found!")
        else:
            break

    num_bills = int(input("Enter the number of bill PDFs: ").strip())
    bill_pdfs = []
    for i in range(num_bills):
        while True:
            bill_file = input(f"Enter bill PDF filename #{i + 1}: ").strip()
            if not os.path.exists(bill_file):
                logging.error(f"Bill PDF {bill_file} not found!")
            else:
                break
        bill_pdfs.append(bill_file)
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
def compile_latex_to_pdf(latex_filepath):
    """Compiles the LaTeX document to PDF using the LaTeX Online API."""
    try:
        with open(latex_filepath, "r", encoding="utf-8") as file:
            latex_content = file.read()
        url = "https://latexonline.cc/compile"
        params = {
            "format": "pdf",
            "code": latex_content
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            pdf_output_path = Path(latex_filepath).with_suffix(".pdf")
            with open(pdf_output_path, "wb") as f:
                f.write(response.content)
            logging.info(f"PDF generated successfully: {pdf_output_path}")
        else:
            logging.error(f"Error compiling LaTeX online: {response.status_code}")
    except Exception as e:
        logging.error(f"Error compiling LaTeX online using API: {e}")

def save_to_file(filename, content):
    """Saves content to a file."""
    with open(filename, "w") as f:
        f.write(content)
    logging.info(f"Saved content to {filename}")

def main():
    # Display available models
    for num, model in AVAILABLE_MODELS.items():
        print(f"{num}. {model}")
    while True:
        selected_model_num = int(input("Enter the model number to use: ").strip())
        if selected_model_num in AVAILABLE_MODELS:
            break
    model_name = AVAILABLE_MODELS.get(selected_model_num)
    if not model_name:
        logging.error("Invalid model number selected.")
        return
    logging.info(f"Selected model: {model_name}")

    # Step 1: Get file inputs
    reimbursement_pdf, bill_pdfs = prompt_for_files()
    if not reimbursement_pdf or not bill_pdfs:
        return

    # Step 2: Extract text from reimbursement form
    reimbursement_text = get_pdf_text(reimbursement_pdf)
    if not reimbursement_text:
        logging.error("Failed to extract text from reimbursement form.")
        return

    # Step 3: Process bills iteratively
    logging.info("Processing the first bill...")
    first_bill_text = get_pdf_text(bill_pdfs[0])
    filled_form = update_filled_form_initial(reimbursement_text, first_bill_text, model_name)

    # Process remaining bills one by one, updating the filled form each time
    for bill_file in bill_pdfs[1:]:
        logging.info(f"Processing subsequent bill: {bill_file}")
        new_bill_text = get_pdf_text(bill_file)
        filled_form = update_filled_form_iterative(filled_form, new_bill_text, model_name)

    # Step 4: Convert the final filled form to LaTeX
    logging.info("Converting filled form to LaTeX...")
    latex_code = convert_to_latex(filled_form, "Reimbursement_Form_Template.txt", "LaTeX_Formatting_Instructions.txt", model_name)
    latex_filename = "D:\Making LLMs fill Reimbursement form\Filled_Reimbursement_Form.tex"
    save_to_file(latex_filename, latex_code)

    # Step 5: Open LaTeX editor for review and interactive editing
    open_latex_editor(latex_filename)

    # Step 6: Compile LaTeX to PDF using the online API
    compile_latex_to_pdf(latex_filename)
    logging.info("Process completed successfully.")

if __name__ == "__main__":
    main()
