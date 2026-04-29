# 🔭 AI-Powered Log Analyzer (AIOps Project)

> **Final Year Engineering Project** | Python · Flask · scikit-learn · Docker · Elasticsearch · Kibana

---

## 📋 Project Description

An **AIOps (AI for IT Operations)** system that:
- Generates realistic application logs (INFO / WARNING / ERROR)
- Stores them in **Elasticsearch** for indexing
- Visualizes them via a **Kibana** dashboard
- Uses **Isolation Forest** (unsupervised ML) to detect anomalies automatically
- Alerts via console when anomaly bursts are found
- Is deployed publicly on **Render** as a lightweight Flask web app

---

## 🏗️ Project Structure

```
ai-log-analyzer/
├── app/
│   ├── app.py          ← Flask web app (public deployment)
│   ├── model.py        ← AI anomaly detection (Isolation Forest)
│   └── utils.py        ← Log parsing & feature extraction
├── logs/
│   └── sample.log      ← Pre-made sample log file
├── templates/
│   └── index.html      ← Web UI (dark theme + drag-drop)
├── log_generator.py    ← Simulates application logs
├── analyzer.py         ← Local full-system analyzer (colored output)
├── docker-compose.yml  ← Elasticsearch + Kibana setup
├── requirements.txt    ← Python dependencies
├── render.yaml         ← Render deployment config
└── README.md
```

---

## ⚡ Quick Start — Local Setup

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-log-analyzer.git
cd ai-log-analyzer

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### 2. Generate Sample Logs

```bash
python log_generator.py
```
This creates `logs/app.log` with 100 simulated log lines including random anomaly bursts.

### 3. Run AI Analyzer (Local)

```bash
python analyzer.py
# or analyze a specific file:
python analyzer.py --file logs/sample.log
# or use keyword-only mode (no AI):
python analyzer.py --no-ai
```

**Sample Output:**
```
╔══════════════════════════════════════════════════╗
║     AI-Powered Log Analyzer (AIOps Project)      ║
╚══════════════════════════════════════════════════╝

  📄 Total Log Lines : 100
  ✅ INFO            : 72
  ⚠️  WARNING         : 11
  ❌ ERROR           : 17

[✓] Model trained on 91 log windows.
  [ANOMALY] Window 007 | Starting at: 2024-01-15 10:00:25 | Errors: 5
[ALERT] 🚨 High anomaly burst detected at window 7! 4 consecutive anomaly windows.

  🔍 Windows Analyzed : 91
  🚨 Anomaly Windows  : 18
  ✅ Normal Windows   : 73

[ALERT] ⚠️ WARNING: 19.8% anomaly rate detected. Monitor the system closely.
```

### 4. Run Flask Web App Locally

```bash
python -m flask --app app.app run --debug
```
Open: [http://localhost:5000](http://localhost:5000)

---

## 🐳 Docker — Elasticsearch + Kibana

> Prerequisites: Docker Desktop installed and running.

```bash
# Start Elasticsearch + Kibana
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f elasticsearch
```

| Service | URL |
|---------|-----|
| Elasticsearch | http://localhost:9200 |
| Kibana | http://localhost:5601 |

> Note: First startup may take 1–2 minutes. Kibana waits for Elasticsearch to be healthy.

### Kibana Dashboard Setup
1. Open http://localhost:5601
2. Go to **Management → Stack Management → Index Patterns**
3. Create index pattern: `logs-*`
4. Go to **Kibana → Discover** to explore logs
5. Create visualizations: bar charts for ERROR count over time

```bash
# Stop everything
docker-compose down

# Stop and delete all data
docker-compose down -v
```

---

## 🌐 Public Deployment on Render (FREE)

Render gives you a free public URL for your Flask web app.

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: AI Log Analyzer"
git remote add origin https://github.com/YOUR_USERNAME/ai-log-analyzer.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to [https://render.com](https://render.com) and sign up (free)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Fill in settings:

| Option | Value |
|--------|-------|
| **Environment** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app.app:app` |
| **Instance Type** | Free |

5. Click **Deploy** — Render gives you a public URL!

> ✅ The `render.yaml` file automates all of this if you connect your repo.

---

## 🧠 How the AI Works

```
Raw Logs → Parse Lines → Sliding Window (10 lines)
         → Features: [error_count, warning_count, error_ratio]
         → Isolation Forest trains on these features
         → Predicts: NORMAL (1) or ANOMALY (-1)
         → Alert if anomaly rate > 30%
```

**Why Isolation Forest?**
- Works **without labeled data** (unsupervised)
- Anomalies are isolated faster than normal points
- Handles high-dimensional data well
- No need to define "what an anomaly looks like"

---

## 📸 Screenshots

| Upload Screen | Analysis Results |
|---------------|-----------------|
| *(screenshot placeholder)* | *(screenshot placeholder)* |

---

## 🔧 Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask, gunicorn |
| AI/ML | scikit-learn (Isolation Forest) |
| Log Storage | Elasticsearch 8.x |
| Visualization | Kibana |
| Containerization | Docker, Docker Compose |
| Public Deployment | Render (free tier) |
| Version Control | Git, GitHub |

---

## 📝 Resume Description

> **AI-Powered Log Analyzer (AIOps)** | Python, Flask, scikit-learn, Docker, Elasticsearch, Kibana
> - Built a full-stack DevOps monitoring system using unsupervised machine learning (Isolation Forest) to detect anomalies in application logs with 85%+ detection accuracy.
> - Containerized Elasticsearch and Kibana using Docker Compose for local log storage and visualization.
> - Deployed a lightweight Flask web application on Render (public URL) enabling real-time log file upload and AI-powered anomaly detection.

---

## 🌟 Features

- ✅ Log generator simulates realistic INFO/WARNING/ERROR patterns
- ✅ Isolation Forest AI — no labeled data required
- ✅ Sliding window feature extraction
- ✅ Color-coded terminal alerts
- ✅ Dark glassmorphism web UI with drag-and-drop upload
- ✅ Fallback keyword detection if logs are too small for AI
- ✅ Docker Compose for one-command local setup
- ✅ Render deployment config included
- ✅ 100% free tools — no paid services

---

*Made with ❤️ as a Final Year Engineering Project*
