# Langfuse Integration Guide & Documentation

Dokumentasi ini dirangkum dari sumber resmi Langfuse untuk membantu implementasi **Phase 7.5: Implement Langfuse Web Analytics** dan pemantauan **LangGraph Workflow** di sisi backend.

---

## 1. Persiapan (Prerequisites)

Sebelum melakukan coding, pastikan kredensial berikut sudah siap di file `.env`:

```bash
# Ambil dari Settings > API Keys di Dashboard Langfuse
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com" # Host default (EU)
```

---

## 2. Integrasi Backend (LangGraph & LangChain)

Karena inti proyek ini adalah LangGraph, integrasi menggunakan `CallbackHandler` adalah cara yang paling efisien secara profesional.

### Instalasi (Python)
```bash
pip install langfuse langchain langgraph
```

### Implementasi pada LangGraph Node
Gunakan `CallbackHandler` saat melakukan `invoke` pada graph.

```python
from langfuse.langchain import CallbackHandler
from src.graph.workflow import app # Asumsi lokasi graph Anda

# Inisialisasi Handler
langfuse_handler = CallbackHandler()

# Jalankan Graph dengan tracing
# Pastikan thread_id atau session_id disertakan untuk pelacakan percakapan
inputs = {"messages": [("user", "Bagaimana cara melakukan onboarding?")]}
config = {
    "configurable": {"thread_id": "user-session-123"},
    "callbacks": [langfuse_handler],
    "metadata": {
        "langfuse_user_id": "employee-id-001",
        "langfuse_session_id": "session-unique-id"
    }
}

response = app.invoke(inputs, config=config)
```

---

## 3. Integrasi Frontend (Web Analytics)

Untuk memenuhi **Task 7.5**, Anda perlu melacak interaksi user di sisi React/Vite.

### Instalasi (NPM/Yarn)
```bash
npm install @langfuse/tracing @langfuse/otel @opentelemetry/sdk-node
```

### Inisialisasi Instrumentation (Vite/React)
Buat file `src/instrumentation.ts`:

```typescript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { LangfuseSpanProcessor } from "@langfuse/otel";

export const sdk = new NodeSDK({
  spanProcessors: [new LangfuseSpanProcessor()],
});

sdk.start();
```

### Melacak Event di Chat Interface
```typescript
import { startActiveObservation } from "@langfuse/tracing";

async function sendMessage(text: string) {
  // Mulai observasi untuk satu interaksi chat
  await startActiveObservation("user-chat-interaction", async (span) => {
    span.update({
      input: text,
      metadata: { component: "ChatBox" }
    });
    
    // Logika pengiriman pesan ke backend Anda...
    const response = await api.chat(text);
    
    span.update({ output: response });
  });
}
```

---

## 4. Professional Best Practices (Professional Standard)

| Kategori | Best Practice | Rationale |
|---|---|---|
| **Privacy** | Masking PII (Data Pribadi) | Jangan mengirim nama asli atau info sensitif ke cloud analytics tanpa enkripsi/masking. |
| **Hierarchy** | Nested Spans | Gunakan span bersarang untuk setiap langkah agent (Planner -> Explainer -> Assessor) agar terlihat langkah mana yang lambat. |
| **Cost** | Token Usage | Langfuse otomatis menghitung biaya jika model name dikirim dengan benar. |
| **Feedback** | User Scores | Gunakan `langfuse.score()` untuk menangkap jempol (thumbs up/down) dari user guna mengevaluasi kualitas jawaban AI. |
| **Async** | Shutdown/Flush | Di lingkungan serverless atau script singkat, selalu panggil `langfuse.flush()` sebelum proses berhenti agar data tidak hilang. |

---

## 5. Dokumentasi Referensi (Local)

Daftar file mentah yang berhasil diunduh via terminal:
- `docs/web_sdk.mdx`
- `docs/langchain_python.mdx`
- `temp_langfuse_skills/skills/langfuse/references/instrumentation.md`

> [!TIP]
> Anda dapat melihat detail teknis lebih dalam di file-file di atas jika diperlukan konfigurasi spesifik seperti *Advanced Filtering* atau *Custom Metrics*.
