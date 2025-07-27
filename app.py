from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

from flask import send_from_directory, jsonify
from PyPDF2 import PdfReader
import difflib

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf1' not in request.files or 'pdf2' not in request.files:
        return jsonify({'success': False, 'error': 'Both PDF files are required.'})
    pdf1 = request.files['pdf1']
    pdf2 = request.files['pdf2']
    if not (allowed_file(pdf1.filename) and allowed_file(pdf2.filename)):
        return jsonify({'success': False, 'error': 'Invalid file type.'})
    filename1 = secure_filename(pdf1.filename)
    filename2 = secure_filename(pdf2.filename)
    path1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
    pdf1.save(path1)
    pdf2.save(path2)
    # Save filenames in session or temp file for later steps (for demo, save globally)
    global last_uploaded
    last_uploaded = {'pdf1': filename1, 'pdf2': filename2}
    return jsonify({'success': True})

@app.route('/extract', methods=['POST'])
def extract():
    page1 = int(request.form.get('page1', 1)) - 1
    page2 = int(request.form.get('page2', 1)) - 1
    filenames = last_uploaded
    path1 = os.path.join(app.config['UPLOAD_FOLDER'], filenames['pdf1'])
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], filenames['pdf2'])
    try:
        reader1 = PdfReader(path1)
        reader2 = PdfReader(path2)
        text1 = reader1.pages[page1].extract_text() if page1 < len(reader1.pages) else ''
        text2 = reader2.pages[page2].extract_text() if page2 < len(reader2.pages) else ''
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    global last_extracted
    last_extracted = {'text1': text1 or '', 'text2': text2 or ''}
    return jsonify({'success': True, 'text1': text1 or '', 'text2': text2 or ''})

@app.route('/compare', methods=['POST'])
def compare():
    text1 = request.form.get('text1', '')
    text2 = request.form.get('text2', '')
    # Use difflib to compare at character level
    diff = difflib.ndiff(text1, text2)
    result_html = ''
    result_text = ''
    for part in diff:
        code = part[0]
        char = part[2:]
        if code == '+':
            result_html += f'<span class="diff-added">{char}</span>'
        elif code == '-':
            result_html += f'<span class="diff-removed">{char}</span>'
        else:
            result_html += char
        result_text += part
    global last_result
    last_result = result_text
    return jsonify({'success': True, 'result_html': result_html, 'result_text': result_text})

@app.route('/download', methods=['GET'])
def download():
    # Serve the last comparison result as a text file
    from flask import Response
    global last_result
    return Response(
        last_result,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=comparison_result.txt"}
    )

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    app.run(debug=True)
