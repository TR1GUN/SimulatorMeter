# расположим здесь парсеры наших xml
from xml.dom import minidom
import os

path ='/'.join((os.path.abspath(__file__).replace('\\', '/')).split('/')[:-1])


class ReadCounters:
    """
    Данный класс предназначен для чтения Настроек в файле xml

    """
    # Определяем все поля в none
    xmlpath = None
    xmldoc = None
    name = None
    address = None
    password = None
    snumber = None
    maker = None
    version = None
    model = None
    random = None
    datecheckmode = None
    respondtimeout = None

    def __init__(self, xmlpath):
        self.xmlpath = xmlpath
        xmldoc = minidom.parse(self.xmlpath)
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
