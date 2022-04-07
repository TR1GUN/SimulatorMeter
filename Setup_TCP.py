# Итак - Здесь опишем имитатор счетчика сервера

import socket
import time
from Simulator_meter import SimulatorMeterEnergomera
from hexdump import dump
import datetime


class SetupMeter:
    """
    Здесь инициализируем сокет нашего эмулятора счетчика чтоб обращаться к нему по Ethernet
    """
    cid = None
    port = ''
    SimulatorMeter = None
    log_file = None

    def __init__(self,
                 # Здесь указываем :
                 # Порт на котором висит счетчик - Обязательно
                 conect_port,
                 # Данные которые нужно протащить в счетчик
                 data=None,
                 # Серийный номер счетчика - НУЖНО ЧТОБ НЕ ПОТЕРЯТЬСЯ
                 serial=None):

        # Задаем Порт
        self.serv_port = None
        self.port = conect_port

        # Создаем сокет сервера
        serv_sock = self.__create_serv_sock()

        # self.cid = 0
        # -----

        # Создаем  наш счетчик
        self._create_Meter(data=data, serial=serial)
        # self.SimulatorMeter = SimulatorMeterEnergomera()

        # Ожидаем конекта
        self.__connect_socket(serv_sock)

    def _create_Meter(self, data=None, serial=None):
        """
        Здесь создаем наш счетчик
        :return:
        """
        # ЕСЛИ У НАС НЕ НАЛЛ - спускаем серийник
        from copy import deepcopy
        SimulatorEnergomera = deepcopy(SimulatorMeterEnergomera)

        # serial = '009218054000006_' + str(self.port)

        # ЕСЛИ ЗАЖАЮТСЯ ДАННЫЕ И СЕРИЙНИК _ ПОЛЬЗУЕМСЯ ЭТИМ

        SimulatorMeter = SimulatorEnergomera()
        if serial is not None:
            # serial = str(self.port)
            SimulatorMeter.Set_Serial(serial)
        if data is not None:
            #     Здесь Записываем все наши данные в наш счетчик - ЭТО ВАЖНО !!!!
            SimulatorMeter.Set_Data(data=data)

        # Теперь Переоопределяем его
        self.SimulatorMeter = SimulatorMeter

    def __connect_socket(self, serv_sock):

        """
        Метод для самого коннекта - ждем присоеденения и инициализируем ссесию обмена -
        если конекта нет более 20 секунд - отваливаемся по таймауту

        """
        while True:
            try:
                self.client_socket = self.__accept_client_conn(serv_sock)
                # print('режим блокировки', self.client_socket.getblocking())
                self.__session_client()

                # теперь закрываем сокет
                self._close_socket()

            except socket.timeout:
                # print('режим блокировки', self.client_socket.getblocking())

                break

            except Exception as e:
                print('Произошла ошибка', e)

                break

    def __create_serv_sock(self):
        """
        Создание нашего серверного сокета

        :return:
        """

        # self.SimulatorMeter = SimulatorMeterEnergomera()

        serv_sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM,
                                  proto=0)
        serv_sock.bind(('', self.port))

        serv_sock.settimeout(20.0)

        serv_sock.listen()

        return serv_sock

    # Отслеживаем Конект к сокету
    def __accept_client_conn(self, serv_sock):
        """
        Отслеживание коннекта к сокету

        :param serv_sock:
        :return:
        """

        self.client_sock, client_addr = serv_sock.accept()

        # print(f'Client #{self.cid} connected '
        #       f'{client_addr[0]}:{client_addr[1]}')

        client_sock = self.client_sock
        return client_sock

    def __session_client(self):
        """
        Сама сессия обмена -
        читаем данные - ищем команду для ответа

        Если получаем пустоту или команду конца обмена - сбрасываем сессию

        :return:
        """

        # Читаем запрос
        session = True
        while session:
            request = self.__read_request()
            # print('Команда', request)
            if request is None:
                # print(f'Client #{self.cid} unexpectedly disconnected')
                # print('Пришла пустота')
                session = False

            # Если у нас есть команда конец передачи
            elif self.SimulatorMeter.close in request:
                # print('Конец передачи')
                session = False

            else:
                # Формируем ответ
                response = self.__handle_request(request)
                self.__write_response(response)

    # Читаем запрос
    def __read_request(self):

        """
        Читаем команды

        :return:
        """

        # Когда сессия появилась - выставляем заново таймаут
        self._SET_TIMEOUT(0.5)
        # и после этого начинаем читать

        request = bytes()

        # request = bytearray()
        try:

            # итак что делаем - считываем Первый Пакет с сокета
            request = self.client_socket.recv(1024)
            # ЕСЛИ У НАС В ПАКЕТЕ 1
            # - 2 БАЙТА - это неообходимость для первого влючения
            if len(request) == 2:
                while True:

                    chunk = self.client_socket.recv(1024)
                    request = request + chunk

                    # print('вначале было два ', request)
                    # ЕСЛИ У НАС КОНЕЦ ПЕРЕДАЧИ
                    if len(chunk) < 1:
                        break
                    # Клиент преждевременно отключился.
                    if not chunk:
                        # print(' Клиент преждевременно отключился.')
                        break
                    break

            # ЕСЛИ У НАС ОДИН БАЙТ
            if len(request) == 1:
                chunk = self.client_socket.recv(1024)
                request = request + chunk
                # print('вначале был один байт', )

            # ЕСЛИ У НАС ПУСТОТА
            if len(request) < 1:
                # print(' От клиента пришло пустое значение.')
                request = None
            if not request:
                # print(' От клиента не пришло никакой информации.')
                request = None

            # Логируем
            # print('------------------------------- ЧИТАЕМ ДАННЫЕ -----------------------------------')
            # self.log(chunk=request, type_packet=' Полученный ')

            # Возвращаем
            return request

        except ConnectionResetError:
            # Соединение было неожиданно разорвано.
            print('Соединение было неожиданно разорвано.')
            return None
        except Exception as e:
            print(' ОШИБКА Сокета ', e)

            # print('Неизвестная ошибка')
            #
            # print('ЧТО ПРОЧИТАЛИ\n', request)
            return None

    # обрабатывает Запрос
    def __handle_request(self, request):
        """
        Обрабатываем команду
        :param request:
        :return:
        """
        # Здесь Формируем ответ в зависимости от запроса

        response = self.SimulatorMeter.command(request)

        # response = SimulatorMeter(request=request).response
        # print('--------------------------------ОТПРАВЛЯЕМ ОТВЕТ-------------------------')
        # self.log(chunk=response, type_packet=' Отправленный ')
        # print('отправили ', response)
        # return request[::-1]
        return response

    # отправляет клиенту ответ
    def __write_response(self, response):
        # Сделаем так что ответ идет массивом

        #

        self.client_socket.sendall(response)
        time.sleep(1)

    # -----------------------------------------------
    def _SET_TIMEOUT(self, timeout):
        """
        Здесь устанавливаем таймаут на сокет

        :param timeout:
        :return:
        """
        if type(self.client_socket) is socket.socket:
            self.client_socket.settimeout(float(timeout))

    # -----------------------------------------------

    def _close_socket(self):
        # Если ответа нет, закрываем сокет
        self.client_socket.close()

    def log(self, chunk, type_packet: str):
        print('\n!!!!!!!!!!', '!!!!!!!!!!!\n')
        print(type_packet + 'пакет : ', chunk, ' ')
        print(' Его длина : ', len(chunk), '')
        print('Байт код\n', chunk.hex(), '\n')
        print('ДАМП : ', dump(chunk), '')

        try:
            print('Расшифровка :', chunk.decode('ascii'), '\n')
        except UnicodeDecodeError:
            print('Не Удалось расшифровать :', chunk, '\n')

        print1 = str(type_packet) + 'пакет : ' + str(chunk) + '\n'
        print2 = ' Его длина : ' + str(len(chunk)) + '\n'

        print3 = 'ДАМП : ' + str(dump(chunk)) + '\n'

        try:
            print4 = 'Расшифровка : ' + str(chunk.decode('ascii')) + '\n'
        except UnicodeDecodeError:
            print4 = 'Не Удалось расшифровать : ' + str(chunk) + '\n'
        # логируем через файл -
        writen_text = '---------------------------------------------------------\n' + \
                      str(datetime.datetime.now()) + '\n' + \
                      print1 + print2 + print3 + print4


