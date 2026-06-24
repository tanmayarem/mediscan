MEDIScan – AI-Based Medicine Identification System

**MEDIScan** is an **AI-powered healthcare web application** that identifies medicines using **image processing and Optical Character Recognition (OCR)**. The system extracts and analyzes text from medicine packaging to provide structured information such as **medicine name, composition, and description** through an intuitive web interface.

This project demonstrates practical implementation of **Artificial Intelligence, OCR, Flask-based backend development, and database management**, making it suitable for academic evaluation and industry-level screening.

 Key Skills Demonstrated

* Artificial Intelligence (AI)
* Optical Character Recognition (OCR)
* Image Processing
* Python Programming
* Flask Web Framework
* SQLite Database Management
* RESTful Web Application Development
* Frontend–Backend Integration

---

## Core Features

* Image-based medicine identification using OCR
* Automated text extraction from medicine labels
* Medicine detail lookup and display
* Web-based user interface for real-time interaction
* Local database for storing and retrieving medicine records

---

 Technology Stack

Programming Language:

* Python

**Backend Framework:**

* Flask

**OCR & Image Processing:**

* Tesseract OCR
* OpenCV
* Pillow

**Database:**

* SQLite3

**Frontend:**

* HTML
* CSS
* JavaScript

---

## System Architecture (High-Level)

1. User uploads a medicine image via web interface
2. Image preprocessing using OpenCV
3. Text extraction using Tesseract OCR
4. Information parsing and validation
5. Storage and retrieval using SQLite database
6. Results rendered through Flask templates

---

## Project Structure

```bash
MEDIScan/
│
├── app.py                 # Flask application entry point
├── database.db            # SQLite database
├── static/                # Frontend assets (CSS, JS, images)
├── templates/             # HTML templates
├── uploads/               # Uploaded medicine images
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

---

## Installation and Execution

### Step 1: Clone Repository

```bash
git clone https://github.com/your-username/MEDIScan.git
cd MEDIScan
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate       # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run Application

```bash
python app.py
```

Access the application at:
**[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**

---

## Problem Statement

Manual identification of medicines from unclear packaging or prescriptions is time-consuming and error-prone. Existing systems lack a simple AI-driven interface for extracting and presenting medicine information from images.

---

## Solution Overview

MEDIScan automates the medicine identification process using OCR and AI-based text processing. The system reduces human dependency, improves accessibility, and provides accurate medicine information through a lightweight web application.

---

## Use Cases

* Medicine identification from damaged or unclear labels
* Healthcare support tools
* Academic and AI learning projects
* Prototype for digital health platforms

---

## Hackathon Details

* **Project Name:** MEDIScan
* **Event Type:** Hackathon Project
* **Location:** VIT Chennai
* **Team Members:**

  * Naseen Nazar
  * Kripa

---

## Future Scope

* Drug–drug interaction analysis
* Expiry date detection using computer vision
* Fake medicine detection using ML models
* Cloud-based database integration
* Mobile application development

---

## License

This project is developed for **educational and research purposes**.



