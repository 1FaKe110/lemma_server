import pandas as pd
import json
from application.parser import Text, Phrase
from loguru import logger


class Application:

    @logger.catch
    def __init__(self, xlsx_filepath: str, save_path: str):
        self.save_path = save_path
        self.results = {}

        with pd.ExcelFile(xlsx_filepath) as reader:
            if ['Текст', 'Ключи'] != reader.sheet_names:
                message = (f'Не верные названия страниц в xlsx файле: {reader.sheet_names}\n'
                           f' - должно быть ["Текст", "Ключи"]')
                raise KeyError(message)

            try:
                self.texts = [Text(raw) for raw in pd.read_excel(reader, 'Текст', header=None)[0]]
                self.keys = [Phrase(raw) for raw in pd.read_excel(reader, 'Ключи', header=None)[0]]
            except ValueError:
                message = f'Файл {xlsx_filepath} поврежден!\n {ValueError}'
                raise RuntimeError(message)

    @logger.catch
    def run(self):
        results = self.calculate()
        self.save(results)
        return self.save_path

    @logger.catch
    def save(self, results):
        logger.info("Сохраняют результаты")

        for text_id, values in results.items():
            logger.info(f"Данные по тексту с id [{text_id}]:")
            logger.info(json.dumps(values, indent=2, ensure_ascii=False))

            save_path = f'{self.save_path}/{text_id}.xlsx'
            logger.debug(f'Сохраняю данные по: {save_path}')

            with pd.ExcelWriter(save_path) as writer:
                logger.debug("Создаю страницу [Ключи]")
                keys_df = pd.DataFrame().from_dict(values).T
                keys_df.to_excel(writer, sheet_name='Ключи', index=True)

                logger.debug("Создаю страницу [Пассажи]")
                sentences = dict(
                    id=[i + 1 for i in range(len(self.texts[text_id - 1].sentences))],
                    text=[t.text for t in self.texts[text_id - 1].sentences]
                )

                sentences_df = pd.DataFrame().from_dict(sentences)
                sentences_df.to_excel(writer, sheet_name='Пассажи', index=False)
                logger.debug("Файл сохранен!")

    @logger.catch
    def calculate(self):
        results = {}
        for text_id, text in enumerate(self.texts, start=1):
            results[text_id] = {}
            logger.debug(f'Считаю текст: {text_id}')
            for phrase in self.keys:

                for sentence in text.sentences:
                    matches = sentence.get_matches(phrase)

                    for row in matches:
                        if matches.__dict__[row]['count'] < 1:
                            continue

                        logger.debug("Найдено совпадение")
                        phrase.__dict__[row].append(
                            matches.__dict__[row]['id_']
                        )

                results[text_id][phrase.text] = phrase.values()
        return results
