# 🚀 MaddyBot 2.0 — Ultra Fast Multimodal AI Assistant

MaddyBot 2.0 is a redesigned, high-performance AI assistant powered by **Google Gemini Models**, **ChromaDB**, and **LangChain**.  
It supports **text, PDF, images, audio**, and delivers **extremely fast responses (2–10 s locally)**.

---

## ✨ Features

### 🧠 1. Multimodal Input Support
MaddyBot 2.0 can process:
- 📄 PDF files  
- 📝 TXT documents  
- 🖼️ Images  
- 🎧 Audio files  
- 💬 Standard text chat  

### 🔍 2. Local RAG using ChromaDB
- Uses **Gemini embeddings (embedding-001)**  
- Stores vectors locally in **ChromaDB**  
- Ultra-fast semantic search  
- Privacy-safe (no cloud storage)

### ⚡ 3. Ultra-Fast Response Pipeline
Optimized backend responds within **2–5 ms**.

### 🧰 4. Modular Tools System (Skills)
Includes built-in tools:
- 🛠️ Code execution  
- 🕒 Time utilities  
- 🌐 Web search  

Easily extendable.

### 🖥️ 5. Clean Frontend UI
- Chat interface  
- File upload: PDF, image, audio  
- Super-fast response display  
- Built with **Flask + HTML + CSS + JavaScript**

---

## 🏗️ Tech Stack

**Backend**
- Python  
- Flask  
- Google Gemini API  
- LangChain  
- ChromaDB  

**Frontend**
- HTML  
- CSS  
- JavaScript  

---

## 🛠 Installation

### 1. Clone the repository (v2.0 branch)
```bash
git clone -b v2.0 https://github.com/YOURUSERNAME/maddybot.git
cd maddybot
```

### 2. Add your Gemini API key
Create a `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000
```

---

## 📦 Project Structure

```
maddybot2.0/
│── app.py
│── agent_core.py
│── requirements.txt
│── utils/
│── skills/
│── templates/
│── static/
│── memory/      (ignored in repo)
└── .env         (ignored in repo)
```

---

## 🏷️ Version

**Current Release:** `v2.0`

Includes:
- Multimodal input support  
- ChromaDB vector memory (RAG)  
- Gemini API integration  
- Updated UI  
- Tools system  
- Major performance optimizations  

---

## 📜 License
MIT License

---

## ⭐ Acknowledgements

- Google Gemini API  
- Flask  
- LangChain  
- ChromaDB  

---

## 🎉 Enjoy MaddyBot 2.0!
Ultra-fast. Powerful. Extensible.