# --------------->
#
# СТАРАЯ ВЕРСИЯ
# class SocketMeters:
#     """
#     Здесь инициализируем сокет нашего эмулятора счетчика чтоб обращаться к нему по Ethernet
#     """
#     cid = None
#     port = ''
#     SimulatorMeter = None
#     log_file = None
#
#     def __init__(self, conect_port, data=None, serial=None):
#
#         # Создаем файл лога
#         self.log_file = write_file.write_log_file(
#             file_name='EmulatorMeter_' + str(time.mktime(datetime.datetime.now().timetuple())) + str('.txt'),
#             writen_text='ЛОГ обмена :', folder='Meter/')
#         # Задаем Порт
#         self.serv_port = None
#         self.port = conect_port
#
#         self.SimulatorMeter = self._create_Meter(data=data, serial=serial)
#
#         # Создаем сокет сервера
#         serv_sock = self.__create_serv_sock()
#
#         self.cid = 0
#         # -----
#
#         self.__connect_socket(serv_sock)
#
#         print('ЗАВЕРШАЕМ')
#
#     def _create_Meter(self, data=None, serial=None):
#         """
#         Здесь создаем наш счетчик
#         :return:
#         """
#
#         # ЕСЛИ У НАС НЕ НАЛЛ - спускаем серийник
#         from copy import deepcopy
#         SimulatorEnergomera = deepcopy(SimulatorMeterEnergomera)
#
#         # serial = '009218054000006_' + str(self.port)
#
#         # ЕСЛИ ЗАЖАЮТСЯ ДАННЫЕ И СЕРИЙНИК _ ПОЛЬЗУЕМСЯ ЭТИМ
#
#         SimulatorMeter = SimulatorEnergomera()
#         if serial is not None:
#             # serial = str(self.port)
#             SimulatorMeter.Set_Serial(serial)
#         if data is not None:
#             #     Здесь Записываем все наши данные в наш счетчик - ЭТО ВАЖНО !!!!
#             SimulatorMeter.Set_Data(data=data)
#
#         return SimulatorMeter
#
#     def __connect_socket(self, serv_sock):
#         # while True:
#         #     if self.cid > 0 :
#         #         break
#         while True:
#             try:
#                 self.client_socket = self.__accept_client_conn(serv_sock)
#
#             except socket.timeout:
#                 # print('Привышен таймаут на подключение')
#                 break
#
#             except Exception as e:
#                 print('ОШИБКА сессии ', e)
#                 break
#             break
#
#
#         # Производим сессию обмена инфой
#         self.__session_client()
#         # Добавляем еще одного пользователя
#         self.cid += 1
#         # while True:
#         #
#         #     try :
#         #         # Производим сессию обмена инфой
#         #         self.__session_client()
#         #         # Добавляем еще одного пользователя
#         #         self.cid += 1
#         #     except :
#         #
#         #         """ОШИБКА СЕССИИ"""
#         #         break
#
#     def __create_serv_sock(self):
#
#         # self.SimulatorMeter = SimulatorMeterEnergomera()
#
#         serv_sock = socket.socket(socket.AF_INET,
#                                   socket.SOCK_STREAM,
#                                   # proto=0
#                                   )
#
#         serv_sock.bind(('', self.port))
#         # print(serv_sock.getsockname())
#         serv_sock.settimeout(20.0)
#         serv_sock.listen(1)
#
#         return serv_sock
#
#     # Отслеживаем Конект к сокету
#     def __accept_client_conn(self, serv_sock):
#
#         client_sock, client_addr = serv_sock.accept()
#
#         # print(f'Client #{self.cid} connected '
#         #       f'{client_addr[0]}:{client_addr[1]}')
#
#         # client_sock = self.client_sock
#         return client_sock
#
#     def __session_client(self):
#         # Читаем запрос
#         session = True
#
#         print('CECCCИИИ')
#         while session:
#             self._SET_TIMEOUT(2)
#             # ЗДЕСЬ обеспечим скорость передачи не более 2 секунд
#             # Замеряем время
#             time_start = time.time()
#
#             # Читаем запрос
#             request = self.__read_request()
#             # логируем
#             # self.log(chunk=request, type_packet=' Полученный ')
#
#             # Если запрсо пустота - сбрасываем подключяение
#             if request is None:
#                 # print(f'Client #{self.cid} unexpectedly disconnected')
#                 # self.close_socket()
#                 # session = False
#                 pass
#
#             # если в запросе есть конец сессии - закрываем подключение
#             elif self.SimulatorMeter.close in request:
#                 # self.close_socket()
#                 # отправляем пустой байт
#                 # self.__write_response(response=b'')
#                 time.sleep(0.2)
#                 # pass
#
#             # ЕСЛИ ПРИШЕЛ ПУСТОЙ ОТВЕТ
#             elif b'' == request:
#                 pass
#                 print('ПРИШЕЛ ПУСТОЙ ОТВЕТ')
#
#             elif len(request) > 0:
#                 # Формируем ответ
#                 response = self.__handle_request(request)
#
#                 # Отправляем ответ
#                 self.__write_response(response)
#
#                 # Получаем время
#                 time_finis = time.time()
#                 print('Запрос Обрабатывался:', time_finis - time_start)
#                 # assert time_finis - time_start < 2, 'Слишком долгое время ожидания'
#             else:
#                 break
#
#
#     def _SET_TIMEOUT(self, timeout):
#         """
#         Здесь устанавливаем таймаут на сокет
#
#         :param timeout:
#         :return:
#         """
#         if type(self.client_socket) is socket.socket:
#             self.client_socket.settimeout(float(timeout))
#
#     # Читаем запрос
#
#     def __read_request(self):
#         # Когда сессия появилась - выставляем заново таймаут
#         self._SET_TIMEOUT(1)
#         # и после этого начинаем читать
#
#         request = bytes()
#
#         try:
#             # Первое что делаем - читаем первый символ
#             chunk = self.client_socket.recv(20)
#             print('чо прочитали',  chunk)
#             request = request + chunk
#             # Теперь включаем бесконечный цикл
#             while True:
#                 # Ставим таймаут на 10 милисекунд
#                 self._SET_TIMEOUT(0.05)
#                 # и дочитываем все что нам нужно
#                 chunk = self.client_socket.recv(1)
#                 request = request + chunk
#                 # ЕСЛИ У НАС КОНЕЦ ПЕРЕДАЧИ
#                 if len(chunk) < 1:
#                     break
#                 # Клиент преждевременно отключился.
#                 if not chunk:
#                     print(' Клиент преждевременно отключился.')
#                     break
#                 if chunk == b'':
#                     print('пустота')
#                     break
#
#                 if self.SimulatorMeter.lf in chunk:
#                     break
#                 if self.SimulatorMeter.etx in chunk:
#                     # и дочитываем все что нам нужно
#                     chunk = self.client_socket.recv(1)
#                     request = request + chunk
#                     break
#             # Логируем
#             # print('------------------------------- ЧИТАЕМ ДАННЫЕ -----------------------------------')
#             # self.log(chunk=request, type_packet=' Полученный ')
#             print(datetime.datetime.now(), request)
#             # Возвращаем
#             return request
#
#
#         except ConnectionResetError:
#             # Соединение было неожиданно разорвано.
#             print('Соединение было неожиданно разорвано.')
#             return None
#
#         # Когда ловыим ошибку по тайауту - возвращаем что накопили
#         except socket.timeout:
#
#             print(datetime.datetime.now(),'попався', request)
#             return request
#
#         except Exception as e:
#             print(' ОШИБКА Сокета ', e)
#
#             # print('Неизвестная ошибка')
#             #
#             print('ЧТО ПРОЧИТАЛИ\n', request)
#
#             return None
#
#     # обрабатывает Запрос
#     def __handle_request(self, request):
#
#         # Здесь Формируем ответ в зависимости от запроса
#
#         response = self.SimulatorMeter.command(request)
#
#         # print('--------------------------------ОТПРАВЛЯЕМ ОТВЕТ-------------------------')
#         # self.log(chunk=response, type_packet=' Отправленный - ')
#
#         return response
#
#     # отправляет клиенту ответ
#     def __write_response(self, response):
#
#         try:
#             self.client_socket.sendall(response)
#
#         except Exception as e:
#             print('НЕ УДАЛОСЬ ОТПРАВИТЬ ОТВЕТ')
#             print('ОШИБКА при отправке ', e)
#
#             self.close_socket()
#
#     # -----------------------------------------------
#     def close_socket(self):
#         # Если ответа нет, закрываем сокет
#         self.client_socket.close()
#
#     # -----------------------------------------------
#     def log(self, chunk, type_packet: str):
#         print('!!!!!!!!!!', '!!!!!!!!!!!')
#         print(type_packet + 'пакет : ', chunk, ' ')
#         print(' Его длина : ', len(chunk), '')
#         print('Байт код\n', chunk.hex(), '\n')
#         print('ДАМП : ', dump(chunk), '')
#
#         try:
#             print('Расшифровка :', chunk.decode('ascii'), '\n')
#         except UnicodeDecodeError:
#             print('Не Удалось расшифровать :', chunk, '\n')
#
#         print1 = str(type_packet) + 'пакет : ' + str(chunk) + '\n'
#         print2 = ' Его длина : ' + str(len(chunk)) + '\n'
#
#         print3 = 'ДАМП : ' + str(dump(chunk)) + '\n'
#
#         try:
#             print4 = 'Расшифровка : ' + str(chunk.decode('ascii')) + '\n'
#         except UnicodeDecodeError:
#             print4 = 'Не Удалось расшифровать : ' + str(chunk) + '\n'
#         # логируем через файл -
#         writen_text = '---------------------------------------------------------\n' + \
#                       str(datetime.datetime.now()) + '\n' + \
#                       print1 + print2 + print3 + print4
#
#         write_file.append_write_log_file(file_name=self.log_file, writen_text=writen_text)
SetupMeter(5555)