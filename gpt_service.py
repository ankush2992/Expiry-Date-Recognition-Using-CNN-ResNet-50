import google.generativeai as genai
from dotenv import load_dotenv
import os
from datetime import datetime
import re
load_dotenv()

class TextAnalysisService:
    def __init__(self):
        # Get API key from environment
        gemini_key = os.getenv('GEMINI_API_KEY')
        self.ai_model = None
        
        if not gemini_key:
            print("gemini api not in your .env file")
            return
        
        try:
            genai.configure(api_key=gemini_key)
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_methods:
                    available_models.append(m)
            
            if available_models:
                model_name = available_models[0].name
                self.ai_model = genai.GenerativeModel(model_name)
                print(f"we are going to use ==> {model_name}")
            else:
                print("no model found")
        except Exception as e:
            print(f"unknown error , replace ai , or api key: {str(e)}")

    def analyze_text(self, text, detected_ocr_dates=None): # responsible for deciding if a product is expired based on detected text (date)
        
        try:
            found_dates = []
        
            if detected_ocr_dates and isinstance(detected_ocr_dates, list): # DATE OUR OCR FOUNDED - WE ARE USING IT FIRST ()
                for date_obj in detected_ocr_dates:
                    raw_text = date_obj.get('paddle_text')
                    if not raw_text:
                        continue
                    clean_text = self._clean_date_string(raw_text)
                    
                    # Is it a date?
                    if not self._looks_like_date(clean_text):
                        continue
                        
                    date = self._parse_date(clean_text)
                    if date:
                        confidence = date_obj.get('paddle_confidence', 0)
                        found_dates.append((date, raw_text, confidence))
            
            #  method 2nd ----- Regex patterns (custom defined)
            if not found_dates:
                patterns = [
                    r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}',  #25/12/2023,12-31-2023
                    r'\d{2,4}[-/.]\d{1,2}[-/.]\d{1,2}',  # 2023/12/25
                    r'\d{1,2}[-/.]\d{2,4}',             #12/2023
                    r'\d{2,4}[-/.]\d{1,2}'            #2023/12
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        date_text = match.group()
                        date = self._parse_date(date_text)
                        if date:
                           
                            found_dates.append((date, date_text, 0.8))
            
            # optional method 3rd ----- Gemini help us if you found dates in the text
            if not found_dates and self.ai_model:
                try:
                    prompt = f"""
                    Hey, I have a project, and i have used 2 methodes prior to it to find dates from image texts. if i am here it means both methods have already failed. i am so demotivated with my project , but still i want to give it a final try to find date from those texts ,  i need you to extract an expiration date from this product text please please please help me use your full power to help me, and if you do it sucessfullt i will buy your premium version , heres the text:
                    "{text}"
                    
                    Just give me the date and nothing else. Format it as DD/MM/YYYY, MM/DD/YYYY, or YYYY/MM/DD.
                    If you can't find a date,  say "No date found".
                    """
                    
                    response = self.ai_model.generate_content(prompt)
                    if response.parts:
                        date_text = response.text.strip()
                        if date_text != "No date found":
                            date = self._parse_date(date_text)
                            if date:
                                # not trusted , so we give it a lower confidence
                                found_dates.append((date, date_text, 0.7))
                except Exception as e:
                    print(f"gemini is in coma , or api key is not valid: {str(e)}")
            
            # 4th method ----- Check for weird date formats
            if not found_dates and detected_ocr_dates:
                for date_obj in detected_ocr_dates:
                    raw_text = date_obj.get('paddle_text')
                    if not raw_text:
                        continue
                    
                    # Check for format YYYYMM/DD (like 202401/15)           # Ai generated code for the specific error types.
                    if re.match(r'^\d{6}/\d{1,2}$', raw_text):
                        try:
                            year = int(raw_text[:4])
                            month = int(raw_text[4:6])
                            day = int(raw_text.split('/')[1])
                            
                            if month < 1 or month > 12 or day < 1 or day > 31 or year < 2000 or year > 2100:
                                continue
                                
                            date = datetime(year, month, day)
                            confidence = date_obj.get('paddle_confidence', 0) * 0.9
                            found_dates.append((date, raw_text, confidence))
                        except ValueError:
                            # Skip invalid dates
                            pass
                    
                    # Check for format YYYYMMDD (like 20240115)
                    elif re.match(r'^\d{8}$', raw_text):
                        try:
                            year = int(raw_text[:4])
                            month = int(raw_text[4:6])
                            day = int(raw_text[6:8])
                            
                            # Sanity check
                            if month < 1 or month > 12 or day < 1 or day > 31 or year < 2000 or year > 2100:
                                continue
                                
                            date = datetime(year, month, day)
                            confidence = date_obj.get('paddle_confidence', 0) * 0.9
                            found_dates.append((date, raw_text, confidence))
                        except ValueError:
                            pass

            # If we still couldn't find any dates, let the user know
            if not found_dates:
                return "sorry , i couldn't find any dates on this product ! try another image please"

            # Sort our dates by confidence then date
            best_dates = sorted(found_dates, key=lambda x: (x[2], x[0]), reverse=True)
            # Take the best guess
            expiry_date, original_format, confidence = best_dates[0]
            today = datetime.now()
            
            # How many days since expiration
            days_diff = (expiry_date.date() - today.date()).days
            nice_date = expiry_date.strftime('%d-%m-%Y')
            # is the product expired
            if days_diff < 0:
                status = "EXPIRED"
                time_msg = f"{abs(days_diff)} days ago"
            else:
                status = "NOT EXPIRED"
                time_msg = f"{days_diff} days remaining"

            # summarise everythiong to display thm
            result = f"Expiration Date: {nice_date}\n"
            result += f"Original Format: {original_format}\n"
            result += f"Status: {status}\n"
            result += f"Time: {time_msg}"

            return result
            
        except Exception as e:
            print(f"something is worng: {str(e)}")
            return " found a date but cant tell if it's expired."
    
    def _clean_date_string(self, text):
        """kick out everything thats not part of the date"""
        # work on strings
        text = str(text).strip()
        # some patterns that are not part of the date but often appear near to them in the text
        filler_words = [
            'best before', 'best by', 'use by', 
            'expiry', 'expiration', 'exp', 
            'date', 'sell by', 'valid until'
        ]
        
        for word in filler_words:
            text = re.sub(r'(?i)' + word, '', text)
        text = text.strip()
        
        # Handle the tricky YYYYMM/DD format                  -- # Ai generated code for the specific error types found on random image in testing.
        if re.match(r'^\d{6}/\d{1,2}$', text):
            y, m, d = text[:4], text[4:6], text.split('/')[1]
            return f"{y}/{m}/{d}"
        
        return text
    
    def _looks_like_date(self, text):
        date_pattern = r'\d+[-/.,]\d+|^\d{6,8}$'
        return bool(re.search(date_pattern, text))
    
    def _parse_date(self, text):
        text = text.strip()
        # Format:  (20240402)
        if re.match(r'^\d{8}$', text):
            try:
                y, m, d = int(text[:4]), int(text[4:6]), int(text[6:8])
                # fast validation
                if 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y, m, d)
            except ValueError:
                pass
        
        # Format: YYYYMM (202401)
        if re.match(r'^\d{6}$', text):
            try:
                y, m = int(text[:4]), int(text[4:6])
                if 1 <= m <= 12:
                    # Default to 1st of month when day not specified
                    return datetime(y, m, 1)
            except ValueError:
                pass
        
        # Format: (2022.07.19)
        if re.match(r'^\d{4}[.]\d{2}[.]\d{2}$', text):
            try:
                y = int(text[:4])
                m = int(text[5:7])
                d = int(text[8:10])
                if 1 <= m <= 12 and 1 <= d <= 31:
                    return datetime(y, m, d)
            except ValueError:
                pass
        
        #  standard formats as a fallback mechanism
        date_formats = [
            # day first
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            
            # Mmonth first 
            '%m/%d/%Y', '%m-%d-%Y', '%m.%d.%Y',
            
            # year first 
            '%Y/%m/%d', '%Y-%m-%d', '%Y.%m.%d',
            
            # month year only
            '%m/%Y', '%m-%Y', '%m.%Y',
            
            # year month only
            '%Y/%m', '%Y-%m', '%Y.%m'
        ]
        
        # retry try hard until any one of that works up
        for fmt in date_formats:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                # No match, try the next format
                continue
        
        # finaslly
        return None 