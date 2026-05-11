import { NodeSDK } from "@opentelemetry/sdk-node";
import { LangfuseSpanProcessor } from "@langfuse/otel";
import { Resource } from "@opentelemetry/resources";
import { SemanticResourceAttributes } from "@opentelemetry/semantic-conventions";

// Initializing the Langfuse Span Processor
// Note: In a real production app, these should come from environment variables.
// For Vite, we use import.meta.env.
export const langfuseSpanProcessor = new LangfuseSpanProcessor({
  publicKey: import.meta.env.VITE_LANGFUSE_PUBLIC_KEY,
  baseUrl: import.meta.env.VITE_LANGFUSE_HOST || "https://cloud.langfuse.com",
  exportMode: "immediate", // Recommended for serverless/web environments
  version: import.meta.env.VITE_APP_VERSION || "1.0.0",
});

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: "enterprise-ai-onboarding-frontend",
  }),
  spanProcessors: [langfuseSpanProcessor],
});

try {
  sdk.start();
  console.log("Langfuse OpenTelemetry SDK started");
} catch (error) {
  console.error("Error starting Langfuse OpenTelemetry SDK", error);
}
