import React, { useState } from "react";

function App() {
  // State to store the form and receipt files
  const [formFile, setFormFile] = useState(null);
  const [receiptFiles, setReceiptFiles] = useState([]) ;//stores multiple files

  // State to show a success/failure message after file upload
  const [message, setMessage] = useState("");

  //for llm model selection
  const [selectedModel, setSelectedModel] = useState("mistral"); // Default Model

  // Available models
  const models = ["llama3-gradient:8b",
"llama2:7b",
"llama2-uncensored:latest",
"llama3-gradient:1048k",
"qwen:0.5b",
"qwen2:0.5b",
"qwen2:1.5b",
"llama3.2:1b",
"llama2:latest",
"llama2:13b",
"deepseek-v2:latest",
"llama3-chatqa:latest",
"deepseek-r1:7b",
"qwen2.5:1.5b",
"deepseek-r1:1.5b",
"qwen2.5:0.5b",
"qwen:4b",
"qwen:1.8b",
"mistral-small:24b",
"codestral:latest",
"mistral-small:22b",
"mistral-nemo:latest",
"dolphin-mistral:latest",
"samantha-mistral:latest",
"mistral:latest",
"mistrallite:latest",
"phi:latest",
"qwen2.5:14b",
"qwen:14b",
"qwen2.5:7b",
"qwen2.5:latest",
"qwen2:7b",
"qwen:7b",
"deepseek-r1:14b",
"deepseek-r1:8b",
"llama3.1:latest",
"llama3:latest",
"llama3.2:latest"
]

  // Handles when the form file is uploaded. 
  const handleFormFileChange = (event) => {
    setFormFile(event.target.files[0]);
    setMessage(""); // Clear previous messages
  };

  // Handles when the multiple receipt files are uploaded
  const handleReceiptFilesChange = (event) => {
    const filesArray = 
    Array.from(event.target.files); // convert filelost to an array
    setReceiptFiles(filesArray); //store multiple reciepts
    setMessage(""); // Clear previous messages
  };

  // Handles file upload to the FastAPI backend
  const handleUpload = async () => {
    if (!formFile || receiptFiles.length === 0) {
      setMessage("Please upload both the form and atleast one receipt!");
      return;
    }

    // Creating a FormData object to send both files
    const formData = new FormData();
    formData.append("form_file", formFile);
    //formData.append("receipt_file", receiptFile);
    receiptFiles.forEach((file) =>
    formData.append("receipt_files",file));

    try {
      // Sending a POST request to the FastAPI backend
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      // Parsing the response from the backend
      const data = await response.json();
      setMessage(data.message); // Display success message from the server
    } catch (error) {
      setMessage("Upload failed! Please try again.");
    }
  };

  
  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>File Uploader</h2>

      {/* Form Upload */}
      <p>Upload Form:</p>
      <input type="file" onChange={handleFormFileChange} />

      {/* Multiple Receipts Upload */}
      <p>Upload Receipts:</p>
      <input type="file" multiple onChange={handleReceiptFilesChange} />  {/* ✅ Allows multiple file selection */}

      {/* Model Selection Dropdown.  */}
      {/* Will make this selection more dynamic. */}
      <p>Select AI Model:</p>
      <select onChange={(e) => setSelectedModel(e.target.value)} value={selectedModel}>
        {models.map((model, index) => (
          <option key = {index} value = {model}>
            {model}
          </option>
        ))}
        {/*<option value="mistral">Mistral</option>
        <option value="llama3-gradient:8b">LLaMA 3 Gradient (8B)</option>
        <option value="llama2:7b">LLaMA 2 (7B)</option>
        <option value="deepseek-v2:latest">DeepSeek V2 (Latest)</option> */}
      </select>

      {/* Display selected files */}
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

      {/* Upload Button */}
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
        Upload Files
      </button>

      {/* Show success or failure messages */}
      {message && <p style={{ marginTop: "10px", fontWeight: "bold" }}>{message}</p>}
    </div>
);
}

export default App;