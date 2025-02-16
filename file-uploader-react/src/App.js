import React, { useState } from "react";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileType, setFileType] = useState("");
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setFileType("");
      setError("");
    }
  };

  const handleTypeSelection = (type) => {
    if (!selectedFile) {
      setError("Please upload a file first.");
      return;
    }

    const fileExtension = selectedFile.name.split(".").pop().toLowerCase();
    if (fileExtension !== type) {
      setError("Error: File format does not match the selected type!");
      return;
    }

    setFileType(type);
    setError("");
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>File Uploader</h2>
      <input type="file" onChange={handleFileChange} />
      
      {selectedFile && (
        <div style={{ marginTop: "20px" }}>
          <p><strong>Selected File:</strong> {selectedFile.name}</p>
          <p><strong>Size:</strong> {(selectedFile.size / 1024).toFixed(2)} KB</p>
          <p><strong>Detected Type:</strong> {selectedFile.name.split('.').pop().toUpperCase()}</p>

          <h4>Select File Type:</h4>
          <div style={{ display: "flex", justifyContent: "center", gap: "10px", flexWrap: "wrap" }}>
            {["jpg", "png", "pdf", "docx", "txt", "webp"].map((type) => (
              <button
                key={type}
                onClick={() => handleTypeSelection(type)}
                style={{
                  padding: "10px",
                  cursor: "pointer",
                  backgroundColor: fileType === type ? "green" : "lightgray",
                  border: "none",
                  borderRadius: "5px",
                }}
              >
                {type.toUpperCase()}
              </button>
            ))}
          </div>

          {fileType && <p style={{ marginTop: "10px" }}><strong>Selected Type:</strong> {fileType.toUpperCase()}</p>}
          {error && <p style={{ color: "red", fontWeight: "bold", marginTop: "10px" }}>{error}</p>}
        </div>
      )}
    </div>
  );
}

export default App;
