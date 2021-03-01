# Здесь расположим имитатор ответов счетчика
import random
import struct
from datetime import date, datetime, timedelta
import xml.etree.ElementTree as xmltree
import time
import os
from xml.dom import minidom
import json

# Для начала пропишем наш файл со значениями
path = '/'.join((os.path.abspath(__file__).replace('\\', '/')).split('/')[:-1])
times = 1

# Получаем файл с параметрами
valuesbank = xmltree.parse(path + '/values.xml').getroot()


def parse_values():
    """Итак у нас есть функция чтения знаачений - Это ваажно"""
    # Сначала читаем наш JSON
    try:
        jsonfile = open(path + '/values.json')
        json_text = jsonfile.read()
        valuesbank = json.loads(json_text)
    except:
        valuesbank = xmltree.parse(path + '/values.xml').getroot()

    return valuesbank


# Набор скоростей
def switch_energ_baudrates(case):
    return {
        b'0': 300,
        b'1': 600,
        b'2': 1200,
        b'3': 2400,
        b'4': 4800,
        b'5': 9600,
    }.get(case, None)


# РАсчет ВСС
def calcbcc(rx):
    lrc = 0
    for x in rx:
        lrc += x
    lrc &= 0x7f
    lrc = hex(lrc)
    lrc = int(lrc, 16)
    return struct.pack('B', lrc)


