import os
import secrets
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import google.generativeai as genai
import pypdfium2 as pdfium
from PIL import Image

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max upload size

# Configure Google Gemini/Generative AI API
API_KEY = "AIzaSyAdzP9nGj-gfIWgLEJamwHBV48u6g99FqY"
genai.configure(api_key=API_KEY)

# Global in-memory storage for PDF slide images (indexed by filename)
pdf_content_store = {}


def get_unique_upload_name(filename):
    """Avoid collisions so multiple PDFs with the same base name can coexist."""
    name, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1

    while candidate in pdf_content_store or os.path.exists(
        os.path.join(app.config['UPLOAD_FOLDER'], candidate)
    ):
        candidate = f"{name}_{counter}{ext}"
        counter += 1

    return candidate


def build_uploaded_file_info(filename):
    images = pdf_content_store.get(filename, [])
    return {
        'filename': filename,
        'status': 'Ready',
        'word_count': len(images)  # We display page count in the sidebar
    }

def render_pdf_to_images(filepath):
    """Renders PDF pages directly to PIL images locally using pypdfium2"""
    images = []
    try:
        doc = pdfium.PdfDocument(filepath)
        # Limit to the first 8 pages to optimize context size and request speed
        max_pages = min(len(doc), 8)
        
        for i in range(max_pages):
            page = doc[i]
            # Render at standard scale (1.0x) for highly efficient memory usage
            pil_img = page.render(scale=1).to_pil()
            pil_img.thumbnail((500, 500))
            if pil_img.mode in ("RGBA", "LA", "P"):
                pil_img = pil_img.convert("RGB")
            images.append(pil_img)
            
        print(f"Successfully rendered {len(images)} pages from {os.path.basename(filepath)}")
    except Exception as e:
        print(f"Error rendering PDF pages: {e}")
    return images

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected files'}), 400
    
    uploaded_files_info = []
    
    for file in files:
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            filename = get_unique_upload_name(filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Render all pages to PIL images for direct multimodal visual analysis by Gemma 4
            images = render_pdf_to_images(filepath)
            
            pdf_content_store[filename] = images
            uploaded_files_info.append(build_uploaded_file_info(filename))

    if not uploaded_files_info:
        return jsonify({'error': 'No valid PDF files were uploaded.'}), 400

    all_uploaded_files = [build_uploaded_file_info(filename) for filename in pdf_content_store]
                
    return jsonify({
        'message': f'Successfully uploaded and processed {len(uploaded_files_info)} PDF(s).',
        'files': all_uploaded_files
    })

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json or {}
    question = data.get('question', '').strip()
    model_name = data.get('model', 'models/gemma-4-31b-it')
    selected_files = data.get('files', [])
    
    if not question:
        return jsonify({'error': 'Question is required.'}), 400
        
    # Gather image parts from all selected files
    contents = []
    for filename in selected_files:
        if filename in pdf_content_store:
            contents.extend(pdf_content_store[filename])
            
    if not contents:
        return jsonify({'error': 'No document images found. Please upload at least one PDF first.'}), 400
        
    # Append the prompt containing instructions and user question at the end
    prompt = f"""You are a highly precise PDF Document Assistant. 
Analyze the provided slide/page images visually and answer the user question based strictly on their contents.

Instructions:
- Cite the specific document name when answering.
- If the answer cannot be found in the images, say "I cannot find the answer in the provided documents."
- Do not repeat system constraints, instructions, or the question.

USER QUESTION: {question}

Provide a direct, concise answer below:"""
    contents.append(prompt)

    try:
        # Call Google AI Studio Gemma 4 Multimodal model (without system_instruction parameter to prevent API 500 crashes)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(contents)
        
        # Extract the final answer and filter out the thinking/reasoning parts
        answer_text = ""
        try:
            parts = response.candidates[0].content.parts
            if len(parts) > 1:
                answer_text = parts[-1].text
            else:
                answer_text = response.text
        except Exception as parts_err:
            print(f"Parts extraction failed, falling back to full text: {parts_err}")
            answer_text = response.text
            
        if answer_text:
            return jsonify({'answer': answer_text.strip()})
        else:
            return jsonify({'answer': 'Sorry, the model returned an empty response.'})
            
    except Exception as e:
        print(f"API Error with model {model_name}: {e}")
        return jsonify({'error': f"API Error ({model_name}): {str(e)}"}), 500

@app.route('/clear', methods=['POST'])
def clear_session():
    pdf_content_store.clear()
    try:
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    except Exception as e:
        print(f"Error cleaning folder: {e}")
    return jsonify({'message': 'Session cleared successfully.'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
