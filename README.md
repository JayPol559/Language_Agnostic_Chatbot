Quick start (backend)
1. cd Backend
2. create virtualenv:
   python3 -m venv venv
   source venv/bin/activate
3. pip install -r requirements.txt
4. ensure Backend/.env contains:
   GEMINI_API_KEY=AIzaSyDimyRfkF7a8Nj84IE8D4PVrZgFVH7WHp4
   PORT=5000
   FLASK_DEBUG=1
5. python app.py
   - Backend will run on http://0.0.0.0:5000 (or PORT from .env)

Quick start (frontend)
1. cd frontend
2. npm install
3. For development (local):
   - create frontend/.env with:
     REACT_APP_API_URL=https://language-agnostic-chatbot-1.onrender.com
   - npm start
4. For production build:
   REACT_APP_API_URL=https://language-agnostic-chatbot-1.onrender.com npm run build
   - Deploy build/ to GitHub Pages, Netlify, or any static host.
