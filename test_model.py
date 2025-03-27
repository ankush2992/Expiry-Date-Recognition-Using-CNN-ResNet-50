import torch
import torchvision.transforms as T
from PIL import Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import cv2
import numpy as np
from ocr_service import OCRService

ocr_service = OCRService()

def get_model(num_classes=5):
    # pre-trained 
    model = fasterrcnn_resnet50_fpn(pretrained=True)
    
    # Change the model to work with our number of classes
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    return model

def process_image(image_path, model, size=640, min_detection_confidence=0.3):
    image = Image.open(image_path)
    original_width, original_height = image.size
    
    # chjanging inmage size for faster processing
    if original_width > original_height:
        new_width = size
        new_height = int(original_height * (size / original_width))
        scale = original_width / size
    else:
        new_height = size
        new_width = int(original_width * (size / original_height))
        scale = original_height / size
    
    image_resized = image.resize((new_width, new_height))
    
    # Prepare image for processing on the the model
    transform = T.Compose([
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Running the model without calculating gradients (faster)
    with torch.no_grad():
        image_tensor = transform(image_resized).unsqueeze(0)
        predictions = model(image_tensor)
    
    # Get predct.. results
    boxes = predictions[0]['boxes'].cpu().numpy()
    scores = predictions[0]['scores'].cpu().numpy()
    labels = predictions[0]['labels'].cpu().numpy()
    
    # Storing all detected dates
    all_detections = []
    
    # checking all detected objects
    for box, score, label in zip(boxes, scores, labels):
        
        if score > min_detection_confidence and label == 1:
            x1, y1, x2, y2 = map(int, box * scale)
            height = y2 - y1
            width = x2 - x1
            padding_x = int(width * 0.20)   # 20% on sides
            padding_y = int(height * 0.20)  # 20%on top/bottom
            
            x1 = max(0, x1 - padding_x)#paddinf
            y1 = max(0, y1 - padding_y)
            x2 = min(original_width, x2 + padding_x)
            y2 = min(original_height, y2 + padding_y)
            
            # chopping the region with the date on iut
            region = image.crop((x1, y1, x2, y2))

            results = ocr_service.read_text(region)
            
            # If we found text, save the detection
            if results['paddle_text']:
                detection = {
                    'paddle_text': results['paddle_text'],
                    'detection_confidence': float(score),
                    'paddle_confidence': float(results['paddle_confidence']),
                    'dimensions': results['dimensions'],
                    'bbox': [x1, y1, x2, y2],
                    'is_date': results['is_date']
                }
                all_detections.append(detection)

    # Sort detections by importance
    def get_detection_priority(detection):
        # Dates  are rewarding also imoprtant (1000 bonus)
        is_date_score = 1000 if detection['is_date'] else 0
        confidence_score = detection['detection_confidence'] * detection['paddle_confidence']
        return is_date_score + confidence_score

    # Sortingf by priority and keep top 3
    sorted_detections = sorted(all_detections, key=get_detection_priority, reverse=True)[:3]
    
    return sorted_detections

def main():
    try:
        # Load the model
        print("Loading model...")
        model = get_model()
        
        # Load saved weights
        checkpoint = torch.load('checkpoints/final_model.pth', map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict']) 
        model.eval()  # evaluation mode
        
        print("Model loaded successfully")

        print("\nProcessing image...")
        image_path = 'test_images/test_image.jpg'
        detected_dates = process_image(image_path, model)
        
        #results
        if len(detected_dates) == 0:
            print("No dates detected in the image")
        else:
            for date in detected_dates:
                print(f"Detected date: {date['paddle_text']}")
                print(f"Detection confidence: {date['detection_confidence']:.2f}")
                print(f"OCR confidence: {date['paddle_confidence']:.2f}")
                print("-" * 30)
            
    except Exception as e:
        print("\nSomething went wrong:")
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()