import zipfile

import os
from os.path import join, dirname, realpath

from loguru import logger
from munch import DefaultMunch

# flask imports
from flask_cors import CORS
from flask import Flask, request, render_template, jsonify, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# db imports
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# local imports
from application import Application

app = Flask(__name__)
app.secret_key = '12345'  # секретный ключ для сессий
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'  # URI для базы данных SQLite
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'files/uploaded')
app.config['PROCESSED_FOLDER'] = os.path.join(os.getcwd(), 'files/processed')

db = SQLAlchemy(app)
CORS(app)

logger.add("App.log")
as_class = DefaultMunch.fromDict


class File(db.Model):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    download_filename = Column(String, default=None)
    upload_filepath = Column(String, nullable=False)
    download_filepath = Column(String, default=None)
    status = Column(String, nullable=False, default='Загружен')
    process_time = Column(String, default=None)
    uploaded_timestamp = Column(DateTime, nullable=False, default=datetime.now)
    complete_timestamp = Column(DateTime, default=None)

    def __repr__(self):
        return f'Db[{self.__tablename__}]'


def create_zip_archive(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))


# СТРАНИЦЫ ОТДАВАЕМЕ ПОЛЬЗОВАТЕЛЮ

@app.route('/')
@logger.catch
def index():
    files = [f for f in os.listdir(app.config['PROCESSED_FOLDER']) if f != '____.file']
    return render_template('index.html',
                           status='idle',
                           files=files)


@app.route('/ready/<filename>')
@logger.catch
def ready(filename):
    logger.info(f'Файл {filename} готов!')
    return render_template('index.html',
                           status='complete',
                           filename=filename)


@app.route('/processing')
@logger.catch
def processing():
    files = File.query.filter(File.status.in_(['Загружен', 'В обработке'])).all()
    filenames = [file.filename for file in files]
    logger.info(filenames)
    return render_template('processing.html', files=files)


@app.route('/complete')
@logger.catch
def complete():
    files = File.query.filter_by(status='Обработан').all()
    return render_template('complete.html', files=files)


# ЭНДПОИНТЫ API

@app.route('/upload', methods=['POST'])
@logger.catch
def upload():
    """ Загрузка файлов """
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

    old_file = File.query.filter_by(filename=file.filename).first()
    if old_file:
        if old_file.status == 'В обработке':
            message = ("Такой файл в данный момент обрабатывается. "
                       "Дождитесь окончания обработки или загрузите этот файл с другим именем!")
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

    old_file = File.query.filter_by(filename=file.filename).first()
    if old_file:
        logger.info(f"Редактирую предыдущую обработку {file.filename}")
        old_file.download_path = None
        old_file.status = 'Загружен'
        old_file.process_time = None
        old_file.complete_timestamp = None
        old_file.uploaded_timestamp = datetime.now()
    else:
        logger.info(f"Cоздаем новую запись в бд для файла {file.filename}")
        new_file = File(filename=file.filename, upload_filepath=filepath)
        db.session.add(new_file)
    db.session.commit()

    return jsonify(dict(message=f"\n Файл сохранен: {file.filename}",
                        code='info',
                        filename=file.filename))


@app.route('/operate/<filename>')
def operate(filename: str):
    """ Обработка файла """
    file = File.query.filter_by(filename=filename).first()
    if not file:
        message = "Файл не найден в бд"
        logger.error(message)
        return jsonify(dict(message=message,
                            code='error'))

    file.status = 'В обработке'
    db.session.commit()

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
        return change_status_on_exception(message, filename)

    except RuntimeError:
        message = "Файл поврежден. Дальнейшая обработка не возможна"
        logger.error(message)
        return change_status_on_exception(message, filename)

    logger.info(f"Начинаю обработку файла: {filename}")
    start_time = datetime.now()

    try:
        unzipped_dir = lemme.run()
    except Exception as ex:
        logger.error(ex)
        return change_status_on_exception(ex, filename)

    end_time = datetime.now()
    process_time = end_time - start_time

    file = File.query.filter_by(filename=filename).first()
    if file:
        file.process_time = process_time.total_seconds()
        file.complete_timestamp = end_time
        db.session.commit()

    logger.info(f"Создаем архив из папки {unzipped_dir}")
    create_zip_archive(unzipped_dir, down_path)

    logger.info(f"Удаляю временную папку {unzipped_dir}")
    rm_state = os.system(f"rm -rf {unzipped_dir}")
    logger.debug(f'Статус удаления: {rm_state}')
    rm_state = os.system(f"rm {unzipped_dir}")
    logger.debug(f'Статус удаления: {rm_state}')

    logger.info(f"Архив создан: {down_path}")
    file = File.query.filter_by(filename=filename).first()
    if file:
        file.download_filepath = down_path
        file.download_filename = down_path.rsplit('/', 1)[-1]
        file.status = 'Обработан'
        db.session.commit()
        return jsonify(dict(message="Файл обработан и готов для скачивания",
                            code='info'))

    return jsonify(dict(message="Не удалось найти файл в бд",
                        code='error'))


def change_status_on_exception(ex, filename):
    """ Проставление статуса ошибки в бд """

    logger.info(f'Для {filename} проставляю статус ошибки по причине: \n - {ex}')
    file = File.query.filter_by(filename=filename).first()
    if file:
        file.status = 'Ошибка'
        db.session.commit()
    return jsonify(dict(message=ex,
                        code='error'))


@app.route('/download/<filename>')
@logger.catch
def download(filename: str):
    """ Скачивание файла """
    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    logger.debug(f"путь до файла: {file_path}")
    logger.debug(f"Скачиваю файл: {filename}")
    return send_file(file_path,
                     as_attachment=True,
                     download_name=filename)


@logger.catch
def main():
    logger.debug(f"Path: \n"
                 f" - {app.config['UPLOAD_FOLDER']} \n"
                 f" - {app.config['PROCESSED_FOLDER']}")

    logger.debug("Создаю БД")
    with app.app_context():
        db.create_all()

    app.run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
