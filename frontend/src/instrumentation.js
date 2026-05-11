import { LangfuseWeb } from "langfuse";

// Note: LangfuseWeb is the specialized SDK for browser environments.
// It handles batching, retries, and browser-specific metadata automatically.

const langfuse = new LangfuseWeb({
  publicKey: import.meta.env.VITE_LANGFUSE_PUBLIC_KEY,
  baseUrl: import.meta.env.VITE_LANGFUSE_HOST || "https://cloud.langfuse.com",
});

// We can export this instance to use it for manual tracing if needed.
export default langfuse;

console.log("Langfuse Web SDK initialized");