# Класс имитатор
class SimulatorMeterEnergomera:
    """
     Эмулятор Счетчика ЭНЕРГОМЕРА 303\301
    """
    # Поля котоыре нужны для составления пакетов по протоколу МЭК
    soh = b'\x01'
    stx = b'\x02'
    etx = b'\x03'
    ack = b'\x06'
    nak = b'\x15'
    cr = b'\r'
    lf = b'\n'
    data = b'\x06\x06\x06'
    dataargs = b''
    readen_args = b''
    lbrace = b''
    rbrace = b''
    c = b''
    # Тип полученной команды
    type = None
    # Генерируемый ответ
    answer = b''
    # Запрос
    _response = bytearray()

    # Ответ на вопрос
    response_answer = None
    # ЗАпрос который используется
    request = None

    # НАШ СЛОВАРЬ ЗНАЧЕНИЙ СЧЕТЧИКА
    valuesbank = {}
    # Список типов ответов
    answerbank = {
        'hello': None,
        'confirm': None,
        'auth': bytes(ack),
        'CMD': b'',
        'None': b''}

    # Список ассоциаций тегов
    args = {}
    # Список ассоциаций запросов
    tags = {}

    def __init__(self, request=b'\x01B0\x03u'):
        """
        Здесь инициализируем все значения с которыми можно будет работать. Это важно

        Подача параметра не обязательна
        :param request: Команда - по умолчанию стоит команда нет - Если подразумевается рабоат с обьектом класса - не подавать.
        """
        # Переопределяем основные поля :
        # Поле Ответа
        self.response_answer = None
        # Поле запроса
        self.request = None
        # Переопределяем байтовые Тэги - Нужны для поиска нужного ТЭГА по запросу
        self.tags = {
            b'FREQU': 'Freq',
            b'POWPP': 'P',  #
            b'POWEP': 'PS',
            b'POWPQ': 'Q',  # QC , QA , QB
            b'POWEQ': 'QS',  # QS
            # b'COS_f': 'CF',
            b'COS_f': 'kP',
            b'VOLTA': 'U',
            b'CURRE': 'I',
            b'CORUU': 'Ang',
            b'ET0PE': 'A+',
            b'ET0PI': 'A-',
            b'ET0QE': 'R+',
            b'ET0QI': 'R-',
            b'ENDPE': 'dA+',
            b'ENDPI': 'dA-',
            b'ENMPE': 'MA+',
            b'ENMPI': 'MA-',
            b'EADPE': 'dCA+',
            b'EADPI': 'dCA-',
            b'EADQE': 'dCR+',
            b'EADQI': 'dCR-',
            b'EAMPE': 'MCA+',
            b'EAMPI': 'MCA-',
            b'EAMQE': 'MCR+',
            b'EAMQI': 'MCR-',
            b'ENDQE': 'dR+',
            b'ENDQI': 'dR-',
            b'ENMQE': 'MR+',
            b'ENMQI': 'MR-',
            b'GRAPE': 'DPP+',
            b'GRAPI': 'DPP-',
            b'GRAQE': 'DPQ+',
            b'GRAQI': 'DPQ-',
            # UPD : ЖУрналы
            # ВЫХОД ЗА ПРЕДЕЛЫ ФАЗОВОГО ЗНАЧЕНИЯ
            b'JOVER': 'Journal',
            # ФАЗа вкл/выкл
            b'PHASE': 'Journal',
            # Корекция часов
            b'JCORT': 'Journal',
            # вскрытие счетчика
            b'DENIA': 'Journal',
            # Электронная пломба - плока выдает ошибку
            b'ELOCK': 'Journal',
            # Журанл программирования
            b'ACCES': 'Journal'
        }

        # Определяем наш словарь который содержит значения данных
        self.valuesbank = \
            {
                "const": 1.0,
                "kI": 0.99,
                "kU": 0.99,
                "isAm": True,
                "isClock": True,
                "isCons": True,
                "isDst": False,
                "isRm": True,
                "isRp": True,
                "isTrf": True,
                "cTime": 30,
                "DayConsDepth": 44,
                "DayDepth": 44,
                "MonConsDepth": 13,
                "MonDepth": 12,
                "VarConsDepth": 0,
                "serial": "009218054000006",
                "dDay": 44,
                "cArrays": 1,
                "model": "CE303",

                # БУФЕР
                'Journal': ['ERROR - buffer empty']
            }

        # Теперь - Определяем путь до xml которая содержит конфигурацию счетчика
        path = '/'.join((os.path.abspath(__file__).replace('\\', '/')).split('/')[:-1])

        # ВЫБРАНА ЭНЕРГОМЕРА 303
        counter_meter = path + '/Counters/CE303.xml'

        # Читаем эти данные из xml
        self._counter = EMeter(counter_meter)

        # Служебные настройки - хз для чего
        self.times = 1
        self.datecheck = int(self._counter.datecheckmode)
        self.respondtimeout = int(self._counter.respondtimeout) * 0.001
        self.datecheckcount = 1

        # Теперь загружаем внутрение показатели счетчика -
        # Сначала Получаем дату
        self.time_now = datetime.now()
        # После загружаем xml
        self.__load_parametrs_from_xml()

        # После этого перезаписываем его нужным нам JSON
        self.__parse_JSON()

        # Серийный порт - ПОКА ФУНКЦИОНАЛ ВЫРЕЗАН
        # self._serial = ser

        # Переопределяем перемсенные оссновных команд
        self.start = b''
        self.address = b''
        self.exclam = b''
        self.bcc = b''
        self.c = b''
        self.d = b''
        self.v = b''
        self.z = b''
        self.y = b''
        self.eot = b''
        # Инициализируем наш адресс
        self._counter_address = self._counter.address.encode()

        # ТЕПЕРЬ ГОТОВЫ К РАБОТЕ :
        # разобрать запрос и сгенерировать ответ
        self.request = request
        self._response = request
        # Запускаем -
        self.response_answer = self.__parse_request()
        # после того как дали ответ - записываем дату ответа
        self.record_timenow()

    # -------------------------------ОСНОВНАЯ КОМАНДА РАБОТЫ С ВИРТУАЛЬНЫМ СЧЕТЧИКОМ------------------------------------

    def command(self, command):
        """
        Основной метод работы со счетчиком  без его перезапуска.

        :param command: Сюда пихаем команду на которую надо получить ответ
        :return: И получаем наш ответ
        """
        # разобрать запрос и сгенерировать ответ
        self.request = command
        self._response = command
        # Запускаем -
        self.response_answer = self.__parse_request()
        # после того как дали ответ - записываем дату ответа
        self.record_timenow()

        return self.response_answer

    # -------------------------------СЛУЖЕБНЫЕ КОМАНДЫ РАБОТЫ С ВИРТУАЛЬНЫМ СЧЕТЧИКОМ----------------------------------
    # Функция загрузки параметров из values.xml
    def __load_parametrs_from_xml(self):
        """
        В Этом методе загружаем параметры в наш valuesbank из xml - Даныный метод - обязательный

        :return:
        """
        # Парсим файл
        valuesbank = xmltree.parse(path + '/values.xml').getroot()
        # Берем словарь
        valuesbank_dict = {}
        # Загружаем сначала таймштамп -
        # Он идет обычным словарем
        valuesbank_dict.update(valuesbank.attrib)
        # Теперь проходимся по каждому элементу
        for child in valuesbank:
            valuesbank_dict[child.attrib['code']] = child.text

        # Теперь изменяем таймштамп на текущий системный
        valuesbank_dict['time'] = self.time_now
        # СОХРАНЯЕМ ЭТО ПО КЛЮЧУ - Now
        self.valuesbank['NOW'] = valuesbank_dict

    # Функция Парсинга джейсон и заполнение данных поверх нашей xml
    def __parse_JSON(self):
        """
        Функция Парсинга джейсон и заполнение данных поверх нашей xml

        :return:
        """
        try:
            jsonfile = open(path + '/values.json')
            json_text = jsonfile.read()
            import json
            primary_valuesbank = json.loads(json_text)
        except:
            print('Не удалось прочитать JSON, используются значения по умолчанию')
            primary_valuesbank = None

        # Если он не пустой , то переформатируем до нужного вида
        if primary_valuesbank is not None:
            vals = primary_valuesbank.get('vals')

            # Проверяем валидацию json
            try:
                element = vals[0]["tags"][0]["tag"]

                # ТЕПЕРЬ НАДО ПОНЯТЬ МЫ ПОЛУЧИЛИ ЖУРНАЛЫ ИЛИ НЕТ
                if element in ['event', 'eventId', 'journalID']:
                    # если получили журналы , то записываем их в буффер журналов

                    self.__adding_journal_values(vals)
                # иначе - опускаем в перезапись по таймштапам
                else:
                    self.__adding_values_from_json(vals)
            except:
                print('***ERROR : ВАЛИДАЦИЯ JSON НЕУСПЕШНА***')

        # else:
        #     self.values_dict_with_timestamp = {datetime.now(): None}

    def __adding_values_from_json(self, vals):
        """
        Добавление значений из JSON  в наш банк значений

        :return:
        """
        # дЕЛАЕМ СЛОВАРЬ
        valuesbank_dict = {}
        # Начинаем перебирать наш словарь
        for i in range(len(vals)):
            tags_dict = {}
            # Если нет

            # ЗАПОЛНЯЕМ НАШ СЛОВАРЬ ЗНАЧЕНИЯМИ
            for x in range(len(vals[i]["tags"])):
                tag = vals[i]["tags"][x]["tag"]
                val = vals[i]["tags"][x]["val"]
                tags_dict[tag] = val
            # ПОСЛЕ ЧЕГО ПЕРЕВОДИМ ЭТОТ СЛОВАРЬ ЗНАЧЕНИЙ ДОСТУПНЫМ ПО UNIX TIME в качестве ключа
            # а не - лучше использовать юникс тайм
            unix_time = vals[i]["time"]
            valuesbank_dict[unix_time] = tags_dict
        # СТАВИМ ПОСЛЕДНЫЙ ТАЙМШТАМП В КАЧЕСТВЕ ЗНАЧЕНЯИ ПО УМОЛЧАНИЮ
        self.valuesbank['time'] = unix_time
        # ПОСЛЕДНИЙ ТАЙМШТАМП обновляем ключ NOW
        self.valuesbank['NOW'].update(valuesbank_dict[unix_time])
        # остальные таймштампы записываем в основной словарь
        self.valuesbank.update(valuesbank_dict)

    def __adding_journal_values(self, json_values):
        """
        Данный метод нужен для нормального парсинга значений журналов - и добавления их в буффер в правильном виде
        :param values_dict:
        :return:
        """

        # Сделаем словарь для определеняи позиции байта
        # в нем - журнал айди отдает позицию бита

        # Журнал айди берется согласно протоколу

        byte_position = \
            {
                20: 3,
                21: 0,
                22: 4,
                23: 1,
                24: 5,
                25: 2,

                9: 0,
                10: 1,
                11: 2,
                1: 6,

                6: 3,
                3: 5,

            }

        # Создаем буффер определенной длины - а именно количеству таймштампов в JSON
        journal_buffer = [None] * len(json_values)
        # Теперь - берем и правильно его заполняем
        for i in range(len(json_values)):
            # Сначала берем время
            timestamp = datetime.fromtimestamp(json_values[i]['time'])
            # Теперь делаем из него запис
            timestamp = str(timestamp.day) + '-' + str(timestamp.month) + '-' + str(timestamp.year)[-2:] + '-' + \
                        str(timestamp.hour) + '-' + str(timestamp.minute) + '-'

            # Теперь что делаем - Проходимся по значениям журнала
            tags_dict = {}
            for x in range(len(json_values[i]["tags"])):
                # Теперь что нам надо - вывезти все значения
                tag = json_values[i]["tags"][x]["tag"]
                val = json_values[i]["tags"][x]["val"]
                tags_dict[tag] = val
            # Теперь можно делать с ними разные манипуляции

            # Буффер - Выход за пределы минимального\максимального значения напряжения фазы
            if tags_dict['journalID'] in [20, 21, 22, 23, 24, 25]:
                # Берем позицию байта
                position = byte_position[tags_dict['journalID']]
                # упаковываем наш байт
                value_bytes = ''
                for byte in range(6):
                    # Если натыкаемся на позицию что нам нужна -
                    if byte in [position]:
                        value_bytes = value_bytes + str(tags_dict['event'])
                    # Иначе - Оставляем пустым
                    else:
                        value_bytes = value_bytes + '0'
                # Переворачиваем нашу строку
                value_bytes = value_bytes[::-1]
                # Переводим в десятичный инт
                value_bytes = int(value_bytes, 2)
                # И после чего добавляем к нашей строке записи
                journal_record = timestamp + str(value_bytes)
                # После чего добавляем ее по индексу в массив

            # Буффер - Включение/выключение фазы , включение выключения счетчика
            elif tags_dict['journalID'] in [1, 9, 10, 11]:

                # Берем позицию байта
                position = byte_position[tags_dict['journalID']]
                # упаковываем наш байт
                value_bytes = ''
                for byte in range(8):
                    # Если натыкаемся на позицию что нам нужна -
                    if byte in [position]:
                        value_bytes = value_bytes + str(tags_dict['event'])
                    # Иначе - Оставляем пустым
                    else:
                        value_bytes = value_bytes + '0'
                # Переворачиваем нашу строку
                value_bytes = value_bytes[::-1]
                # Переводим в десятичный инт
                value_bytes = int(value_bytes, 2)
                # И после чего добавляем к нашей строке записи
                journal_record = timestamp + str(value_bytes)
                # После чего добавляем ее по индексу в массив

            # Буффер - Корекция времени
            elif tags_dict['journalID'] in [2]:
                # Берем значение времени - изменяем
                timestamp = timestamp.replace('-', '/')
                # Добавляем к нему цифру на которую изменили
                value_bytes = tags_dict['event']
                journal_record = timestamp + str(value_bytes)
                # После чего добавляем ее по индексу в массив
            # Буффер - Несанкционированный доступ (вскрытие/закрытие заводской крышки)
            elif tags_dict['journalID'] in [8]:
                # Здесь все просто - добавляем время
                journal_record = timestamp[:-1]

            # Журнал тарифов
            elif tags_dict['journalID'] in [6]:
                journal_record = timestamp + '8'


            # Журнал Сброса накопленных параметров
            elif tags_dict['journalID'] in [3]:
                journal_record = timestamp + '32'

            # ИНАЧЕ - ЗАПОЛНЯЕМ НАШ БуФЕР ошибкой
            else:
                journal_record = 'ERR12'

            # после чего заполянем буффер
            journal_buffer[tags_dict['eventId'] - 1] = journal_record
        Journal = {'Journal': journal_buffer}
        self.valuesbank.update(Journal)

    # --------------------------------------------------------------------------------------------------------------
    # -------------------------------ОСНОВНАЯ ЛОГИКА РАБОТЫ ВИРТУАЛЬНОГО СЧЕТЧИКА ----------------------------------
    # --------------------------------------------------------------------------------------------------------------
    # разобрать запрос и сгенерировать ответ
    def __parse_request(self):
        """
        Служебная команда для парсинга запроса и отдачи ответа
        :return:
        """
        # Переопределяем
        request = self.request

        # Структурируем
        self.start = struct.pack('b', request[0])
        #
        try:
            self.__parse_comand(command=self.start)
        except:
            # Итак - если у нас лажанула команда - то отправляем команду НЕ ПОНЕЛ
            print('*************************НЕ ПРАВИЛЬНАЯ КОМАНДА*************************\n ',
                  '*************************** ПЕРЕЗАПРАШИВАЕМ ***************************')
            self.type = 'CMD'
            self.answerbank['CMD'] = self.nak

        # Делаем ответ:
        # Определяем тип команд
        response = self.__makeanswer(self.type)

        return response

    # Делаем ответ
    def __makeanswer(self, anstype):  # make answer
        """
        МЕТОД ДЛЯ ТОГО ЧТОБ СДЕЛАТЬ ОТВЕТ НА ЗАПРОС

        :param anstype:
        :return:
        """
        # ПО ТИПУ ЗАПРОСА ОПРЕДЕЛЯЕМ ОТВЕТ ЧЕРЕЗ СЛОВАРЬ ОТВЕТОВ
        self.answer = self.answerbank[anstype]

        return self.answer

    # --------------------------------------------------------------------------------------------------------------
    # --------------------------------------------Рабочие методы----------------------------------------------------
    # --------------------------------------------------------------------------------------------------------------
    #     Служебный метод парсинга команды
    def __parse_comand(self, command):
        """
        ЗДЕСЬ - ОПРЕДЕЛЯЕМ ПО ЗАГОЛОВКУ ТИП КОМАНДЫ _ И СООТВЕТСВЕННО ПИХАЕМ В НУЖНЫЙ РАЗДЕЛ
        :param command:
        :return:
        """
        if b'/' in command:
            self.__reqhello()
        elif self.ack in command:
            self.__confirm()
        elif self.soh in command:
            self.__prog()
        else:
            self.__empty()

    # ---------------------------------------------Обработка команд--------------------------------------------------
    # Тип ответа "плоха"
    def __empty(self):
        """Тип ответа плохо - Возвращаем пустоту и соответственно связь обрывается - см протокол обмена"""
        self.type = 'None'

    # тип ответа "ПРИВЕТ"
    def __reqhello(self):
        """Данный ментод нужен для составления ответа на ПРИВЕТ и возникновения первичной связи"""
        # разбираем ответ на "Привет"
        if len(self._response) > 1 and struct.pack('b', self._response[1]) == b'?':
            self.start += struct.pack('b', self._response[1])
            self.type = 'hello'
            if struct.pack('b', self._response[4]) == '!'.encode():
                self.address = bytes(self._response[2:4])
                self.exclam = struct.pack('b', self._response[4])
            else:
                self.address = bytes(self._response[2:5])
                self.exclam = struct.pack('b', self._response[5])
            self.cr = struct.pack('b', 13)
            self.lf = struct.pack('b', 10)

        # Делаем ответ на "Привет"
        self.answerbank['hello'] = \
            bytes(
                b'/EKT5' + self._counter.name.encode() + self._counter.version.encode() + self.cr + self.lf
            )

    # данынй метод нужен для обмена информаций после привет
    def __confirm(self):
        """ ДАнный метод нужен для установления связи после первичного привет и обмена конфигуррацией счетчика """
        # Разбираем вопрос к режиму программирования
        self.type = 'confirm'
        self.v = struct.pack('b', self._response[1])
        self.z = struct.pack('b', self._response[2])
        self.y = struct.pack('b', self._response[3])
        self.cr = struct.pack('b', self._response[len(self._response) - 2])
        self.lf = struct.pack('b', self._response[len(self._response) - 1])
        self.cr = struct.pack('b', 13)
        self.lf = struct.pack('b', 10)

        # Делаем ответ на запрос программирования
        self.answerbank['confirm'] = \
            bytes(
                self.soh +
                b'P0' +
                self.stx +
                b'(' + self._counter_address + b')'
                + self.etx
                + calcbcc(b'P0' + self.stx + b'(' + self._counter_address + b')' + self.etx)
            )

    # создать ответ на запросы авторизации и данных
    def __prog(self):

        """
        Данный метод нужен для составления нормального ответа после того как перешли в режим программирования -
        Здесь используется Сценарий обмена тип С -

        Здесь описана вся логика обмена основынми командами
        :return:
        """

        if self._response[1] is not None:
            self.c = struct.pack('b', self._response[1])
            # блок авторизации
            if self.c == b'P':  # auth block
                self.type = 'auth'
                self.d = struct.pack('b', self._response[2])
                self.stx = struct.pack('b', self._response[3])
                self.lbrace = struct.pack('b', self._response[4])
                self.data = self._response[5:len(self._response) - 3]
                if self.data != self._counter.password.encode():
                    print(u'Пароль не совпал пароль счетчика{0} и пароль УМ{1}'.format(str(
                        self._counter.password, self.data)))
                    f = open(self.log, 'a')
                    timestamp = '>' + str(datetime.now().strftime("%d.%m.%y %H:%M:%S")) + '>'
                    f.writelines(timestamp + '\n')
                    f.writelines(u'Пароль не совпал пароль счетчика{0} и пароль УМ{1}'.format(str(
                        self._counter.password, self.data)) + '\n')
                    f.close
                    return
                self.rbrace = struct.pack('b', self._response[len(self._response) - 3])
            # блок запроса данных - основные страдания проходят именнов этом блоке -
            # Здесь уже нельзя быть косипошей чтоб Ничего не сломать
            elif self.c == b'R':  # data request block
                self.type = 'CMD'
                tmp = self.stx
                self.d = struct.pack('b', self._response[2])
                self.stx = struct.pack('b', self._response[3])
                # Парсим всю команду в кодирвоке энергомеры - Нужна чтоб вытащить время
                self.comand_energomera_protocol = self._response[4:-2]
                # Парсим просто команду, без скобок
                self.data = self._response[4:9]
                # получение данных в первый раз
                # Пытаемся по команде узнать что надо отвечать
                try:  # getting data first time

                    # Итак , опускаем в нашу функцию парсинга времени
                    # Опускаем нашу команду в словарь со всеми командами которые учтены тут
                    self.__definion_datetime()

                    self.dataargs = self.args.get(self.data, self.get_random_bytes)(self, 1)
                except Exception as e:
                    print('ОШИБКА',e)
                self.lbrace = struct.pack('b', self._response[9])
                self.readen_args = bytes(self._response[10:len(self._response) - 3])
                self.rbrace = struct.pack('b', self._response[len(self._response) - 3])
                # проверяем, нужно ли использовать дополнительные аргументы
                if len(self.readen_args) == 0:  # check if we have to use additional arguments
                    tmp += bytes(self.data + self.lbrace + self.dataargs + self.rbrace + self.cr + self.lf)
                    t = 2
                    self.answerbank['CMD'] = tmp + self.etx + calcbcc(tmp[1:] + self.etx)
                    # получение дополнительных данных, если запрос требует нескольких данных
                    while t <= times:  # getting more data if request is requiring multiple data
                        try:
                            self.dataargs = self.args.get(self.data, self.get_random_bytes)(self, t)
                        except Exception as e:
                            print('ОШИБКА',e)
                        tmp += bytes(self.data + self.lbrace + self.dataargs + self.rbrace + self.cr + self.lf)
                        self.answerbank['CMD'] = tmp + self.etx + calcbcc(tmp[1:] + self.etx)
                        t += 1
                else:
                    t = 2
                    tmp += bytes(
                        self.data + self.lbrace + self.dataargs + self.rbrace + self.cr + self.lf)
                    self.answerbank['CMD'] = tmp + self.etx + calcbcc(tmp[1:] + self.etx)
                    # получение дополнительных данных, если запрос требует нескольких данных
                    while t <= times:  # getting more data if request is requiring multiple data
                        try:
                            self.dataargs = self.args.get(self.data, self.get_random_bytes)(self, t)
                        except Exception as e:
                            print('ОШИБКА',e)
                        tmp += bytes(
                            self.data + self.lbrace + self.dataargs + self.rbrace + self.cr + self.lf)
                        self.answerbank['CMD'] = tmp + self.etx + calcbcc(tmp[1:] + self.etx)
                        t += 1
            # БЛок записи
            elif self.c == b'W':
                self.type = 'CMD'
                self.answer = b''
                # Отправляем Ок
                self.answerbank['CMD'] = self.ack

            elif self.c == b'B':
                self.type = 'CMD'
                self.d = struct.pack('b', self._response[2])
                self.answer = b''
                self.answerbank['CMD'] = b''
            # self.etx = struct.pack('b', self._response[len(self._response) - 2])
            self.etx = struct.pack('b', 3)
            # ПЫтаемся запокавать это
            try:
                self.bcc = struct.pack('b', self._response[len(self._response) - 1])

            # Если не получилось сразу , то запаковываем это альтернативно- ЭТО ОЧЕНЬ ВАЖНЫЙ МОМЕНТ
            #                   UPD
            # !!!!!Дело в том что энергомера использует протокол передачи 7е1!!!!!!
            # Это означает что в одном БАЙТЕ 7 БИТ
            # НЕТ , НЕ ТЕХ БИТ ЧТО В БАГАЖНИКЕ
            # ДА , В ШКОЛЕ УЧИЛИ ЧТО ИХ 8 как в денди
            # НО ЭТО НЕ ДЕНДИ А ЭНЕРГОМЕРА
            except:
                pack = self._response[len(self._response) - 1]
                # ПРИНУДИТЕЛЬНО ЗАПОКОВЫВАЕМ
                bcc_byte = pack.to_bytes(8, byteorder='big', signed=True)

                # Альтернативные пути запоковывания
                # unpack_1 = pack // 100
                # unpack_2 = pack % 100
                # bcc1 = struct.pack('b', unpack_1)
                # bcc2 = struct.pack('b', unpack_2)
                # bcc  = bcc1 + bcc2
                self.bcc = bcc_byte

    # -----------------------Служебные методы для перезаписи Значений Относительно времени-----------------------------
    # ДАнная функция нужна чтоб определить тип даты-времени в запросе
    def __definion_datetime(self):
        """Данная команда нужна чтоб найти необходимое время - Это важно, если читаем по глубине времени!!!"""

        type_datetime = \
            {
                # Срез по дням
                b'ENDPE': 'd',
                b'ENDPI': 'd',
                b'ENDQE': 'd',
                b'ENDQI': 'd',
                # Срез по месяцам
                b'ENMPE': 'M',
                b'ENMPI': 'M',
                b'ENMQE': 'M',
                b'ENMQI': 'M',
                # Срез по дням потребление
                b'EADPE': 'dC',
                b'EADPI': 'dC',
                b'EADQE': 'dC',
                b'EADQI': 'dC',
                # Срез по месяцам потребление
                b'EAMPE': 'MC',
                b'EAMPI': 'MC',
                b'EAMQE': 'MC',
                b'EAMQI': 'MC',
                # профили мощности первого архива электросчетчика - те что каждые пол часа
                b'GRAPE': 'DP',
                b'GRAPI': 'DP',
                b'GRAQE': 'DP',
                b'GRAQI': 'DP',

                # МГНОВЕННЫЕ ПОКАЗАНИЯ !!!
            }
        # Ищем нашу команду в списке выше
        type_date = type_datetime.get(self.data)

        if type_date is not None:
            # Далее опускаем в функцию перезаписи нашего попаденца
            self.__rewrited_value_dict(type_date)

    # Метод для перезаписи нашего банка значений для нужного времени!!!
    def __rewrited_value_dict(self, type_date):
        """
        Итак этот метод перезаписывает изначальные значения в зависимости от таймштампа
        :param type_date: тип даты
        :return:
        """
        # Здесь нам понадобятся регульрные выражения чтоб не колхозить
        import re
        energomera_command_protocol = self.comand_energomera_protocol
        # Теперь парсим дату - Она в скобках
        if type_date == 'd':
            # итак - Работаем Только с днем
            request_date = re.findall(r'\d{2}\.\d{1,2}\.\d{2}', str(energomera_command_protocol.decode()))
            # Теперь после того как вытащили дату ее можно употребить В ФОРМАТЕ ДД , ММ, ГГ
            request_date = request_date[0].split('.')
            # Собираем нашу дату
            # find_date = int(time.mktime(find_date.timetuple()))
            find_date = self.__consrtuct_date_by_find(year=int('20' + str(request_date[2])),
                                                      month=int(request_date[1]),
                                                      day=int(request_date[0])
                                                      )
            # И поскольку это энергомера - прибавляем один день
            energomera_delta = timedelta(days=1)
            # переводим из юникс тайм в нормальный вид , и прибомвляем день
            energomera_time = datetime.fromtimestamp(find_date) + energomera_delta
            # после чего обратно запаковываем в юнекс тайм
            find_date = time.mktime(energomera_time.timetuple())

        elif type_date == 'M':
            # итак - Работаем c месяцем
            request_date = re.findall(r'\d{1,2}\.\d{2}', str(energomera_command_protocol.decode()))
            # Теперь после того как вытащили дату ее можно употребить В ФОРМАТЕ ММ, ГГ
            request_date = request_date[0].split('.')
            # Собираем нашу дату
            month = int(request_date[0]) + 1
            year = int('20' + str(request_date[1]))
            # А теперь фокус - если у нас получилось перебор , переводим часы

            if month > 12:
                month = 1
                year = year + 1

            find_date = self.__consrtuct_date_by_find(
                year=year,
                month=month,
                day=1
            )

        elif type_date == 'dC':
            # итак - Работаем Только с днем
            request_date = re.findall(r'\d{2}\.\d{1,2}\.\d{2}', str(energomera_command_protocol.decode()))
            # Теперь после того как вытащили дату ее можно употребить В ФОРМАТЕ ДД , ММ, ГГ
            request_date = request_date[0].split('.')
            # Собираем нашу датy
            # Теперь переводим это все в Unixtime
            # find_date = int(time.mktime(find_date.timetuple()))
            find_date = self.__consrtuct_date_by_find(year=int('20' + str(request_date[2])),
                                                      month=int(request_date[1]),
                                                      day=int(request_date[0])
                                                      )

        elif type_date == 'MC':
            # итак - Работаем c месяцем
            request_date = re.findall(r'\d{1,2}\.\d{2}', str(energomera_command_protocol.decode()))
            # Теперь после того как вытащили дату ее можно употребить В ФОРМАТЕ ММ, ГГ
            request_date = request_date[0].split('.')
            # Собираем нашу дату
            month = int(request_date[0])
            year = int('20' + str(request_date[1]))
            # А теперь фокус - если у нас получилось перебор , переводим часы

            if month > 12:
                month = 1
                year = year + 1

            find_date = self.__consrtuct_date_by_find(
                year=year,
                month=month,
                day=1
            )

        elif type_date == 'DP':
            # итак - Работаем с получасом
            request_date = re.findall(r'\d{1,2}\.\d{1,2}\.\d{2}.\d{1,2}', str(energomera_command_protocol.decode()))
            # Теперь после того как вытащили дату ее можно употребить В ФОРМАТЕ ДД , ММ, ГГ, номер получаса
            request_date = request_date[0].split('.')
            # Собираем нашу датy
            # Теперь переводим это все в Unixtime
            # Итак - Ищем день
            find_date = self.__consrtuct_date_by_find(year=int('20' + str(request_date[2])),
                                                      month=int(request_date[1]),
                                                      day=int(request_date[0])
                                                      )

            # И поскольку это энергомера - прибавляем один день
            # energomera_delta = timedelta(days=1)
            # переводим из юникс тайм в нормальный вид , и прибомвляем день
            # energomera_time = datetime.fromtimestamp(find_date) + energomera_delta
            # после чего обратно запаковываем в юнекс тайм
            # find_date = time.mktime(energomera_time.timetuple())
            # Теперь к этому дню надо добавить нужное колличество минут
            timesDP = timedelta(minutes=30 * int(request_date[3]))

            # Переводим это в юнекс тайм и плюсуем
            find_date = datetime.fromtimestamp(find_date)
            find_date = find_date + timesDP
            # И переводим обрвтно в юникс тайм
            find_date = int(time.mktime(find_date.timetuple()))

        else:
            # НЕ УДАЛОСЬ ПРЕОБРАЗОВАТЬ ДАТУ
            find_date = int(time.mktime(datetime.now().timetuple()))
        try:
            # А после ищем значения по этой дате
            # --
            # values_dict = self.values_dict_with_timestamp[find_date]
            # --
            values_dict = self.valuesbank.get(find_date)
            # --
            if values_dict is not None:
                # Теперь что делаем - Одновляем наш список до нужных значений !!!
                correct_values_dict = {}
                for key in values_dict.keys():
                    correct_values_dict[type_date + str(key)] = values_dict[key]

                # После чего обновляем наш список
                self.valuesbank['NOW'].update(correct_values_dict)

        except KeyError:
            print('   ***ERROR НЕ УДАЛОСЬ НАЙТИ ВРЕМЯ ***\n', find_date)
            pass

    def __consrtuct_date_by_find(self, year: int = 0, month: int = 0, day: int = 0, hour: int = 0, minute: int = 0):

        """
        Итак - очень важная хрень - конструктор нужной даты для последующего ее поиска- Это важно!!
        :return:
        """
        # ИТАК - ЕСЛИ ГОД , МЕСЯЦ , ЧИСЛО ИЛИ ЧТО ТО ИЗ ЭТОГО НЕ ЗАДАВАЛОСЬ ПО КАКОЙ ТО ПРИЧИНЕ - ПЕРЕОПРЕДЕЛЯЕМ НА
        # ТЕКУЩЕЕ
        if year == 0:
            year = self.time_now.year

        if month == 0:
            month = self.time_now.month

        if day == 0:
            day = self.time_now.day

        find_date = datetime.now()
        find_date = datetime.replace(find_date,
                                     year=year,
                                     month=month,
                                     day=day,
                                     hour=hour,
                                     minute=minute,
                                     second=0,
                                     microsecond=0
                                     )
        # Теперь переводим это все в Unixtime
        find_date = int(time.mktime(find_date.timetuple()))

        # А ТЕПЕРЬ ВОЗВРАЩАЕМ В ЗАД
        return find_date

    # -----------------------------------------------------------------------------------------------------------------
    # ----------------------------------МЕТОДЫ ДЛЯ ПОИСКА НУЖНЫХ ДАННЫХ------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------
    #  Показатели энергии на конец дня , месяц , и моментные показатели
    def __get_bytes_for_energy_and_set_times_by_El_Energy(self, t):
        """
        Здесь считываем значения для ElMomentEnergy , ElDayEnergy , ElMonthEnergy

            МОМЕНТНЫЕ показатели энергии

            :param t:
            :return:
            """
        global times
        times = 6
        # Генерируем рандомно все это
        if self._counter.random == '1':
            var = "%.3f" % (1000 * random.random())

        # ЕСли не стоит рандомно то делаем это все по шаблону
        else:
            # Берем тэг что нам нужен
            tag = str(self.tags.get(self.data)) + str(t - 1)
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag]) / 1000
            # Теперь берем и округляем
            var = float('{:.6f}'.format(var))
            var = str(var)
            # Если ломается - то идем по старому сценарию
        return var.encode()

    # Значения Напряжения
    def __get_bytes_for_Volts(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = "%.3f" % (float(219) + 10 * random.random())
        else:
            # ЕСли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен

            tag_dict = {0: 'A', 1: 'B', 2: 'C'}
            tag = str(self.tags.get(self.data)) + str(tag_dict[t - 1])

            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag])
            var = str(var)
        return var.encode()

    # Значения Q
    def __get_bytes_for_Power(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = str("%.3f" % random.random())
        else:
            # ЕСли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен
            tag = str(self.tags.get(self.data)) + str(t - 1)
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag])
            var = str(var)
            # Если ломается - то идем по старому сценарию
        return var.encode()

    def __get_bytes_for_PowerPS(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = str("%.3f" % random.random())
        else:
            # ЕСли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен
            tag = str(self.tags.get(self.data))
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag]) / 1000
            var = str(var)
            # Если ломается - то идем по старому сценарию
        return var.encode()

    def __get_bytes_for_PowerQS(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = str("%.3f" % random.random())
        else:
            # ЕСли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен
            tag = str(self.tags.get(self.data))
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag]) / 1000
            var = str(var)
            # Если ломается - то идем по старому сценарию
        return var.encode()

    def __get_bytes_for_PowerABC(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = str("%.3f" % random.random())
        else:
            # ЕСли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен

            tag_dict = {0: 'A', 1: 'B', 2: 'C'}
            tag = str(self.tags.get(self.data)) + str(tag_dict[t - 1])
            # tag = str(self.tags.get(self.data)) + str(t - 1)
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag]) / 1000
            var = str(var)
            # Если ломается - то идем по старому сценарию
        return var.encode()

    def __get_bytes_for_Power_PA_PB_PC(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = str("%.3f" % random.random())
        else:
            # ЕСли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен

            tag_dict = {0: 'A', 1: 'B', 2: 'C'}
            tag = str(self.tags.get(self.data)) + str(tag_dict[t - 1])
            # tag = str(self.tags.get(self.data)) + str(t - 1)
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag]) / 1000
            var = str(var)
            # Если ломается - то идем по старому сценарию
        return var.encode()

    # Сила ТОКА
    def __get_bytes_Current(self, t):

        global times
        times = 3
        if self._counter.random == '1':
            var = str("%.3f" % random.random())
        else:

            # Еcли не стоит рандомно то делаем это все по шаблону
            # Берем тэг что нам нужен

            tag_dict = {0: 'A', 1: 'B', 2: 'C'}
            tag = str(self.tags.get(self.data)) + str(tag_dict[t - 1])
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag])
            var = str(var)
            # Если ломается - то идем по старому сценарию

        return var.encode()

        # УГОЛ

    def __get_bytes_for_Angles(self, t):  # angles

        global times
        times = 3
        if self._counter.random == '1':
            var = "%.1f" % (100 * random.random())
        else:

            tag_dict = {0: 'AB', 1: 'BC', 2: 'AC'}
            # Берем тэг что нам нужен
            tag = str(self.tags.get(self.data)) + str(tag_dict[t - 1])
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag])
            var = str(var)
            # Если ломается - то идем по старому сценарию

        return var.encode()

    # cosinus
    def __get_bytes_for_Cos(self, t):  # cosinus

        global times
        times = 4
        if self._counter.random == '1':
            var = str("%.2f" % random.random())
        else:
            # Берем тэг что нам нужен
            # Ставим нужный словарь для поулчения значений
            key_dict = {0: 'S', 1: 'A', 2: 'B', 3: 'C', }
            tag = str(self.tags.get(self.data)) + str(key_dict[t - 1])
            # Теперь по значению этого тэга ищем значение в нашем словаре

            var = float(self.valuesbank['NOW'][tag])
            var = str(var)

        return var.encode()

    # значения профиля мощности
    def __get_bytes_for_PowerProfQpQmPpPm(self, t):  # power profile values

        time.sleep(self.respondtimeout)
        global times
        times = 1
        if self._counter.random == '1':
            var = "%.2f" % (100 * random.random())
        else:

            tag = str(self.tags.get(self.data))
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag]) / 1000
            var = str(var)
        return var.encode()

    # -----------------------------------------------------------------------------------------------------------------
    # Методы генерации данных

    # Серийник
    def __get_counter_snumber(self, t):  # seril number

        global times
        times = 1
        return str(self._counter.snumber).encode()

    # Номер модели

    def __get_counter_model(self, t):  # counter model

        global times
        times = 1
        # Параметр котоырй парсится из настроек - Couters
        # Подробнее смотри протокол энергомеры - Команда MODEL
        model = str(self._counter.model)
        return model.encode()



    # energy values - ПОКАЗАТЕЛИ ЭНЕРГИИ
    def __get_bytes_for_energy_and_set_times(self, t):  # energy values
        # А теперь очень важная вещь - пытаемся вытащить из команды значения что идут в скобках
        global times
        times = 6
        if self._counter.random == '1':
            var = "%.3f" % (1000 * random.random())
        else:
            tag = str(self.tags.get(self.data)) + str(t - 1)

            query = 'Value[@code="' + tag + '"]'
            var = str(valuesbank.find(query).text)
        return var.encode()

    # частота
    def __get_frequ(self, t):  # frequency

        global times
        times = 1
        if self._counter.random == '1':
            return b'50.00'
        else:
            tag = str(self.tags.get(self.data))
            # Теперь по значению этого тэга ищем значение в нашем словаре
            var = float(self.valuesbank['NOW'][tag])
            var = str(var)

            return var.encode()

    # общие значения для других тегов
    def __get_bytes_general_and_set_times(self, t):  # general values for other tags

        global times
        times = 3
        if self._counter.random == '1':
            return str("%.3f" % random.random()).encode()
        else:
            tag = str(self.tags.get(self.data)) + str(t - 1)
            query = 'Value[@code="' + tag + '"]'
            var = str(valuesbank.find(query).text)
            return var.encode()

    # общие случайные значения для неподдерживаемых запросов и тегов
    def get_random_bytes(self, test=1, t=1):  # general random values for unsupported requests and tags

        global times
        times = 1
        var = "%.3f" % random.random()
        return var.encode()

    def __get_taver(self, t):  # taver
        """Период интегрирования, мин - Интервал времени усреднения значений профиля нагрузки"""

        global times
        times = 1
        cTime = self.valuesbank['cTime']
        cTime = str(cTime)
        return cTime.encode()

    def __get_NGRAP(self, t):
        """
        Количество суточных профилей нагрузки, хранимых в счетчике при заданном времени усреднения TAVER
         ПОКА НЕ ИСПОЛЬЗУЕТСЯ
        """

        NGRAP = 99
        NGRAP = str(NGRAP)
        return NGRAP.encode()

    # trsum
    def __get_trsum(self, t):  # trsum
        'РАЗРЕШЕНИЕ НА ПЕРЕХОД НА ЗИМНЕЕ ВРЕМЯ'

        global times
        times = 1

        # Здесь - берем из наших настроек
        isDst = self.valuesbank['isDst']

        # ЗДЕСЬ берем и меняем булевы параметры на 1 и 0
        if isDst:
            isDst = 1

        else:
            isDst = 0

        isDst = str(isDst)
        return isDst.encode()

    def __get_pacce(self, t):

        global times
        times = 1
        return b'01'

    # Коэффициент преобразования по напряжению
    def __get_kU(self, t):
        global times
        times = 1
        values = float(self.valuesbank['NOW']['kU'])
        values = str(values)
        return values.encode()

    # Коэффициент преобразования по току
    def __get_kI(self, t):
        global times
        times = 1
        values = float(self.valuesbank['NOW']['kI'])
        values = str(values)
        return values.encode()

    # -----------------------------------------------------------------------------------------------------------------
    # ----------------------------------        МЕТОДЫ ДЛЯ ЖУРНАЛОВ    ------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------
    def __get_JournalValues(self, t):
        """
        Метод для работы с ЖУРНАЛАМИ

        :param t:
        :return:
        """
        global times
        times = len(self.valuesbank['Journal'])

        # Получаем ТЭГ
        tag = str(self.tags.get(self.data))
        # Теперь по значению этого тэга ищем значение в нашем словаре
        values = str
        # values_list = str(self.valuesbank[tag])
        # for i in values_list:
        #     values = values + '(' + str(values_list[i]) + ')'
        values = str(self.valuesbank[tag][t - 1])

        return values.encode()

    # -----------------------------------------------------------------------------------------------------------------
    # текущая дата
    def __datenow(self, t):  # current date
        time.sleep(self.respondtimeout)
        global times
        times = 1
        if self.datecheck == 1:
            if self.datecheckcount == 1:
                today = date.fromtimestamp(1441043940)
                # self.datecheckcount = 2
            if self.datecheckcount == 2:
                today = date.fromtimestamp(1441054800)
                # self.datecheckcount = 3
            if self.datecheckcount == 3:
                today = date.fromtimestamp(1441054800)
                # self.datecheckcount = 4
            if self.datecheckcount == 4:
                today = date.fromtimestamp(1441054800)
                self.datecheckcount = 0
        else:
            today = date.today()
        self.datecheckcount += 1

        return str(today.strftime("0%w.%d.%m.%y")).encode()

    # Текущее время
    def __timenow(self, t):  # current time
        global times
        times = 1
        time.sleep(self.respondtimeout)
        if self.datecheck == 1:
            now = datetime.fromtimestamp(2)
        elif self.datecheck == 2:
            now = datetime.fromtimestamp(1)
        else:

            self.time_now = datetime.now()

            now = self.time_now.time()

            # now = datetime.now().time()

        # ЗАПИСЫВАЕМ ВРЕМЯ
        return str(now.strftime("%H:%M:%S")).encode()

    # Запись в файл текущего времени - ЭТО ОЧЕНЬ ВАЖНО

    def record_timenow(self):

        # Теперь переводим все это в Unixtime
        Unix_time = self.time_now.timestamp()
        # Делаем словарь
        timestamp_dict = {'time': int(Unix_time)}
        # Переводим в JSON
        timestamp_json = json.dumps(timestamp_dict)
        # А После записываем
        path_values = path + '/Counters/' + 'Meter_Timestamp.json'
        a = open(path_values, 'w')
        a.write(timestamp_json)
        a.close()

    # Определитель типов ответа

    # Command types list
    # Список типов команд
    cmdbank = {b'/': __reqhello,
               ack: __confirm,
               soh: __prog}
    cmdbank.setdefault(None, __empty)

    # # Requests association list
    # Список ассоциаций запросов

    args = {b'DATE_': __datenow,
            b'TIME_': __timenow,
            b'MODEL': __get_counter_model,
            b'SNUMB': __get_counter_snumber,
            b'TRSUM': __get_trsum,
            b'FREQU': __get_frequ,
            b'POWPP': __get_bytes_for_Power_PA_PB_PC,
            b'POWPQ': __get_bytes_for_PowerABC,
            b'POWEP': __get_bytes_for_PowerPS,
            b'POWEQ': __get_bytes_for_PowerQS,
            b'COS_f': __get_bytes_for_Cos,
            b'VOLTA': __get_bytes_for_Volts,
            b'CURRE': __get_bytes_Current,
            b'CORUU': __get_bytes_for_Angles,
            # Мгновенный показатель А+
            b'ET0PE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ET0PI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ET0QE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ET0QI': __get_bytes_for_energy_and_set_times_by_El_Energy,

            b'ENDPE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENDPI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENMPE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENMPI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EADPE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EADPI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EADQE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EADQI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EAMPE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EAMPI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EAMQE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'EAMQI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENDQE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENDQI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENMQE': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ENMQI': __get_bytes_for_energy_and_set_times_by_El_Energy,
            b'ECDPE': __get_bytes_for_energy_and_set_times,
            b'ECDPI': __get_bytes_for_energy_and_set_times,
            b'ECDQE': __get_bytes_for_energy_and_set_times,
            b'ECDQI': __get_bytes_for_energy_and_set_times,
            b'ECMPE': __get_bytes_for_energy_and_set_times,
            b'ECMPI': __get_bytes_for_energy_and_set_times,
            b'ECMQE': __get_bytes_for_energy_and_set_times,
            b'ECMQI': __get_bytes_for_energy_and_set_times,
            b'GRAPE': __get_bytes_for_PowerProfQpQmPpPm,
            b'GRAPI': __get_bytes_for_PowerProfQpQmPpPm,
            b'GRAQE': __get_bytes_for_PowerProfQpQmPpPm,
            b'GRAQI': __get_bytes_for_PowerProfQpQmPpPm,
            b'TAVER': __get_taver,
            b'PACCE': __get_pacce,
            b'PLOCK': __get_pacce,
            b'PDENI': __get_pacce,
            b'PPHAS': __get_pacce,

            b'FCVOL': __get_kU,
            b'FCCUR': __get_kI,
            b'NGRAP': __get_NGRAP,

            # UPD : ЖУрналы
            # ВЫХОД ЗА ПРЕДЕЛЫ ФАЗОВОГО ЗНАЧЕНИЯ
            b'JOVER': __get_JournalValues,
            # ФАЗа вкл/выкл
            b'PHASE': __get_JournalValues,
            # Корекция часов
            b'JCORT': __get_JournalValues,
            # вскрытие счетчика
            b'DENIA': __get_JournalValues,

            # Электронная пломба - плока выдает ошибку
            b'ELOCK': __get_JournalValues,

            # Журанл программирования
            b'ACCES': __get_JournalValues,

            }


# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------

class EMeter:
    def __init__(self, xmlpath):
        xmldoc = minidom.parse(xmlpath)
        self.name = xmldoc.getElementsByTagName('name')[0].firstChild.data
        self.address = xmldoc.getElementsByTagName('address')[0].firstChild.data
        self.password = xmldoc.getElementsByTagName('password')[0].firstChild.data
        self.snumber = xmldoc.getElementsByTagName('snumber')[0].firstChild.data
        self.maker = xmldoc.getElementsByTagName('maker')[0].firstChild.data
        self.version = xmldoc.getElementsByTagName('version')[0].firstChild.data
        self.model = xmldoc.getElementsByTagName('model')[0].firstChild.data
        self.random = xmldoc.getElementsByTagName('random')[0].firstChild.data
        self.datecheckmode = xmldoc.getElementsByTagName('datecheck')[0].firstChild.data
        self.respondtimeout = xmldoc.getElementsByTagName('respondtimeout')[0].firstChild.data
