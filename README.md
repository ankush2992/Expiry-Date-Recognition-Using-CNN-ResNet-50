# 🕒 Expiry Date Recognition System

## 📚 Project Overview
The **Expiry Date Recognition System** is an AI-powered web application that detects and analyzes expiration dates from product images. Users upload images via a web interface, which are processed on a backend hosted on an **Azure VPS**. The system utilizes multiple AI/ML technologies to extract and interpret the expiration date and other relevant information, presenting the results in real-time.

---

## ⚡️ Key Features
- **Image Upload & Analysis:** Users can upload product images through an intuitive web interface.
- **Expiry Date Detection:** Detects and extracts expiry labels using a CNN with **ResNet-50** backbone.
- **Text Extraction & Translation:**  
    - **PaddleOCR:** Extracts date information from identified regions.  
    - **Azure OCR:** Performs OCR on the full image to extract product descriptions.  
    - **Azure Translator:** Converts extracted text to English (if necessary).  
- **Text Analysis:** Identifies and interprets various date formats.  
- **Result Display:**  
    - Annotated image with bounding boxes on detected date regions.  
    - Original and translated text along with expiration status.  

---

## 🛠️ Technology Stack
### ⚙️ Backend
- **Python/Flask:** Handles API requests and application logic.
- **Gunicorn:** Serves the Flask application in a production environment.
- **Nginx:** Reverse proxy to manage HTTPS traffic and improve performance.
- **Azure VPS:** Hosts the application and model securely.

### 🧠 AI/ML Models
- **ResNet-50:** Pre-trained CNN model for feature extraction and date detection.
- **PaddleOCR:** For extracting text from detected date regions.
- **Azure OCR & Translator:** For full image OCR and multi-language support.

### 🌐 Frontend
- **HTML/CSS/JavaScript:** Clean and responsive web interface.
- **Bootstrap:** Ensures a user-friendly experience.

---

## 📡 Workflow
1. **Image Upload:** User uploads the image on the web interface.
2. **Backend Processing:** Image sent to Flask backend where:
    - ResNet-50 detects date regions.
    - PaddleOCR extracts text from regions.
    - Azure OCR analyzes product descriptions.
    - Azure Translator translates text if needed.
3. **Date Analysis:** System processes extracted text to identify the date format and predicts the expiration date.
4. **Result Display:** Annotated image, date predictions, and relevant text information are shown on the website.

---

## 🔒 Security & Deployment
- **Domain Name:** Hosted at [ExpiryScan.me](https://expiryscan.me) with **SSL encryption** for secure communication.
- **Nginx as Reverse Proxy:** Ensures HTTPS traffic, manages requests, and enhances performance.
- **Gunicorn Deployment:** Deploys Flask app efficiently for production-grade environments.

---

## 🚀 Setup Instructions
### 1. Clone the Repository
```bash
git clone [https://github.com/your-repo-name.git](https://github.com/ankush2992/Expiry-Date-Recognition-Using-CNN-ResNet-50.git)
cd Expiry-Date-Recognition-Using-CNN-ResNet-50.git

python3 -m venv env
source env/bin/activate  # For Linux/Mac
env\Scripts\activate  # For Windows

pip install -r requirements.txt

gunicorn --bind 0.0.0.0:5000 app:app
```

## 📝 Usage Instructions
- Open https://expiryscan.me to access the web interface.

- Upload product images for expiry date detection and analysis.

- View detected regions, extracted text, and expiration status on the results page.





