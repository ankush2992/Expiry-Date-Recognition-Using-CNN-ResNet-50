from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient
from dotenv import load_dotenv
import os
import io

# Loading environment variables from .env file
load_dotenv()

class AzureVisionService:
    def __init__(self):

        self.vision_endpoint = os.getenv('AZURE_VISION_ENDPOINT')
        self.vision_key = os.getenv('AZURE_VISION_KEY')
        self.translator_key = os.getenv('AZURE_TRANSLATOR_KEY')
        
        if not all([self.vision_endpoint, self.vision_key, self.translator_key]):
            raise ValueError("not all keys are there in env, check the subscription status in azureportal. if its not active anymore")
        
        # Setting up the OCR service
        self.vision_client = ComputerVisionClient(
            endpoint=self.vision_endpoint,
            credentials=CognitiveServicesCredentials(self.vision_key)
        )
        self.vision_client.config.connection.timeout = 15.0  # using 15s timeout- changee to 10 when in production
        
          #   translation service - ()
        self.translator_endpoint = "https://api.cognitive.microsofttranslator.com"
        self.translator_location = "centralindia"
        self.translator_client = TextTranslationClient(
            endpoint=self.translator_endpoint,
            credential=AzureKeyCredential(self.translator_key)
        )

    def extract_text(self, image, translate_to='en'):
        """Extract text from image and translate it to the angreji language"""
        try:
            # Convert image format Azure can use
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)  # Go back to start of byte array

            # point 1: Extract text from image using OCR
            try:
                result = self.vision_client.recognize_printed_text_in_stream(
                    image=img_byte_arr,
                    language='ko',  # Assuming Korean text
                    detect_orientation=True
                )
            except Exception as e:
                print(f"OCR Error: {str(e)}")
                return {
                    'original_text': 'issue: cant connect to Azure Vision API',
                    'translated_text': 'issue: Vision is not in service anymore '
                }

            # point 2: Combine all detected text
            all_text = []
            if result.regions:
                for region in result.regions:
                    for line in region.lines:
                        line_text = " ".join(word.text for word in line.words)
                        all_text.append(line_text)

            original_text = " ".join(all_text)
            
            #send back early if not texr founded.
            if not original_text.strip():
                return {
                    'original_text': 'No text detected in image',
                    'translated_text': 'No text detected in image'
                }

            # point 3: Translate the text
            try:
                translation_input = [{'text': original_text}]
                headers = {'Ocp-Apim-Subscription-Region': self.translator_location}

                # Call translation API
                response = self.translator_client.translate(
                    body=translation_input,
                    to_language=[translate_to],
                    from_language='ko',           # testing to convert only korean language as of now. can add more if needed.
                    headers=headers
                )

                # Get translated text from response
                if response and len(response) > 0:
                    translated_text = response[0].translations[0].text
                    return {
                        'original_text': original_text,
                        'translated_text': translated_text
                    }
                else:
                    return {
                        'original_text': original_text,
                        'translated_text': 'Translation failed - no response'
                    }
                
            except Exception as e:
                print(f"Translation Error: {str(e)}")
                return {
                    'original_text': original_text,
                    'translated_text': f'Translation failed: {str(e)}'
                }

        except Exception as e:
            print(f"General Error: {str(e)}")
            return {
                'original_text': 'Error processing image',
                'translated_text': 'Error processing image'
            } 