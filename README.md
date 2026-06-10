# 🚀 ResumeAIX: AI-Powered ATS Scanner & Job Matcher

Welcome to **ResumeAIX**, a full-stack AI web application built to help job seekers bridge the gap between academia and industry. By leveraging **Google Gemini LLM** and real-time job APIs, ResumeAIX instantly calculates an ATS match score, identifies critical skill gaps, and provides live, clickable job matches.

---

## 🎯 Core Features

| 🌟 Feature                 | 📝 Description                                               |
| -------------------------- | ------------------------------------------------------------ |
| 🔐 **User Authentication** | Secure JWT-based login and registration backed by MongoDB    |
| 📄 **Smart PDF Parsing**   | Extracts unstructured text from resumes using `pdfminer.six` |
| 🤖 **AI ATS Scoring**      | Uses Google Gemini 2.5 Flash as a virtual recruiter          |
| 🌍 **Live Job Matches**    | Fetches real-time remote tech jobs via APIs                  |
| 🎨 **3D Glassmorphic UI**  | Dark-mode UI with React Three Fiber animations               |

---

## 🏗️ System Architecture

```text
[ User / Job Seeker ]
        │
        ▼ (Uploads PDF & Clicks Analyze)

┌───────────────────────────────┐
│       React Frontend          │
│  (3D UI, Dashboards, Routes)  │
└─────────────▲─────────────────┘
              │ (Response: ATS Score, Skills, Jobs)
              ▼
┌───────────────────────────────┐
│       FastAPI Backend         │
│   (Auth + Business Logic)     │
└─────────────┬─────────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
Google Gemini API   Remotive API
 (AI Analysis)      (Job Fetching)
```

---

## 💻 Tech Stack

| 🔧 Layer            | 🛠️ Technologies                                         |
| ------------------- | -------------------------------------------------------- |
| **Frontend**        | React.js, React Router, Tailwind CSS, @react-three/fiber |
| **Backend**         | Python, FastAPI, Uvicorn, Requests                       |
| **Database & Auth** | MongoDB, PyMongo, JWT, Passlib, Bcrypt                   |
| **AI & NLP**        | Google Gemini 2.5 Flash, pdfminer.six                    |

---

## ⚙️ Local Setup & Installation

### 🔹 1. Backend Setup

```bash
cd backend
python -m venv venv
```

Activate virtual environment:

```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install fastapi uvicorn python-multipart requests pdfminer.six pymongo google-generativeai passlib bcrypt pyjwt
```

Create `backend/.env` (copy from `backend/.env.example`):

```env
GEMINI_API_KEY=your_gemini_key
RAPIDAPI_KEY=your_rapidapi_jsearch_key
RAPIDAPI_HOST=jsearch.p.rapidapi.com
# or Adzuna India:
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

Run the backend server:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Live jobs: after resume analysis, the dashboard shows **3–4 India jobs per recommended role** (JSearch and/or Adzuna). Without API keys, the job section still renders with a setup notice.

---

### 🔹 2. Frontend Setup

```bash
cd frontend
npm install
npm start
```

---

## 🔄 Workflow Summary

1. User uploads resume (PDF)
2. Backend extracts text using `pdfminer`
3. Gemini AI analyzes resume
4. ATS score + skill gaps generated
5. Matching jobs fetched from API
6. Results displayed in UI dashboard

---

## 🚀 Deployment Tips

* Use **Render / Railway / AWS** for backend hosting
* Deploy frontend via **Vercel / Netlify**
* Store secrets using `.env` files
* Enable HTTPS for secure JWT handling

---

## 📌 Future Enhancements

* 📊 Resume improvement score breakdown
* 🧠 Personalized learning roadmap
* 📈 Skill trend analytics
* 📝 Cover letter generator
* 🎯 Role-specific resume optimization

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork the repo and submit a pull request.

---

## 📄 License

This project is licensed under the **MIT License**.

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub!

---
git add README.md
git commit -m "Finalized README with structured tables and formatting"
git push origin main