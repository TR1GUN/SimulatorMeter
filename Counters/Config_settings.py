# Этот скрипт нужен для парсинга наших файлов с конфигурацией и настрйоками наших виртуальных счетчиков
import os
import json

path ='/'.join((os.path.abspath(__file__).replace('\\', '/')).split('/')[:-1])

# Читаем время последней отправки

def get_time():
    try:
        jsonfile = open(path + '/Meter_Timestamp.json')
        json_text = jsonfile.read()
        valuesbank = json.loads(json_text)
        valuesbank = int(valuesbank["time"])
    except:
        valuesbank = 0
    return valuesbank