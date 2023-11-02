"""
1. Английский ("en") - модель "en_core_web_sm"
2. Немецкий ("de") - модель "de_core_news_sm"
3. Французский ("fr") - модель "fr_core_news_sm"
4. Испанский ("es") - модель "es_core_news_sm"
5. Итальянский ("it") - модель "it_core_news_sm"
6. Португальский ("pt") - модель "pt_core_news_sm"
7. Русский ("ru") - модель "ru_core_news_sm"
python -m spacy download en_core_web_sm
"""
import os
import spacy
from typing import List
from loguru import logger


class Nlps:
    supported: List = ['en_core_web_sm',
                       'de_core_news_sm',
                       'fr_core_news_sm',
                       'es_core_news_sm',
                       'it_core_news_sm',
                       'pt_core_news_sm',
                       'ru_core_news_sm']
    en, de, fr, es, it, pt, ru = [None for _ in range(7)]

    @logger.catch
    def __init__(self):
        self.load_libs()

    @logger.catch
    def load_libs(self):
        logger.info("Подгружаю модели")

        logger.info("Подгружаю ru_core_news_sm")
        self.ru = spacy.load("ru_core_news_sm")

        logger.info("Подгружаю en_core_web_sm")
        self.en = spacy.load("en_core_web_sm")

        logger.info("Подгружаю de_core_news_sm")
        self.de = spacy.load("de_core_news_sm")

        logger.info("Подгружаю fr_core_news_sm")
        self.fr = spacy.load("fr_core_news_sm")

        logger.info("Подгружаю es_core_news_sm")
        self.es = spacy.load("es_core_news_sm")

        logger.info("Подгружаю it_core_news_sm")
        self.it = spacy.load("it_core_news_sm")

        logger.info("Подгружаю pt_core_news_sm")
        self.pt = spacy.load("pt_core_news_sm")

        logger.info("Готово!")

    @logger.catch
    def download_libs(self):
        logger.info("Библиотеки не были найдены. Скачиваю заново")
        for nlp in self.supported:
            state = os.system(f"python -m spacy download {nlp}")
            logger.info(f'{nlp} {"downloaded" if state == 0 else "download failed"}')

