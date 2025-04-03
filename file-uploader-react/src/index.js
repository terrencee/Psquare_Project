import React from "react";
//import ReactDOM from "react-dom";
import ReactDOM from "react-dom/client"; //  Use createRoot for React 18
import { BrowserRouter } from "react-router-dom";  // Import BrowserRouter
import "./index.css";
import App from "./App";
import { useRef } from "react";

console.log("1003", useRef);


const root = ReactDOM.createRoot(document.getElementById("root")); //  Create root


root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);


