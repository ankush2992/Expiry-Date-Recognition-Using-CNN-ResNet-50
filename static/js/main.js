let currentImageData = null;

// Run when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Get HTML elements
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('imageInput');
    const preview = document.getElementById('imagePreview');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const resultsSection = document.getElementById('results-section');
    const boxesContainer = document.getElementById('boundingBoxes');
    const analysisSection = document.getElementById('analysis-section');
    
    // Hide sections initially
    resultsSection.style.display = 'none';
    analysisSection.style.display = 'none';
    
    // Show image when selected
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
                boxesContainer.innerHTML = '';
            }
            reader.readAsDataURL(file);
        }
    });
    
    // Handle form submit
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            alert('Please select an image first');
            return;
        }
        
        // Show loading spinner
        loadingDiv.style.display = 'block';
        resultsDiv.innerHTML = '';
        boxesContainer.innerHTML = '';
        
        // Create data to send
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // Step 1: Detect dates
            const response = await fetch('/detect', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            currentImageData = data;
            resultsSection.style.display = 'block';
            
            if (response.ok) {
                if (data.detections && data.detections.length > 0) {
                    // Show results
                    let html = '<h3>Detection Results</h3>';
                    
                    data.detections.forEach((item, index) => {
                        html += `
                            <div class="result-item">
                                <div class="date-text">Date ${index + 1}: ${item.paddle_text || 'Unknown'}</div>
                                <div class="confidence">Detection: ${(item.detection_confidence * 100).toFixed(1)}%</div>
                                <div class="confidence ${item.paddle_confidence < 50 ? 'low-confidence' : ''}">
                                    OCR: ${item.paddle_confidence.toFixed(1)}%
                                    ${item.paddle_confidence < 50 ? 'Low confidence' : ''}
                                </div>
                            </div>
                        `;
                    });
                    
                    resultsDiv.innerHTML = html;
                    
                    // Draw boxes on image
                    drawBoxes(data.detections, data.image_width, data.image_height);
                    
                    // Pass detected dates to analyze
                    analyzeImage(file, data.detections);
                } else {
                    resultsDiv.innerHTML = '<div class="error">No dates detected</div>';
                    
                    // Even if no dates detected, try to analyze text
                    analyzeImage(file, []);
                }
            } else {
                resultsDiv.innerHTML = `<div class="error">Error: ${data.error || 'Failed to process'}</div>`;
                analyzeImage(file, []);
            }
        } catch (error) {
            resultsDiv.innerHTML = `<div class="error">Error: ${error.message || 'Connection failed'}</div>`;
            analyzeImage(file, []);
        } finally {
            loadingDiv.style.display = 'none';
        }
    });
    
    // Fix boxes when window size changes
    window.addEventListener('resize', function() {
        if (currentImageData) {
            drawBoxes(
                currentImageData.detections, 
                currentImageData.image_width, 
                currentImageData.image_height
            );
        }
    });
});

// Draw boxes on image
function drawBoxes(detections, imageWidth, imageHeight) {
    const container = document.getElementById('boundingBoxes');
    container.innerHTML = '';
    
    const img = document.getElementById('imagePreview');
    const scale = img.offsetWidth / imageWidth;
    
    detections.forEach((item, index) => {
        const [x1, y1, x2, y2] = item.bbox;
        
        // Create box
        const box = document.createElement('div');
        box.className = 'box';
        box.style.left = `${x1 * scale}px`;
        box.style.top = `${y1 * scale}px`;
        box.style.width = `${(x2 - x1) * scale}px`;
        box.style.height = `${(y2 - y1) * scale}px`;
        
        // Add label
        const label = document.createElement('div');
        label.className = 'box-label';
        label.textContent = `Date ${index + 1}`;
        box.appendChild(label);
        
        container.appendChild(box);
    });
}

