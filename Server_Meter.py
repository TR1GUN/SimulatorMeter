# Здесь напишем простенький сервер Эмулятор УСПД
import socket
import time
from Simulator_meter import SimulatorMeterEnergomera

from hexdump import dump

import datetime
import threading


class SocketMeters:
    """
    Здесь инициализируем сокет нашего эмулятора счетчика чтоб обращаться к нему по Ethernet
    """
    cid = None
    port = ''
    SimulatorMeter = None
    log_file = None
    address = '192.168.205.190'
    def __init__(self, conect_port, data=None):

        # Создаем файл лога
        # self.log_file = write_file.write_log_file(
        #     file_name='EmulatorMeter_' + str(time.mktime(datetime.datetime.now().timetuple())) + str('.txt'),
        #     writen_text='ЛОГ обмена :', folder='Meter/')
        # Задаем Порт
        print('GJlyzkb')
        self.serv_port = None
        self.port = conect_port

        self.SimulatorMeter = self._create_Meter()

        # Создаем сокет сервера
        serv_sock = self.__create_serv_sock()

        self.cid = 0
        # -----

        self.__connect_socket(serv_sock)

        print('ЗАВЕРШАЕМ')

    def _create_Meter(self, data = None):
        """
        Здесь создаем наш счетчик
        :return:
        """

        # ЕСЛИ У НАС НЕ НАЛЛ - спускаем серийник
        from copy import deepcopy
        SimulatorEnergomera = deepcopy(SimulatorMeterEnergomera)

        # serial = '009218054000006_' + str(self.port)

        # В качестве серйиника используем порт
        serial = str(self.port)
        SimulatorMeter = SimulatorEnergomera()
        SimulatorMeter.Set_Serial(serial)
        if data is not None:
            #     Здесь Записываем все наши данные в наш счетчик - ЭТО ВАЖНО !!!!
            SimulatorMeter.Set_Data(data=data)

        return SimulatorMeter


    def __connect_socket(self, serv_sock):
        # while True:
        #     if self.cid > 0 :
        #         break
        while True:
            try:
                self.client_socket = self.__accept_client_conn(serv_sock)
            except socket.timeout:
                print('Привышен таймаут')
                break

            # Производим сессию обмена инфой
            self.__session_client()
            # Добавляем еще одного пользователя
            self.cid += 1

    def __create_serv_sock(self):

        # self.SimulatorMeter = SimulatorMeterEnergomera()

        serv_sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_STREAM,
                                  # proto=0
                                  )

        print(self.port)
        # serv_sock.bind(('', self.port))
        serv_sock.bind((self.address, self.port))
        serv_sock.settimeout(40.0)

        serv_sock.listen(1)


        print(serv_sock.getsockname())
        return serv_sock

    # Отслеживаем Конект к сокету
    def __accept_client_conn(self, serv_sock):

        self.client_sock, client_addr = serv_sock.accept()

        # print(f'Client #{self.cid} connected '
        #       f'{client_addr[0]}:{client_addr[1]}')

        client_sock = self.client_sock
        return client_sock

    def __session_client(self):
        # Читаем запрос
        session = True
        while session:
            request = self.__read_request()

            print('----> ПОЛУЧИЛИ ЗАПРОС', request)

            if request is None:
                # print(f'Client #{self.cid} unexpectedly disconnected')
                session = False

            else:
                # Формируем ответ - ЕСЛИ ЭТО НЕ ЗХАКРЫТИЕ СЕССИИ
                if self.SimulatorMeter.close not in request:
                    # Формируем ответ
                    response = self.__handle_request(request)

                    # Отправляем ответ
                    self.__write_response(response)
                # Если это закрытие сессии- слушаем сокет на момент закрытия
                else:
                    print(self.client_socket, type(self.client_socket))
                    print(self.client_socket.getpeername())
                    print(self.client_socket.getblocking())
                    print(self.client_socket.gettimeout())
                    print(self.client_socket.getsockname())
                    print(self.client_socket.fileno())

                    time.sleep(5)
                    print('-----------Слушаем сокет--------')
                    print(self.client_socket, type(self.client_socket))
                    print(self.client_socket.getpeername())
                    print(self.client_socket.getblocking())
                    print(self.client_socket.gettimeout())
                    print(self.client_socket.getsockname())
                    print(self.client_socket.fileno())

                    self.close_socket()

    # Читаем запрос

    def __read_request(self):

        request = bytearray()
        try:
            # итак что делаем - считываем Первый Пакет с сокета
            request = self.client_socket.recv(1024)

            # ЕСЛИ У НАС В ПАКЕТЕ 1
            # - 2 БАЙТА
            if len(request) in [2]:
                while True:
                    chunk = self.client_socket.recv(1024)
                    request = request + chunk

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

            # ЕСЛИ У НАС ПУСТОТА
            if len(request) < 1:
                # print(' От клиента пришло пустое значение.')
                request = None
            if not request:
                # print(' От клиента не пришло никакой информации.')
                request = None

            # Логируем
            # print('------------------------------- ЧИТАЕМ ДАННЫЕ -----------------------------------')
            self.log(chunk=request, type_packet=' Полученный ')

            # Возвращаем
            return request


        except ConnectionResetError:
            # Соединение было неожиданно разорвано.
            print('Соединение было неожиданно разорвано.')
            return None
        except:

            print('Неизвестная ошибка')
            #
            # print('ЧТО ПРОЧИТАЛИ\n', request)
            return None

    # обрабатывает Запрос
    def __handle_request(self, request):

        # Здесь Формируем ответ в зависимости от запроса

        response = self.SimulatorMeter.command(request)

        # response = SimulatorMeter(request=request).response
        # print('--------------------------------ОТПРАВЛЯЕМ ОТВЕТ-------------------------')
        self.log(chunk=response, type_packet=' Отправленный ')
        # return request[::-1]
        return response

    # отправляет клиенту ответ
    def __write_response(self, response):
        # Сделаем так что ответ идет массивом
        # print('getpeername', self.client_socket.getpeername())
        # print('getblocking', self.client_socket.getblocking())
        # print('gettimeout', self.client_socket.gettimeout())
        # print('getsockname', self.client_socket.getsockname())

        from datetime import datetime
        # print(datetime.now())

        try:
            self.client_socket.sendall(response)

        except:
            print('-----------GOVNOO--------')
            print(self.client_socket, type(self.client_socket))
            print(self.client_socket.getpeername())
            print(self.client_socket.getblocking())
            print(self.client_socket.gettimeout())
            print(self.client_socket.getsockname())

            print(self.client_socket.accept())
            print('aaaaaaaaaaa')

            # self.close_socket()
            # chunk = self.client_socket.recv(1024)
            # print('ffffff',chunk)
            # if self.client_socket.getblocking() == True :
            #     self.client_socket.settimeout(20.0)
            #     # self.__write_response(response)
            #     print(self.client_socket.getblocking())
            #     lol = self.client_socket.send(b'\x00')
            #     print('jnghfdbkb',lol)
            #     time.sleep(1)

    # -----------------------------------------------
    def close_socket(self):
        # Если ответа нет, закрываем сокет
        self.client_socket.close()

        # print('ЗАКРЫЛИ СОКЕТ', self.client_socket.getsockname())

    def log(self, chunk, type_packet: str):
        print('\n!!!!!!!!!!', '!!!!!!!!!!!\n')
        print(type_packet + 'пакет : ', chunk, ' ')