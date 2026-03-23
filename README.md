# 🎓 Durai Tuition Centre Management System

A full-stack multi-syllabus tuition management system built for **Durai Tuition Centre**, Chennai.

## 🌐 Live Demo
👉 **[Open App](https://balamuruganr2004.github.io/durai-tuition-centre/)**

## 📚 Syllabuses Supported
| Board | Curriculum | Fee |
|-------|-----------|-----|
| 🔵 CBSE | NCERT | ₹4,500/month |
| 🟣 International | IB / Cambridge | ₹6,000/month |
| 🟢 State Board | Samacheer Kalvi | ₹3,500/month |

## 👥 User Roles
| Role | Access |
|------|--------|
| **Admin** | Full system — all students, fees, reports, AI insights |
| **Teacher** | Attendance, marks, notes, homework |
| **Student** | Own profile only — marks, attendance, homework, fees |
| **Parent** | Child's profile only — results, fees, WhatsApp alerts |

## ✨ Features
- 📊 **Admin Dashboard** — Stats, AI alerts, fee collection, syllabus-wise reports
- ✅ **Attendance** — Mark by syllabus + grade, WhatsApp auto-alert on absence
- 📝 **Exams & Results** — Enter marks, grade tracking, progress charts
- 💰 **Fees Management** — Board-wise pricing, payment tracking, PDF receipts
- 📚 **Study Materials** — Upload/download notes by syllabus + grade
- 💬 **WhatsApp Integration** — Auto-notifications for absent, fees, results
- 🤖 **AI Assistant** — Claude-powered, board-aware (NCERT/IB/Samacheer)
- 📱 **Mobile-First UI** — Professional blue, app-like experience

## 🚀 Quick Run
Just open `web/index.html` in any browser — no server needed!

## 🏗️ Tech Stack
```
Frontend  : HTML / CSS / JavaScript (zero build)
Backend   : Python Django + Django REST Framework
Database  : PostgreSQL + Redis
Mobile    : Flutter (iOS + Android)
AI        : Anthropic Claude API
WhatsApp  : Meta Business API
Deploy    : Docker + Nginx + GitHub Actions
```

## 📁 Project Structure
```
dt/
├── web/           → Frontend app (open index.html directly)
├── backend/       → Django REST API
│   ├── api/       → Models, Views, Serializers, URLs
│   └── durai_backend/ → Settings, Celery, WSGI
├── mobile/        → Flutter app
└── deployment/    → Docker, Nginx, CI/CD
```

## ⚙️ Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # Add your API keys
python manage.py migrate
python manage.py runserver
```

## 🐳 Docker Deploy
```bash
cd deployment
docker-compose up -d
```

## 👨‍💻 Developer
**Balamurugan R** — [@BalamuruganR2004](https://github.com/BalamuruganR2004)

---
*Built with ❤️ for Durai Tuition Centre, Chennai*
