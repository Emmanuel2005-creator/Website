# My Flask Note App

This is a Flask web application I built, based on TechWithTim's Flask Web App Tutorial. 
It allows creating, editing, and storing personal notes with user authentication.

---

## 🚀 Features

- User **signup**, **login**, and **logout**  
- Create, edit, and delete personal notes  
- Notes are tied to each user (private)  
- Clean, simple UI with Bootstrap  
- SQLite database for persistence  
- Lightweight and easy to run locally

---

## 📁 Project Structure

```
/ (root)
│   main.py  
│   requirements.txt  
│   README.md  
│  
└── website/  
    ├── __init__.py        # Flask app factory, blueprint setup  
    ├── auth.py            # Authentication routes (login/signup)  
    ├── views.py           # Note-related routes (create, read, delete)  
    ├── models.py          # Database models (User, Note)  
    ├── static/             # CSS, JavaScript, images, etc.  
    └── templates/          # HTML templates  
```

---

## 🛠️ Setup & Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/EmmanuelAkinlusi/my-flask-note-app.git
   cd my-flask-note-app
   ```

2. **Set up a virtual environment** (recommended)  
   ```bash
   python -m venv venv  
   source venv/bin/activate   # On Windows: `venv\Scripts\activate`
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Running the App

```bash
python main.py
```

- The app runs in development mode with debugging enabled.  
- Open your browser and go to: `http://127.0.0.1:5000`

---

## 💾 Database

- Uses **SQLite** (via SQLAlchemy).  
- On first run, creates a `database.db` file.  
- Tables: `User` and `Note`.

---

## ✍️ Usage

1. Navigate to the app in your browser.  
2. **Sign up** for a new account (if you don't already have one).  
3. **Login** with your credentials.  
4. Go to the "Home" or "Notes" page to **create** a new note.  
5. Use the UI to **edit** or **delete** notes.

---

## 🔧 Customization Ideas

- Add **markdown support** for rich-text notes  
- Implement **tagging** or **categories** for notes  
- Add **search functionality** to filter notes  
- Use **PostgreSQL** or **MySQL** instead of SQLite  
- Deploy to a cloud platform (Heroku, AWS, etc.)  

---

## 👩‍💻 Dependencies

- Flask  
- Flask-Login  
- Flask-SQLAlchemy  
- Check `requirements.txt` for full list

---

## 📚 References

- Based on [TechWithTim Flask Web App Tutorial](https://github.com/techwithtim/Flask-Web-App-Tutorial)  
- Flask documentation: https://flask.palletsprojects.com/

---

## 📜 License

This project is based on a tutorial but adapted by Emmanuel Akinlusi.  
You can choose an MIT license if you want.

---

## 🙌 Acknowledgments

- Inspired by TechWithTim’s Flask tutorial ([GitHub](https://github.com/techwithtim/Flask-Web-App-Tutorial)) 
