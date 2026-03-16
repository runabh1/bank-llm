# 🏦 BankAssist AI — Personalized LLM for Banks

> A **100% local, private, hallucination-free** AI assistant that answers bank staff queries from internal circulars and regulatory documents.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **RAG Architecture** | Answers grounded purely in retrieved documents — no hallucination |
| 📌 **Citation on Every Answer** | Circular Ref No., Date, and Issuing Authority cited automatically |
| 📄 **Multi-format Support** | Ingests PDF, DOCX, XLSX circulars |
| 🌐 **Secondary Knowledge** | Fetches RBI, NABARD, SEBI public circulars from the web |
| 🔒 **100% Local & Private** | No data leaves the bank's network — runs on LAN |
| 💬 **ChatGPT-like UI** | Clean dark interface with conversation history |
| ⚙️ **Admin Panel** | Upload documents, monitor system, delete outdated circulars |
| 🛡️ **Strict No-Guess Policy** | Explicitly says "I don't know" when answer isn't in circulars |

---

## 🖥️ System Requirements

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| **OS** | Windows 10/11 | Windows 11 |
| **RAM** | 8 GB | 16 GB |
| **CPU** | Intel i5 / Ryzen 5 | Intel i7 / Ryzen 7 |
| **GPU** | Not required | NVIDIA (speeds up LLM) |
| **Storage** | 10 GB free | 20 GB free |
| **Network** | LAN/Intranet | LAN/Intranet |

---

## 🚀 Installation (One-Time Setup)

### Step 1 — Install Ollama
Download and install from: **https://ollama.ai/download**

After install, verify with:
```
ollama --version
```

### Step 2 — Install Python 3.11+
Download from: **https://python.org/downloads**

✅ Check "Add to PATH" during install.

### Step 3 — Run Setup
Double-click **`setup.bat`** — this will:
- Install all Python packages
- Download the LLM model (`llama3.2`, ~2GB)
- Download the embedding model (`nomic-embed-text`)

> ⚠️ First time setup requires internet. After setup, everything runs **offline**.

---

## ▶️ Starting the Server

Double-click **`start.bat`**

The server will display:
```
Local:   http://localhost:8000
LAN:     http://192.168.1.X:8000
Admin:   http://192.168.1.X:8000/admin
```

Share the **LAN URL** with bank staff — they access it from any device on the same network.

---

## 📂 Uploading Circulars

### Method 1 — Drop & Auto-ingest
1. Copy circulars (PDF/DOCX/XLSX) into the `circulars/` folder
2. Open Admin Panel: `http://SERVER_IP:8000/admin`
3. Click **"Re-ingest All from Folder"**

### Method 2 — Upload via Admin Panel
1. Open Admin Panel
2. Drag & drop files into the upload zone
3. Click **"Upload Selected Files"**

### Method 3 — Command Line (Batch)
```bash
cd backend
python document_processor.py
```

---

## 🌐 Secondary Learning (RBI / NABARD / SEBI)

1. Open Admin Panel → **"Secondary Web Learning"** section
2. Click **"Start Web Fetch Now"**
3. The system will scrape current public circulars from RBI, NABARD, SEBI websites and index them

---

## 📁 Project Structure

```
bank_llm/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── rag_engine.py           # RAG pipeline (retrieve + generate)
│   ├── document_processor.py   # PDF/DOCX/XLSX parser + ChromaDB ingestion
│   ├── web_scraper.py          # RBI/NABARD/SEBI web scraper
│   ├── config.py               # All settings (model, paths, thresholds)
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── index.html              # Main chat interface
│   ├── admin.html              # Admin panel
│   ├── style.css               # Styling
│   └── app.js                  # Chat logic
├── circulars/                  # ← Drop your bank circulars here
├── vector_db/                  # ChromaDB (auto-created)
├── setup.bat                   # First-time setup
└── start.bat                   # Start the server
```

---

## ⚙️ Configuration

Edit `backend/config.py` to customize:

```python
LLM_MODEL = "llama3.2"        # Change LLM model
EMBED_MODEL = "nomic-embed-text"
TOP_K_RESULTS = 5              # Chunks retrieved per query
MIN_SIMILARITY_SCORE = 0.35   # Relevance threshold (0.0–1.0)
CHUNK_SIZE = 800               # Text chunk size
SERVER_PORT = 8000             # Change port if needed
```

### Alternative LLM Models (all local via Ollama)

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `llama3.2` | 2GB | ⚡⚡⚡ | ⭐⭐⭐ |
| `llama3.1:8b` | 4.7GB | ⚡⚡ | ⭐⭐⭐⭐ |
| `mistral` | 4.1GB | ⚡⚡ | ⭐⭐⭐⭐ |
| `gemma2:9b` | 5.4GB | ⚡ | ⭐⭐⭐⭐⭐ |

---

## 🛡️ Anti-Hallucination Design

The system uses **three layers** to prevent hallucination:

1. **Similarity Threshold** — Only chunks with ≥35% relevance are included in context
2. **Strict System Prompt** — LLM is instructed to ONLY use provided context
3. **Low Temperature** — LLM temperature set to 0.1 (near-deterministic)

If the knowledge base doesn't contain relevant information, the system responds:
> *"I don't have information about this topic in the available circulars and documents..."*

---

## 🔒 Security Notes

- All data stays on the local server — nothing is sent to the cloud
- No internet required after setup (except for optional web scraping)
- For added security, restrict server access by IP using Windows Firewall
- Consider adding password authentication for the admin panel in production

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Ollama not found" | Ensure Ollama is installed and added to PATH |
| Slow responses | Use a lighter model (`llama3.2`); ensure enough RAM |
| No answers found | Upload circulars first via Admin Panel |
| Can't access from LAN | Check Windows Firewall — allow port 8000 |
| Out-of-memory errors | Reduce `CHUNK_SIZE` in config.py; restart Ollama |

---

## 📞 Support

For issues, check the Activity Log in the Admin Panel at `/admin`.
