import React, { useState, useEffect } from "react";
import html2pdf from "html2pdf.js";
//import PreviewPage from "./PreviewPage"; // Import the PreviewPage component
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import PreviewPage from "./Preview"; // Make sure you have a Preview component
import ReactDOM from "react-dom/client"; // Ensure correct import
import { BrowserRouter } from "react-router-dom";

const App = () => {

  const [receipts, setReceipts] = useState([]);
  const [formData, setFormData] = useState({}); // Holds the form data
  const [textData, setTextData] = useState([]); // Holds extracted text from the form
const [tables, setTables] = useState([]); // Holds extracted tables from the form
const [lastHtmlData, setLastHtmlData] = useState(""); // Holds the latest HTML form
const navigate = useNavigate();



  // State for storing form and receipts
  const [formFile, setFormFile] = useState(null);
  const [receiptFiles, setReceiptFiles] = useState([]);

  // State for displaying upload success/failure messages
  const [message, setMessage] = useState("");

  // State for LLM model selection
  const [selectedModel, setSelectedModel] = useState("mistral");

  // state for llm source
  const [selectedLLMSource, setSelectedLLMSource] = useState("ollama");

  // State for storing the final generated PDF URL
  const [pdfUrl, setPdfUrl] = useState("");

  const [extractedText, setExtractedText] = useState("");

  // Available models
  const models = [
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
  ];

  // Handles Form File selection
  const handleFormFileChange = (event) => {
    setFormFile(event.target.files[0]);
    console.log("Form File:", event.target.files[0]); // Log selected file
    setMessage(""); // Clear previous messages
  };

  // Handles Receipt Files selection (multiple files)
  const handleReceiptFilesChange = (event) => {
    const filesArray = Array.from(event.target.files);
    setReceiptFiles(filesArray);
    setMessage(""); // Clear previous messages
  };


  //let lastHtmlData = null;  // Temporary storage for the latest HTML form

  let previewWindow = null; 

  //handles preview of blank gui
  const handlePreview = async (event) => {
    //const formFile = event.target.files?.[0]; // Ensure file is selected
    if (!formFile) {
        console.error("No file selected");
        return;
    }

    const formData = new FormData();
    formData.append("file", formFile);

    console.log("223", formData.get("file")); // Log FormData object
    // Get selected model and LLM source
    //const model = selectedModel;  // Example: "llama3.2:latest"
    //const llmSource = selectedLLMSource;  // Example: "ollama" or "huggingface"

    //console.log("221", model, llmSource); // Log selected model and LLM source
    //console.log("222", formData); // Log FormData object

    try {
     /* const response = await fetch(`http://localhost:8000/process-file/?model=${model}&llm_source=${llmSource}`,
            { method: "POST", 
              body: formData }
        );*/
        const response = await fetch("http://localhost:8000/preview-form/",
          { method: "POST", 
            body: formData }
      );
        console.log("Response:", response);  //  Log the response object

        if (!response.ok) {
          console.error("Error from API:", await response.text());
          return;
        }
        
        const responseData = await response.json();  //  Convert to JSON first
        console.log("Response Data:", responseData.html_form);  //  Log the response json data

        if (responseData.html_form) {
          // Save extracted HTML in localStorage
          localStorage.setItem("previewFormHtml", responseData.html_form);
          console.log("Saved HTML to localStorage:", localStorage.getItem("previewFormHtml"));

          // Open preview page in a new tab
          previewWindow = window.open("/preview", "_blank");
          if (!previewWindow) {
            alert("Popup blocked! Please allow popups for this site.");
          }
          //window.open("/preview", "_blank");
        } else {
          alert("Error extracting HTML data");
      }
      
    } catch (error) {
        console.error("Error:", error);
    }
};




  // Handles file upload to the FastAPI backend
  const handleUpload = async () => {
   /* if (!lastHtmlData || receiptFiles.length === 0) {
      console.error("lastHtmlData:", lastHtmlData, "receiptFiles length:", receiptFiles.length);
      setMessage("Please upload both the form and at least one receipt!");
      return;
    } */
      if (receiptFiles.length === 0) {
        console.error( "receiptFiles length:", receiptFiles.length);
        setMessage("Please upload at least one receipt!");
        return;
      }

      // Get the last stored HTML form
  const lastHtmlData = localStorage.getItem("previewFormHtml"); // Ensure it's stored in localStorage somewhere
  if (!lastHtmlData) {
    setMessage("No form data available!");
    return;
  }
  console.log("Last HTML Data:", lastHtmlData); // Log the last HTML data

    // Convert HTML string into a Blob and create a File object
    //const htmlBlob = new Blob([lastHtmlData], { type: "text/html" });
    //const htmlFile = new File([htmlBlob], "form.html", { type: "text/html" });

    // Creating a FormData object

    const formData = new FormData();
    formData.append("html_form", lastHtmlData); // Send form as a string
    receiptFiles.forEach((file) => formData.append("receipt_files", file));
    formData.append("model_name", selectedModel);
    formData.append("llm_source", selectedLLMSource);
    // log the form data
    console.log("Form Data:", formData.get("html_form"), formData.get("receipt_files"), formData.get("llm_source"), formData.get("model_name")); 
    
    

    try {
      // Sending a POST request to FastAPI backend
      const response = await fetch("http://localhost:8000/fill-form", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to process receipt");
      }

      // Parsing the response
      const data = await response.json();
      console.log("Backend response:", data); // Log backend response

      // Instead of storing extracted fields, store the filled form
    const filledHtml = data.filled_html_form;
    console.log("filled form :", filledHtml)
    localStorage.setItem("previewFormHtml", filledHtml);

    // If preview window is not open, open it
    if (!previewWindow || previewWindow.closed) {
      previewWindow = window.open("/preview", "_blank");
  } else {
      // If open, send message to reload
      previewWindow.postMessage({ type: "RELOAD_FORM" }, window.origin);
      // Send message after a slight delay to ensure the window is ready
    setTimeout(() => {
      previewWindow.postMessage({ filledHtml }, window.origin);
  }, 500);
  }
      
    } catch (error) {
      console.error("Upload failed:", error);
      setMessage("Upload failed! Please try again.");
    }
  };

  /////////////////////////////////////////////

  const generateEditableGUI = async (formPath) => {
    const response = await fetch("http://localhost:8000/generate-editable-gui", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ form_path: formPath }),
    });

    const data = await response.json();
    setFormData(data);
    setTables(data.tables);
  };

  const handleDownload = async () => {
    const response = await fetch("http://localhost:8000/save-latex", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    const data = await response.json();
    if (data.pdf_url) {
      window.open(`http://localhost:8000${data.pdf_url}`, "_blank");
    }
  };

  return (

  
    <Routes>
      {/* Main page where uploads are made */}
      <Route path="/" element={

    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>Form Processor</h2>

      {/* Form Upload */}
      <p>Upload Form:</p>
      <input type="file" onChange={handleFormFileChange} />

      {/*<p>Select Your Preferred Model:</p>
      <select onChange={(e) => setSelectedModel(e.target.value)} value={selectedModel}>
        {models.map((model, index) => (
          <option key={index} value={model}>
            {model}
          </option>
        ))}
      </select>

      <p>Select Your LLM Source for form preview:</p>
      <select onChange={(e) => setSelectedLLMSource(e.target.value)} value={selectedLLMSource}>
      <option value="ollama">Local : Ollama</option>
      <option value="huggingFace">Hugging Face</option>
      </select>*/}

      <button 
        onClick={handlePreview}
        style={{
          marginTop: "15px",
          padding: "10px",
          backgroundColor: "orange",
          color: "white",
          cursor: "pointer",
          border: "none",
          borderRadius: "5px",
          marginLeft: "10px"
        }}
      >
        Preview Form
      </button>

      {/* Multiple Receipts Upload */}
      <p>Upload The Assisting Receipts:</p>
      <input type="file" multiple onChange={handleReceiptFilesChange} />

      {/* Model Selection Dropdown */}
      <p>Select Your Preferred Model:</p>
      <select onChange={(e) => setSelectedModel(e.target.value)} value={selectedModel}>
        {models.map((model, index) => (
          <option key={index} value={model}>
            {model}
          </option>
        ))}
      </select>

      <p>Select Your LLM Source for Form Fillup:</p>
      <select onChange={(e) => setSelectedLLMSource(e.target.value)} value={selectedLLMSource}>
      <option value="ollama">Local : Ollama</option>
      <option value="huggingFace">Hugging Face</option>
      </select>

      {/* Display Selected Files */}
      {formFile && <p><strong>Form Selected:</strong> {formFile.name}</p>}
      {receiptFiles.length > 0 && (
        <div>
          <strong>Receipts Selected:</strong>
          <ul>
            {receiptFiles.map((file, index) => (
              <li key={index}>{file.name}</li>
            ))}
          </ul>
        </div>
      )}
      <button 
      onClick={handleUpload}
      style={{
        marginTop: "15px",
        padding: "10px",
        backgroundColor: "blue",
        color: "white",
        cursor: "pointer",
        border: "none",
        borderRadius: "5px",
      }}
        >
            Upload and Generate Form
        </button>

      <table>
        <tbody>
          {tables.map((row, index) => (
            <tr key={index}>
              {row.map((cell, i) => (
                <td key={i} contentEditable>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Show Upload Status Message */}
      {message && <p style={{ color: "red", marginTop: "10px" }}>{message}</p>}

    </div>
      }  // End of Route path="/" element
      /> {/* End of Route */}

      {/* Preview Page Route */}
      <Route path="/preview" element={<PreviewPage />}  // Pass the extracted fields to the preview page
      />

      </Routes>
  
  );
};

export default App;
