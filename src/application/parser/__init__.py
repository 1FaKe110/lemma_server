import json
import re
import string
from loguru import logger

from langdetect import detect, DetectorFactory
from munch import DefaultMunch
from application.parser.nlps import Nlps
import time

as_class = DefaultMunch.fromDict
DetectorFactory.seed = 0
local_nlps = Nlps()


def time_of(function):
    def wrapped(*args):
        start_time = time.time()
        res = function(*args)
        total = time.time() - start_time
        logger.trace(f"Время обработки: {total}")
        return res

    return wrapped


class Phrase:
    def __init__(self, text, url, lang):
        self.text: str = ' '.join(text.lower().split())
        self.url: str = url
        self.__lang: str = lang
        self.__nlp = local_nlps.__getattribute__(self.__lang)
        self.lemma: str = " ".join([token.lemma_ for token in self.__nlp(self.text)]).lower()

        self.exact = []
        self.exact_lemmed = []
        self.participant = []
        self.imprecise = []

    def __repr__(self):
        return f"Phrase:{self.__lang}:{len(self.text.split())}"

    @logger.catch
    def values(self):
        reply = {
            'Сверхточное': str(self.exact)[1:-1],
            'Точное': str(self.exact_lemmed)[1:-1],
            'Разбитое': str(self.participant)[1:-1],
            'Частичное': str(self.imprecise)[1:-1],
            'ссылка': self.url
        }

        self.exact.clear()
        self.exact_lemmed.clear()
        self.participant.clear()
        self.imprecise.clear()

        return reply


class Text:

    @logger.catch
    def __init__(self, text: str):
        self.lang = detect(text)
        self.nlp = local_nlps.__getattribute__(self.lang)
        self.text = ' '.join(text.replace('\n', '.').split())
        self.sentences = [Sentence(s_id, x.replace('..', '.').lower(), self.lang, self.nlp)
                          for s_id, x in enumerate(re.split(r'(?<=[.!?\n])\s+', text), start=1)]

    def __repr__(self):
        return f"Text:{self.lang}:{len(self.sentences)}"


class Sentence:
    @logger.catch
    def __init__(self, sent_id, text, lang, nlp):
        self.id_ = sent_id
        self.lang = lang
        self.text: str = ' '.join(text.split())
        self.__nlp = nlp
        self.lemmatized = None

    def __repr__(self):
        return f"Sentence:{self.lang}:{len(self.text.split())}"

    @logger.catch
    def clear_full_sentence(self):
        return self.text.translate(str.maketrans('', '', string.punctuation)).lower()

    @logger.catch
    def lemmatize(self, text) -> str:
        return " ".join([token.lemma_ for token in self.__nlp(text)]).lower()

    @logger.catch
    @time_of
    def get_matches(self, phrase: Phrase):
        return as_class(
            {'exact': self.__match_exact(phrase),
             'exact_lemmed': self.__match_exactlemmed(phrase),
             'participant': self.__match_participant(phrase),
             'imprecise': self.__match_imprecise(phrase)})

    @logger.catch
    def __match_exact(self, phrase: Phrase) -> DefaultMunch:
        """ Поиск супер точного вхождения в предложение """

        logger.debug(f"Phrase: {phrase.text}")

        sentence = self.clear_full_sentence()
        matches = int(phrase.text in sentence)
        logger.debug(f'| СуперТочное вхождение | \n - {phrase.text = } \n - {sentence = } \n - {matches = }')

        self.lemmatized = self.lemmatize(sentence.replace(phrase.text, ''))
        logger.debug("| СуперТочное вхождение | - удаляю встреченный ключ из предложения")
        logger.debug(f'| СуперТочное вхождение | - Привожу к лемме: {self.lemmatized}')

        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=matches))

    @logger.catch
    def __match_exactlemmed(self, phrase: Phrase) -> DefaultMunch:
        """ Поиск точного вхождения в предложение """

        matches = int(phrase.lemma in self.lemmatized)
        logger.debug(f'| Точное вхождение | \n - {phrase.lemma = } \n - {self.lemmatized = } \n - {matches = }')

        logger.debug("| Точное вхождение | - удаляю встреченный ключ из предложения")
        self.lemmatized = self.lemmatized.replace(phrase.text, '')

        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=matches))

    @logger.catch
    def __match_participant(self, phrase: Phrase) -> DefaultMunch:
        """ Поиск разбитое вхождения в предложение """

        sentence_list = self.lemmatized.split()
        phrase_list = phrase.lemma.split()
        if all(item in sentence_list for item in phrase_list):
            matches = 1
            logger.debug(f'| Разбитое вхождение | \n - {phrase.lemma = } \n - {self.lemmatized = } \n - {matches = }')

            logger.debug("| Разбитое вхождение | - удаляю встреченный ключ из предложения")
            [sentence_list.remove(item) for item in phrase_list]
            self.lemmatized = ' '.join(sentence_list)

        else:
            matches = 0
            logger.debug(f'| Разбитое вхождение | \n - {phrase.lemma = } \n - {self.lemmatized = } \n - {matches = }')
            logger.debug("| Разбитое вхождение | - Ключ не был встречен")

        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=matches))

    @logger.catch
    def __match_imprecise(self, phrase: Phrase) -> DefaultMunch:
        """ Поиск частичного вхождения в предложение """
        matches = int(any(item in self.lemmatized.split() for item in phrase.lemma.split()))
        logger.debug(f'| Разбитое вхождение | \n - {phrase.lemma = } \n - {self.lemmatized = } \n - {matches = }')

        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=matches))
