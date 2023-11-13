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
    def __init__(self, text, lang):
        self.text: str = text.lower()
        self.__lang: str = lang
        self.__nlp = local_nlps.__getattribute__(self.__lang)
        self.lemma: str = " ".join([token.lemma_ for token in self.__nlp(text)]).lower()

        self.exact = []
        self.exact_lemmed = []
        self.participant = []
        self.imprecise = []

    def __repr__(self):
        return f"Phrase:{self.__lang}:{len(self.text.split())}"

    @logger.catch
    def values(self):
        reply = {'Сверхточное': str(self.exact)[1:-1],
                 'Точное': str(self.exact_lemmed)[1:-1],
                 'Разбитое': str(self.participant)[1:-1],
                 'Частичное': str(self.imprecise)[1:-1]}

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
        self.text = text.replace('\n', '.')
        self.sentences = [Sentence(s_id, x.replace('..', '.').lower(), self.lang, self.nlp)
                          for s_id, x in enumerate(re.split(r'(?<=[.!?\n])\s+', text), start=1)]

    def __repr__(self):
        return f"Text:{self.lang}:{len(self.sentences)}"


class Sentence:
    @logger.catch
    def __init__(self, sent_id, text, lang, nlp):
        self.id_ = sent_id
        self.lang = lang
        self.text: str = text
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
        logger.debug(f"Phrase: {phrase.text}")

        sentence = self.clear_full_sentence()
        matches = re.findall(phrase.text, sentence)

        modified_sentence = re.sub(r'\b' + re.escape(phrase.text) + r'\b', '', sentence)
        self.lemmatized = self.lemmatize(modified_sentence)
        logger.debug(f'Исходный: {sentence}')
        logger.debug(f'Лемма: {self.lemmatized}')

        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=len(matches)))

    @logger.catch
    def __match_exactlemmed(self, phrase: Phrase) -> DefaultMunch:
        sentence = self.lemmatized

        logger.trace(f"Phrase: {phrase.lemma}")

        matches = re.findall(r'\b' + re.escape(phrase.lemma) + r'\b', sentence)
        self.lemmatized = re.sub(r'\b' + re.escape(phrase.lemma) + r'\b', '', sentence)
        logger.trace(f'Лемма: {self.lemmatized}')
        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=len(matches)))

    @logger.catch
    def __match_participant(self, phrase: Phrase) -> DefaultMunch:
        sentence = self.lemmatized
        logger.trace(f"Phrase: {phrase.lemma}")
        str_pattern = r'\b' + r'\b.*?\b'.join(map(re.escape, phrase.lemma.split())) + r'\b'
        return self.__re_search_lemmed(phrase, sentence, str_pattern)

    @logger.catch
    def __match_imprecise(self, phrase: Phrase) -> DefaultMunch:
        lemma_phrase = phrase.lemma.replace(' ', '|^')
        sentence = self.lemmatized
        str_pattern = r'\w*?(^' + lemma_phrase + ')'

        return self.__re_search_lemmed(phrase, sentence, str_pattern)

    @logger.catch
    def __re_search_lemmed(self, phrase, sentence, str_pattern):
        pattern = re.compile(str_pattern)
        matches = re.findall(pattern, sentence)
        self.lemmatized = re.sub(r'\b' + re.escape(phrase.lemma) + r'\b', '', sentence)
        logger.trace(f'Лемма: {self.lemmatized}')
        return as_class(dict(phrase=phrase.text,
                             id_=self.id_,
                             count=len(matches)))

