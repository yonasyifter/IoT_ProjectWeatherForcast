# 🌦️ IoT Weather Forecast - Park Administration System

This repository contains a full-stack solution for a specialized weather station system designed for Park Administrators. It features a **FastAPI** backend for processing IoT sensor data and a **Vue.js** frontend for real-time visualization.

## 🚀 Features

* **Real-time Dashboard:** Built with Vue.js for reactive data updates.
* **High Performance:** FastAPI backend for asynchronous data handling.
* **IoT Integration:** Designed to process sensor data from remote weather stations.
* **Park Management:** Tailored tools for administrators to monitor micro-climates.

---

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yonasyifter/IoT_ProjectWeatherForcast.git
cd IoT_ProjectWeatherForcast

```

### 2. Backend Setup (FastAPI)

It is recommended to use a virtual environment:

```bash
# Create and activate virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate | On macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 3. Frontend Setup (Vue.js)

Ensure you have [Node.js and npm](https://nodejs.org/) installed.

```bash
# Navigate to the frontend directory (e.g., /frontend or /client)
cd weather

# Install dependencies
npm install

```

---

## 🏃 Running the Application

To run the full system, you will need to start both the backend and frontend servers.

### Start the Backend

From the root directory:

```bash
uvicorn main:app --reload

```

* **API Documentation:** Access [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/api)

### Start the Frontend

From the frontend directory:

```bash
npm run dev

```

* **Local Access:** Usually available at [http://localhost:5173](https://www.google.com/search?q=http://localhost:5173) (Vite) or [http://localhost:8080](https://www.google.com/search?q=http://localhost:8080).

---

## 📁 Project Structure

```text
├── app/                # FastAPI Application
│   ├── main.py
    ├── config.py
│   ├── influx.py
    ├── schemas.py       # Entry point
│   ├── requirements.txt    # Python dependencies
│   └── routes/                # weather.py
├── frontend/               # Vue.js Application
│   ├── src/
  │   ├── asset/
  │   ├── components/
  │   ├── pages/              # Components and Views
│   ├── package.json        # Node dependencies
│   └── public/             # Static assets
└── README.md

```

## 🤝 Contributing

1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.
