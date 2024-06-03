FROM cr.yandex/mirror/python:3.10.7-slim-bullseye

WORKDIR /usr/src/app

COPY ./src ./

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download ru_core_news_sm
RUN python -m spacy download pt_core_news_sm
RUN python -m spacy download it_core_news_sm
RUN python -m spacy download es_core_news_sm
RUN python -m spacy download fr_core_news_sm
RUN python -m spacy download de_core_news_sm
RUN python -m spacy download en_core_web_sm

CMD ["ls", "-la", "/usr/src/app/files/"]
EXPOSE 5000
CMD ["python3", "-u", "main.py"]