// Get text analysis
async function analyzeImage(file, detections = []) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add detected dates to the form data - ensure proper JSON formatting
    if (detections && detections.length > 0) {
        // Make a clean copy of the detections to avoid circular references
        const cleanDetections = detections.map(item => ({
            paddle_text: item.paddle_text || '',
            detection_confidence: item.detection_confidence || 0,
            paddle_confidence: item.paddle_confidence || 0,
            bbox: item.bbox || []
        }));
        
        // Log what we're sending to help debug
        console.log('Sending detections to server:', cleanDetections);
        
        // Add to form data
        formData.append('detections', JSON.stringify(cleanDetections));
        
        // Pre-process detected dates to help with display
        detections.forEach((item, index) => {
            if (item.paddle_text) {
                // Clean up text with regex to handle special formats
                const text = item.paddle_text;
                
                // For formats like "202501/28"
                if (/^\d{6}\/\d{1,2}$/.test(text)) {
                    const year = text.substring(0, 4);
                    const month = text.substring(4, 6);
                    const day = text.split('/')[1];
                    
                    // Add a reformatted version
                    item.formatted_date = `${day}/${month}/${year}`;
                }
                
                // For formats like "20240530"
                else if (/^\d{8}$/.test(text)) {
                    const year = text.substring(0, 4);
                    const month = text.substring(4, 6);
                    const day = text.substring(6, 8);
                    
                    // Add a reformatted version
                    item.formatted_date = `${day}/${month}/${year}`;
                }
                
                // For formats like "2022.07.19"
                else if (/^\d{4}[.]\d{2}[.]\d{2}$/.test(text)) {
                    const year = text.substring(0, 4);
                    const month = text.substring(5, 7);
                    const day = text.substring(8, 10);
                    
                    // Add a reformatted version
                    item.formatted_date = `${day}/${month}/${year}`;
                }
            }
        });
    }
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Show original and translated text
            document.getElementById('originalText').textContent = data.original_text || 'No text found';
            document.getElementById('translatedText').textContent = data.translated_text || 'No text found';
            
            // Handle expiry status
            const analysisResult = document.getElementById('analysisResult');
            const analysisText = data.analysis || 'No expiration date found';
            
            // If we have detected dates but no analysis result, use detected dates directly
            if (analysisText === 'No expiration date found. Please check the image for visible dates.' && detections.length > 0) {
                // Try to parse the first date detection directly in the browser
                for (const item of detections) {
                    if (item.paddle_text) {
                        const dateText = item.paddle_text;
                        const dateObj = parseDetectedDate(dateText);
                        
                        if (dateObj) {
                            // Calculate if expired
                            const now = new Date();
                            const daysDiff = Math.floor((dateObj - now) / (1000 * 60 * 60 * 24));
                            const isExpired = daysDiff < 0;
                            
                            // Create formatted display text
                            const status = isExpired ? "EXPIRED" : "NOT EXPIRED";
                            const timeText = isExpired 
                                ? `${Math.abs(daysDiff)} days ago` 
                                : `${daysDiff} days remaining`;
                                
                            const formattedDate = `${dateObj.getDate().toString().padStart(2, '0')}-${(dateObj.getMonth()+1).toString().padStart(2, '0')}-${dateObj.getFullYear()}`;
                                
                            // Format text with HTML
                            const formattedText = `Expiration Date: ${formattedDate}<br>` +
                                `Original Format: ${dateText}<br>` +
                                `Status: <span class="${isExpired ? 'expired' : 'not-expired'}">${status}</span><br>` +
                                `Time: ${timeText}`;
                            
                            analysisResult.innerHTML = formattedText;
                            
                            // Add additional info about the format
                            if (item.formatted_date) {
                                analysisResult.innerHTML += `<div class="date-format-info">OCR detected "${dateText}" (interpreted as ${item.formatted_date})</div>`;
                            }
                            
                            document.getElementById('analysis-section').style.display = 'block';
                            return; // Exit early since we've handled the date
                        }
                    }
                }
            }
            
            // Format the expiration status
            if (analysisText.includes('EXPIRED')) {
                // Bold the status and colorize
                const formattedText = analysisText
                    .replace(/(Status: )(EXPIRED)/g, '$1<span class="expired">$2</span>')
                    .replace(/(Status: )(NOT EXPIRED)/g, '$1<span class="not-expired">$2</span>')
                    .replace(/\n/g, '<br>');
                
                analysisResult.innerHTML = formattedText;
                
                // Add a clear explanation for special formats
                if (detections.some(d => d.formatted_date)) {
                    const specialFormats = detections
                        .filter(d => d.formatted_date)
                        .map(d => `<div class="date-format-info">OCR detected "${d.paddle_text}" (interpreted as ${d.formatted_date})</div>`)
                        .join('');
                    
                    analysisResult.innerHTML += specialFormats;
                }
            } else {
                analysisResult.textContent = analysisText;
            }
            
            document.getElementById('analysis-section').style.display = 'block';
        } else {
            const analysisResult = document.getElementById('analysisResult');
            analysisResult.textContent = 'Expiration date analysis unavailable';
            document.getElementById('analysis-section').style.display = 'block';
        }
    } catch (error) {
        console.error('Analysis error:', error);
        const analysisResult = document.getElementById('analysisResult');
        analysisResult.textContent = 'Expiration date analysis unavailable';
        document.getElementById('analysis-section').style.display = 'block';
    }
}

