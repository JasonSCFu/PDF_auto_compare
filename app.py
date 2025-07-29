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
    sm = difflib.SequenceMatcher(None, text1, text2)
    result_html1 = ''
    result_html2 = ''
    result_text = ''
    context_window = 20
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            result_html1 += text1[i1:i2]
            result_html2 += text2[j1:j2]
            result_text += text1[i1:i2]
        elif tag == 'replace':
            t1 = text1[i1:i2]
            t2 = text2[j1:j2]
            # Ignore differences that are only in whitespace (spaces, tabs, newlines, indentation)
            if t1.strip() == t2.strip():
                # Only whitespace/indent difference, treat as equal
                result_html1 += t1
                result_html2 += t2
                result_text += t1
                continue
            # Check context around the diff
            ctx1_before = text1[max(i1-context_window, 0):i1]
            ctx1_after = text1[i2:i2+context_window]
            ctx2_before = text2[max(j1-context_window, 0):j1]
            ctx2_after = text2[j2:j2+context_window]
            context_match = (ctx1_before == ctx2_before) and (ctx1_after == ctx2_after)
            if t1.strip() == '' and t2.strip() == '':
                result_html1 += t1
                result_html2 += t2
                result_text += t1
            else:
                if context_match:
                    result_html1 += ctx1_before + f'<span class="diff-removed">{t1}</span>' + ctx1_after
                    result_html2 += ctx2_before + f'<span class="diff-added">{t2}</span>' + ctx2_after
                    result_text += ctx1_before + f'-{t1}' + ctx1_after + ctx2_before + f'+{t2}' + ctx2_after
                else:
                    result_html1 += ctx1_before + f'<span class="diff-removed context-mismatch">{t1}</span>' + ctx1_after
                    result_html2 += ctx2_before + f'<span class="diff-added context-mismatch">{t2}</span>' + ctx2_after
                    result_text += ctx1_before + f'-[context-mismatch]{t1}' + ctx1_after + ctx2_before + f'+[context-mismatch]{t2}' + ctx2_after
        elif tag == 'delete':
            t1 = text1[i1:i2]
            ctx1_before = text1[max(i1-context_window, 0):i1]
            ctx1_after = text1[i2:i2+context_window]
            if t1.strip() == '':
                result_html1 += t1
                result_text += t1
            else:
                result_html1 += ctx1_before + f'<span class="diff-removed">{t1}</span>' + ctx1_after
                result_text += ctx1_before + f'-{t1}' + ctx1_after
        elif tag == 'insert':
            t2 = text2[j1:j2]
            ctx2_before = text2[max(j1-context_window, 0):j1]
            ctx2_after = text2[j2:j2+context_window]
            if t2.strip() == '':
                result_html2 += t2
                result_text += t2
            else:
                result_html2 += ctx2_before + f'<span class="diff-added">{t2}</span>' + ctx2_after
                result_text += ctx2_before + f'+{t2}' + ctx2_after
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
