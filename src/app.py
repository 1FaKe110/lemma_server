from loguru import logger
from munch import DefaultMunch
from flask_cors import CORS
from flask import Flask, request, render_template, jsonify, send_file, flash, redirect, url_for
import os
from os.path import join, dirname, realpath
import zipfile

from application import Application

as_class = DefaultMunch.fromDict
app = Flask(__name__)
app.secret_key = '12345'  # секретный ключ для сессий
CORS(app)

logger.add("App.log")


def create_zip_archive(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))


@app.route('/')
@logger.catch
def index():
    files = [f for f in os.listdir(app.config['PROCESSED_FOLDER']) if f != '____.file']

    if len(files):
        for file in files:
            logger.info(f" - {file}")

    return render_template('index.html',
                           status='idle',
                           files=files)



@app.route('/upload', methods=['POST'])
@logger.catch
def upload():
    if 'file' not in request.files:
        message = "Файл не найден"
        logger.error(message)
        return jsonify(dict(message=message,
                            code='error'))

    file = request.files['file']

    if file.filename == '':
        message = "Файл не выбран"
        logger.error(message)
        return jsonify(dict(message=message,
                            code='error'))

    file.filename = file.filename.replace(' ', '_')
    filepath = join(dirname(realpath(__file__)), 'files/uploaded', file.filename)
    logger.debug(f"Файл будет сохранен: {filepath}")
    if os.path.exists(filepath):
        os.remove(filepath)
    file.save(filepath)

    logger.info(f"Файл сохранен: {filepath}")

    return jsonify(dict(message=f"\n Файл сохранен: {file.filename}",
                        code='info',
                        filename=file.filename))


@app.route('/operate/<filename>')
def operate(filename):
    up_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    temp_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0])
    os.makedirs(temp_dir_path, exist_ok=True)
    down_path = os.path.join(app.config['PROCESSED_FOLDER'], filename.rsplit('.', 1)[0] + '.zip')
    logger.debug(f'Файл: {up_path}')
    logger.debug(f'Временная папка: {temp_dir_path}')

    try:
        lemme = Application(up_path, temp_dir_path)

    except KeyError:
        message = (f'Не верные названия страниц в xlsx файле\n'
                   f' - должно быть ["Текст", "Ключи"]')
        logger.error(message)
        return jsonify(dict(message=message,
                            code='error'))
    except RuntimeError as CorruptedFileException:
        message = "Файл поврежден. Дальнейшая обработка не возможна"
        logger.error(message)
        return jsonify(dict(message=message,
                            code='error'))

    logger.info(f"Начинаю обработку файла: {filename}")
    unzipped_dir = lemme.run()

    logger.info(f"Создаем архив из папки {unzipped_dir}")
    create_zip_archive(unzipped_dir, down_path)

    logger.info(f"Удаляю временную папку {unzipped_dir}")
    rm_state = os.system(f"rm -rf {unzipped_dir}")
    logger.debug(f'Статус удаления: {rm_state}')
    rm_state = os.system(f"rm {unzipped_dir}")
    logger.debug(f'Статус удаления: {rm_state}')

    logger.info(f"Архив создан: {down_path}")
    return redirect(url_for('ready', filename=filename.rsplit('.', 1)[0] + '.zip'))


@app.route('/ready/<filename>')
@logger.catch
def ready(filename):
    logger.info(f'Файл {filename} готов!')
    return render_template('index.html',
                           status='complete',
                           filename=filename)


@app.route('/download/<filename>')
@logger.catch
def download(filename):
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    logger.debug(f"путь до файла: {file_path}")
    logger.debug(f"Скачиваю файл: {filename}")
    return send_file(file_path,
                     as_attachment=True,
                     download_name=filename)


@logger.catch
def main():
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd()'files/uploaded')
    app.config['PROCESSED_FOLDER'] = os.path.join(os.getcwd(), 'files/processed')

    logger.debug(f"Path: \n"
                 f" - {app.config['UPLOAD_FOLDER']} \n"
                 f" - {app.config['PROCESSED_FOLDER']}")

    app.run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
