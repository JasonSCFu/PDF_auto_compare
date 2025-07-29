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

from io import BytesIO

# Store uploaded PDFs in-memory for the session
session_pdfs = {}

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf1' not in request.files or 'pdf2' not in request.files:
        return jsonify({'success': False, 'error': 'Both PDF files are required.'})
    pdf1 = request.files['pdf1']
    pdf2 = request.files['pdf2']
    if not (allowed_file(pdf1.filename) and allowed_file(pdf2.filename)):
        return jsonify({'success': False, 'error': 'Invalid file type.'})
    # Store PDFs in memory for this session/request
    session_pdfs['pdf1'] = BytesIO(pdf1.read())
    session_pdfs['pdf2'] = BytesIO(pdf2.read())
    return jsonify({'success': True})

@app.route('/extract', methods=['POST'])
def extract():
    page1 = int(request.form.get('page1', 1)) - 1
    page2 = int(request.form.get('page2', 1)) - 1
    try:
        session_pdfs['pdf1'].seek(0)
        session_pdfs['pdf2'].seek(0)
        reader1 = PdfReader(session_pdfs['pdf1'])
        reader2 = PdfReader(session_pdfs['pdf2'])
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
    # Remove all spaces for comparison, but keep original for highlighting
    text1_nospace = ''.join(text1.split())
    text2_nospace = ''.join(text2.split())
    sm = difflib.SequenceMatcher(None, text1_nospace, text2_nospace)
    # Map position in nospace text back to original text
    def map_nospace_to_orig(orig):
        mapping = []
        idx = 0
        for i, c in enumerate(orig):
            if not c.isspace():
                mapping.append(i)
        return mapping
    map1 = map_nospace_to_orig(text1)
    map2 = map_nospace_to_orig(text2)
    result_html1 = ''
    result_html2 = ''
    result_text = ''
    last1 = 0
    last2 = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        # Map nospace indices back to original
        s1 = map1[i1] if i1 < len(map1) else len(text1)
        e1 = map1[i2-1]+1 if i2 > 0 and (i2-1) < len(map1) else s1
        s2 = map2[j1] if j1 < len(map2) else len(text2)
        e2 = map2[j2-1]+1 if j2 > 0 and (j2-1) < len(map2) else s2
        # Add unchanged text
        if s1 > last1:
            result_html1 += text1[last1:s1]
            result_text += text1[last1:s1]
        if s2 > last2:
            result_html2 += text2[last2:s2]
        if tag == 'equal':
            result_html1 += text1[s1:e1]
            result_html2 += text2[s2:e2]
            result_text += text1[s1:e1]
        elif tag == 'replace':
            t1 = text1[s1:e1]
            t2 = text2[s2:e2]
            if t1.strip() == t2.strip():
                result_html1 += t1
                result_html2 += t2
                result_text += t1
            else:
                result_html1 += f'<span class="diff-removed">{t1}</span>'
                result_html2 += f'<span class="diff-added">{t2}</span>'
                result_text += f'-{t1}+{t2}'
        elif tag == 'delete':
            t1 = text1[s1:e1]
            result_html1 += f'<span class="diff-removed">{t1}</span>'
            result_text += f'-{t1}'
        elif tag == 'insert':
            t2 = text2[s2:e2]
            result_html2 += f'<span class="diff-added">{t2}</span>'
            result_text += f'+{t2}'
        last1 = e1
        last2 = e2
    # Add any trailing text
    result_html1 += text1[last1:]
    result_html2 += text2[last2:]
    result_text += text1[last1:]
    global last_result
    last_result = result_text
    return jsonify({'success': True, 'result_html1': result_html1, 'result_html2': result_html2, 'result_text': result_text})
    global last_result
    last_result = result_text
    return jsonify({'success': True, 'result_html1': result_html1, 'result_html2': result_html2, 'result_text': result_text})

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
