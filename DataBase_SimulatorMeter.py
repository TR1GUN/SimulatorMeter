# Итак - Здесь расположим класс для работы с БД счетчика.
# в ней будем хранить наши архивные данные счетчика

import sqlite3
import os

from Counters.Config_settings import path


# //-----------------------------------------------------------------------------------------------------------------//
def dict_factory(cursor, row):
    """
    Вспомогательная функция для получения значений из таблицы ввиде dict
    ОЧЕНЬ УДОБНО ,ага

    Принимает - а хз как это обьяснить

    возвращает - даные запроса но только ввиде Dict
    :param cursor:
    :param row:
    :return:
    """
    dict = {}
    for idx, col in enumerate(cursor.description):
        dict[col[0]] = row[idx]
    return dict


# //-----------------------------------------------------------------------------------------------------------------//


class Meter_DataBase:
    """
    Итак - Здесь расположим класс для работы с БД счетчика.
    в ней будем хранить наши архивные данные счетчика

    """

    path_db = path

    def __init__(self, path: str):
        # При инициализации - смотрим - существует ли наша БД
        self.path_db = path + '/values.db'
        # print(self.path_db)
        # инициализируем нашу БД
    #     self.__initialization_database()
    #
    # def __initialization_database(self):
    #     # Пункт первый - Проверяем существует ли этот файл
    #     if not os.path.exists(self.path_db):
    #         # Если нет - То задаем ее
    #         self.create_data_base()
    #
    # def create_data_base(self):
    #     command = '''CREATE TABLE
    #                           IF NOT EXISTS values
    #                       (
    #                       time INT,
    #
    #                       )
    #                 '''
    #
    #     result = self.__execute_comand(command=command)
    #
    # def __execute_comand(self, command):
    #     connection = sqlite3.connect(self.path_db)
    #
    #     connection.row_factory = dict_factory
    #     cursor = connection.cursor()
    #     cursor.execute(command)
    #     table = cursor.fetchall()
    #     connection.commit()
    #     connection.close()
    #     return table