// Helper function to parse dates in various formats
function parseDetectedDate(dateText) {
    // For formats with dots like "2022.07.19"
    if (/^\d{4}[.]\d{2}[.]\d{2}$/.test(dateText)) {
        const year = parseInt(dateText.substring(0, 4), 10);
        const month = parseInt(dateText.substring(5, 7), 10) - 1; // JS months are 0-indexed
        const day = parseInt(dateText.substring(8, 10), 10);
        
        if (year >= 2000 && year <= 2100 && month >= 0 && month <= 11 && day >= 1 && day <= 31) {
            return new Date(year, month, day);
        }
    }
    
    // For formats like "202501/28" (YYYYMM/DD)
    if (/^\d{6}\/\d{1,2}$/.test(dateText)) {
        const year = parseInt(dateText.substring(0, 4), 10);
        const month = parseInt(dateText.substring(4, 6), 10) - 1;
        const day = parseInt(dateText.split('/')[1], 10);
        
        if (year >= 2000 && year <= 2100 && month >= 0 && month <= 11 && day >= 1 && day <= 31) {
            return new Date(year, month, day);
        }
    }
    
    // For formats like "20240530" (YYYYMMDD)
    if (/^\d{8}$/.test(dateText)) {
        const year = parseInt(dateText.substring(0, 4), 10);
        const month = parseInt(dateText.substring(4, 6), 10) - 1;
        const day = parseInt(dateText.substring(6, 8), 10);
        
        if (year >= 2000 && year <= 2100 && month >= 0 && month <= 11 && day >= 1 && day <= 31) {
            return new Date(year, month, day);
        }
    }
    
    // For standard formats like "DD/MM/YYYY" or "MM/DD/YYYY"
    const standardFormats = [
        { regex: /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/, yearIdx: 3, monthIdx: 2, dayIdx: 1 }, // DD/MM/YYYY
        { regex: /^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/, yearIdx: 3, monthIdx: 1, dayIdx: 2 }, // MM/DD/YYYY
        { regex: /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/, yearIdx: 1, monthIdx: 2, dayIdx: 3 }  // YYYY/MM/DD
    ];
    
    for (const format of standardFormats) {
        const match = dateText.match(format.regex);
        if (match) {
            const year = parseInt(match[format.yearIdx], 10);
            const month = parseInt(match[format.monthIdx], 10) - 1;
            const day = parseInt(match[format.dayIdx], 10);
            
            if (year >= 2000 && year <= 2100 && month >= 0 && month <= 11 && day >= 1 && day <= 31) {
                return new Date(year, month, day);
            }
        }
    }
    
    // Couldn't parse the date
    return null;
} 