# GuardianText 🛡️
**Context-Aware Messaging Application for Toxic Language Filtering**

---

## Project Structure

Project root (folder name may vary locally, e.g. `GuardianTextClaude/`):

```
guardiantext/
├── backend/
│   ├── app.py           ← Flask app, Socket.IO events, REST + admin API
│   ├── nlp_filter.py    ← Hybrid NLP toxicity engine (rules + ML)
│   ├── database.py      ← SQLite helpers (users, messages, filter logs, admin flags)
│   ├── auth.py          ← Validation helpers, login_required decorator
│   ├── config.py        ← App configuration (host, port, toxicity thresholds)
│   └── requirements.txt ← Backend Python dependencies
├── frontend/
│   ├── login.html       ← Login / Register page
│   ├── chat.html        ← Real-time chat UI (rooms, typing, suggestions)
│   ├── dashboard.html   ← Message log, analytics & admin controls
│   ├── css/
│   │   └── style.css    ← Global dark-theme stylesheet
│   └── js/
│       ├── auth.js      ← Login/register logic
│       ├── chat.js      ← Socket.IO client, message rendering, suggestion flow
│       └── dashboard.js ← Stats, logs, admin user/message management
├── run.py               ← Convenience launcher (runs backend and opens browser)
└── README.md
```

---

## Setup

### 1. Install Python dependencies
```bash
cd guardiantext/backend
pip install -r requirements.txt
```

### 2. Run the server
```bash
# From the project root:
python run.py

# OR directly:
cd backend
python app.py
```

You will see:
```
  Local access:    http://localhost:5000
  Network access:  http://192.168.x.x:5000   ← share this with other PCs
```

### 3. Connect from other PCs
- Make sure all PCs are on the **same Wi-Fi / LAN network**
- Open a browser on the second PC and go to `http://<server-ip>:5000`
- Both users register/login and can chat in real time

---

## Features

| Feature | Details |
|---|---|
| Real-time chat | Socket.IO WebSockets, multiple rooms |
| Hybrid NLP Filter | Custom rules + TF–IDF + LogisticRegression; leet-speak and slang aware |
| Toxicity scoring | 0–1 probability, visualized as 0–100% in the dashboard |
| Suggestion-before-send | Toxic messages are analyzed and rephrased; sender chooses a toxic‑free version before it is sent |
| Auto-clean | Toxic words/phrases removed and the sentence rephrased to a polite alternative |
| Block system | Highly toxic content is prevented from being sent in original form |
| Filter logs | Full audit trail with original + cleaned messages, scores, actions |
| Dashboard | Stats: total messages, filter rate, blocked/warned counts, “top offenders” |
| User tracking | Per-user filter history and aggregate toxicity |
| Admin controls | Admin account, ban/unban users, reset passwords, clear all chats/logs, delete individual messages |
| Auth | Username/password with session cookies |

---

## NLP Pipeline (nlp_filter.py)

High level:

```
Raw input
   ↓  normalize (lowercase, de-leet, collapse repeats)
   ↓  expand slang/abbreviations (kys→kill yourself, stfu→shut the f*** up, etc.)
   ↓  detect toxic words/phrases (dictionary with severity tiers)
   ↓  vectorize text (TF–IDF over 1–2 grams)
   ↓  ML classifier (LogisticRegression) → toxicity probability
   ↓  decide action: allowed | warned | blocked (based on probability + thresholds)
   ↓  build toxic-free rephrasing (remove insults, clean up grammar, add polite framing)
   ↓  return FilterResult (score, toxic_words, cleaned_message, suggestion, action)
```

### Thresholds (config.py)
| Threshold | Default | Behaviour |
|---|---|---|
| TOXICITY_THRESHOLD | 0.01 | Messages at or above this probability are treated as toxic and trigger suggestions/warnings |
| BLOCK_THRESHOLD | 0.70 | Messages at or above this probability are considered highly toxic and can be blocked from being sent as‑is |

---

## Evaluation Metrics
The system supports:
- **SUS (System Usability Scale)** – evaluate via the UI during user testing
- **Performance metrics** – filter accuracy, false positive/negative rate trackable via the dashboard logs

---

## Requirements
- Python 3.9+
- Flask, Flask-SocketIO, NLTK
- Modern browser (Chrome / Edge / Firefox)
- Same local network for multi-PC access
