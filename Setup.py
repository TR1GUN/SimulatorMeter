# Здесь основнйо файл запуска


class Setup:

    port = 5555

    def __init__(self, port=5555):
        self.port = port
        self._run_up_server()

    def _run_up_server(self):
        from Server_Meter import SocketMeters

        server = SocketMeters(self.port)



lol = Setup()

