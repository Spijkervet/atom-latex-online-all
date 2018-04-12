import os
import subprocess
import uuid
import json
import zipfile
from urllib.parse import urljoin, urlencode
from functools import reduce
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from time import sleep

pdflatex_error = '! '
UPLOAD_FOLDER_REL = 'uploads/'
UPLOAD_FOLDER = '/var/www/html/uploads/'
ALLOWED_EXTENSIONS = set(['tex', 'zip'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER_REL'] = UPLOAD_FOLDER_REL
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def make_pdf_extension(filename):
    fn = os.path.splitext(filename)[0]
    return fn + ".pdf"

def convert_latex(dir_save_path, compile_file):
    args = ["pdflatex", "-halt-on-error", "-interaction=nonstopmode", "-output-directory", dir_save_path, compile_file]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=dir_save_path)

    stdout, stderr = p.communicate()
    p_status = p.wait()

    if (p_status):
        stdout = stdout.decode("utf-8")
        stdout = stdout.split('\n')
        error_lines = []
        for line in stdout:
            if pdflatex_error in line:
                error_lines.append(line)
        if error_lines:
            print(error_lines)
            return p_status, error_lines

    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=dir_save_path)
    p_status = p.wait()
    return p_status, ""


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            compile_file = 'main.tex'
            if request.form['compile_file']:
                compile_file = request.form['compile_file']

            data = {}
            unique_dir = str(uuid.uuid4().hex)
            dir_save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_dir)
            os.mkdir(dir_save_path)

            # TODO: do what Hidde said about compressing inside zip
            if '.zip' in file.filename:
                z = zipfile.ZipFile(file)
                z.extractall(dir_save_path)
                z.close()
            else:
                file.save(os.path.join(dir_save_path, file.filename))
            error_code, error_msg = convert_latex(dir_save_path, compile_file)
            if not error_code:
                data['status'] = 200
                fn_pdf = make_pdf_extension(compile_file)
                data['url'] = "http://" + reduce(urljoin, [request.host.split(':')[0] + '/', app.config['UPLOAD_FOLDER_REL'] + '/', unique_dir + '/', fn_pdf])
                return json.dumps(data)
            else:
                data['status'] = 500
                data['errors'] = error_msg
                return json.dumps(data)
    return ''
app.run(host='0.0.0.0', debug=True)
