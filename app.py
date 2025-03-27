from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import torch
from PIL import Image
from test_model import get_model, process_image
from azure_vision import AzureVisionService
from gpt_service import TextAnalysisService
import platform

app = Flask(__name__)  # app setup
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5000kb size limit from website.

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/css', exist_ok=True)

# here loading azure vision ep=(https://ankush.cognitiveservices.azure.com/) and text analysis services (OCR and translation by using google gemini)
azure_vision = AzureVisionService()
text_analysis = TextAnalysisService()


def play_loading_sound():
    if platform.system() == 'Windows': # only for windows users for now
            import winsound
            for freq in range(500, 2000, 100):
                winsound.Beep(freq, 60)
           
       

# Load expiration date detection model
print("Incoming model...")
play_loading_sound()
model = get_model()
checkpoint = torch.load('checkpoints/final_model.pth', map_location='cpu')
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()
print("Model loaded successfully")
play_loading_sound()

# checking the uploaded file is a image file, also protect the server from malicious files injections. until the img is itself a malicious file.
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"upload_{timestamp}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filepath, filename

# Main page
@app.route('/')
def home():
    return render_template('index.html')

# API endpoint for detecting expiration dates in images
@app.route('/detect', methods=['POST'])
def detect():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filepath, filename = save_uploaded_file(file)
            
            # Process image to findingh exp dates
            detected_dates = process_image(filepath, model)
            
            img = Image.open(filepath)
            result = {
                'image_path': f'/static/uploads/{filename}',
                'image_width': img.size[0],
                'image_height': img.size[1],
                'detections': detected_dates
            }
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Detection Error: {str(e)}")
            return jsonify({'error': str(e)}), 500
        
    return jsonify({'error': 'Invalid file type'}), 400

# API endpoint for OCR, translation and ananalogu of text in images
@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            image = Image.open(file.stream)
            
            # Extract & translatr detected texts from image, any language detected translate in english lang
            result = azure_vision.extract_text(image, translate_to='en')

            # Get OCR dates from the request if available
            ocr_dates = None
            if request.form.get('detections'):
                try:
                    import json
                    ocr_dates = json.loads(request.form.get('detections'))
                except:
                    ocr_dates = None
            
            # using google gemini to brainstorm the output translated texts to conclude a concise result.
            try:
                analysis = text_analysis.analyze_text(result['translated_text'], ocr_dates)
            except Exception as e:
                print(f"Text Analysis Error: {str(e)}")
                analysis = "Error analyzing text. Please check the API configuration."
            
            return jsonify({
                'status': 'success',
                'original_text': result['original_text'],

                'translated_text': result['translated_text'],
                'analysis': analysis
            })
            
        except Exception as e:
            print(f"Analysis Error: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True) 