from PIL import Image
from paddleocr import PaddleOCR
import numpy as np
import cv2
import re

class OCRService:
    def __init__(self):
        # Setup OCR engine
        self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        
        # Patterns to detect dates (YYYY-MM-DD, etc.) the detiction is not accurate.
        #  so sorting muntiple detected outputs on basis of date visibility. 
        #accuracy               ------------------------------- think another approcah (not optimal for production). approach to try: might need more trainning on wide date formate.
        self.date_patterns = [
            r'\d{2,4}[-/.]\d{1,2}[-/.]\d{1,2}',  # YYYY-MM-DD, YYYY/MM/DD
            r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}',  # DD-MM-YYYY, DD/MM/YYYY
            r'\d{1,2}[-/.]\d{2,4}',              # MM/YYYY, MM-YYYY
            r'\d{2,4}[-/.]\d{1,2}'               # YYYY/MM, YYYY-MM
        ]

    def is_date_format(self, text):
        """Check if text looks like a date"""
        text = text.strip()
        return any(re.match(pattern, text) for pattern in self.date_patterns)

    def read_text(self, image):
        """Extract text from image, keeping dates in sc/st catagory"""
        try:
            width, height = image.size
            
            # Converting images for PaddleOCR detection
            paddle_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            paddle_result = self.paddle_ocr.ocr(paddle_image, cls=True)
            
            # def valuee
            paddle_text = ""
            paddle_confidence = 0.0
            
            if paddle_result and paddle_result[0]:
                # Separate dates from other text
                date_texts = []
                other_texts = []
                
                for line in paddle_result[0]:
                    text = line[1][0]
                    conf = float(line[1][1])
                    
                    # Sort text into dates and non-dates
                    if self.is_date_format(text):
                        date_texts.append((text, conf))
                    else:
                        other_texts.append((text, conf))
                
                # providing reservation for date kinds.
                if date_texts:
                    # select date =  highest confidence
                    paddle_text, paddle_confidence = max(date_texts, key=lambda x: x[1])
                elif other_texts:
                    # If no date, get to texts with highest confidence
                    paddle_text, paddle_confidence = max(other_texts, key=lambda x: x[1])
                
                paddle_confidence = paddle_confidence * 100 
           
            return {
                'paddle_text': paddle_text,
                'paddle_confidence': paddle_confidence,
                'dimensions': f"{width}x{height}px",
                'is_date': self.is_date_format(paddle_text)
            }
            
        except Exception as e:
            print(f"OCR Error: {str(e)}")
            return {
                'paddle_text': '',
                'paddle_confidence': 0.0,
                'dimensions': f"{width}x{height}px",
                'is_date': False
            } 