import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
  return (
    <main>
      <p className="eyebrow">Infrastructure change intelligence</p>
      <h1>ClusterMind</h1>
      <p>Understand Terraform changes before they happen.</p>
      <span className="status">Milestone 0 · Foundation ready</span>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
