import io
import time
from flask import Flask, request, send_file, render_template_string, jsonify
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

app = Flask(__name__)

# HTML template for the upload form
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Image Processor - Profiling Example</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .upload-form { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 4px; margin: 20px 0; }
        .operations { margin: 20px 0; }
        label { display: block; margin: 10px 0 5px 0; }
    </style>
</head>
<body>
    <h1>Image Processing Service</h1>
    <div class="info">
        <h3>Available Operations:</h3>
        <ul>
            <li><strong>blur</strong> - Apply Gaussian blur</li>
            <li><strong>sharpen</strong> - Sharpen the image</li>
            <li><strong>edge_detect</strong> - Detect edges</li>
            <li><strong>grayscale</strong> - Convert to grayscale</li>
            <li><strong>enhance</strong> - Enhance colors and contrast</li>
            <li><strong>rotate</strong> - Rotate and apply transformations</li>
            <li><strong>noise_reduction</strong> - CPU-intensive noise reduction</li>
        </ul>
    </div>

    <div class="upload-form">
        <h3>Upload and Process Image</h3>
        <form action="/process" method="post" enctype="multipart/form-data">
            <label for="image">Select Image:</label>
            <input type="file" name="image" id="image" accept="image/*" required>

            <label for="operation">Operation:</label>
            <select name="operation" id="operation">
                <option value="blur">Blur</option>
                <option value="sharpen">Sharpen</option>
                <option value="edge_detect">Edge Detect</option>
                <option value="grayscale">Grayscale</option>
                <option value="enhance">Enhance</option>
                <option value="rotate">Rotate</option>
                <option value="noise_reduction">Noise Reduction (CPU intensive)</option>
            </select>

            <br><br>
            <button type="submit">Process Image</button>
        </form>
    </div>

    <div class="info">
        <h3>Health Check:</h3>
        <p>Visit <a href="/health">/health</a> for service status</p>
    </div>
</body>
</html>
"""


def apply_blur(image):
    """Apply Gaussian blur - moderate CPU/memory usage"""
    return image.filter(ImageFilter.GaussianBlur(radius=5))


def apply_sharpen(image):
    """Sharpen image - light processing"""
    return image.filter(ImageFilter.SHARPEN)


def apply_edge_detect(image):
    """Edge detection - moderate processing"""
    return image.filter(ImageFilter.FIND_EDGES)


def apply_grayscale(image):
    """Convert to grayscale - light processing"""
    return image.convert('L')


def apply_enhance(image):
    """Enhance colors and contrast - moderate processing"""
    # Increase color saturation
    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(1.5)

    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.3)

    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)

    return image


def apply_rotate(image):
    """Rotate and transform - memory intensive"""
    # Multiple rotations and transformations
    result = image.rotate(45, expand=True)
    result = result.rotate(-45, expand=True)
    result = result.transpose(Image.FLIP_LEFT_RIGHT)
    return result


def apply_noise_reduction(image):
    """CPU-intensive noise reduction using numpy"""
    # Convert to numpy array for mathematical operations
    img_array = np.array(image)

    # Simulate noise reduction with multiple passes
    # This is intentionally CPU-intensive for profiling purposes
    result = img_array.astype(np.float32)

    # Apply multiple smoothing passes
    for _ in range(3):
        # Simple box filter implementation
        kernel_size = 3
        padded = np.pad(result, ((kernel_size//2, kernel_size//2),
                                  (kernel_size//2, kernel_size//2),
                                  (0, 0)), mode='edge')

        output = np.zeros_like(result)
        for i in range(result.shape[0]):
            for j in range(result.shape[1]):
                output[i, j] = np.mean(
                    padded[i:i+kernel_size, j:j+kernel_size],
                    axis=(0, 1)
                )
        result = output

    # Convert back to uint8
    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


OPERATIONS = {
    'blur': apply_blur,
    'sharpen': apply_sharpen,
    'edge_detect': apply_edge_detect,
    'grayscale': apply_grayscale,
    'enhance': apply_enhance,
    'rotate': apply_rotate,
    'noise_reduction': apply_noise_reduction,
}


@app.route('/')
def index():
    """Home page with upload form"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'image-processor',
        'timestamp': time.time()
    })


@app.route('/process', methods=['POST'])
def process_image():
    """Process uploaded image with specified operation"""
    start_time = time.time()

    # Validate request
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    operation = request.form.get('operation', 'blur')

    if operation not in OPERATIONS:
        return jsonify({'error': f'Invalid operation: {operation}'}), 400

    try:
        # Read image
        image = Image.open(file.stream)

        # Convert RGBA to RGB if necessary
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        # Apply operation
        processed_image = OPERATIONS[operation](image)

        # Save to bytes
        output = io.BytesIO()
        processed_image.save(output, format='JPEG', quality=85)
        output.seek(0)

        processing_time = time.time() - start_time

        return send_file(
            output,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=f'processed_{operation}.jpg',
            max_age=0
        ), 200, {'X-Processing-Time': f'{processing_time:.3f}s'}

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Use port from environment variable (Render requirement) or default to 5000
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
