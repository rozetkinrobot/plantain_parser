from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.ATR import ATR
from smartcard.CardType import AnyCardType
from smartcard.pcsc.PCSCReader import PCSCReader
from smartcard.CardConnectionDecorator import CardConnectionDecorator
from smartcard.Exceptions import NoCardException, CardConnectionException
import sys

cmdMap = {
    "mute": [0xFF, 0x00, 0x52, 0x00, 0x00],
    "unmute": [0xFF, 0x00, 0x52, 0xFF, 0x00],
    "getuid": [0xFF, 0xCA, 0x00, 0x00, 0x00],
    "firmver": [0xFF, 0x00, 0x48, 0x00, 0x00],
    "loadkey": [0xFF, 0x82, 0x00, 0x00, 0x06]
}

cardnameMap = {
    "00 01": "MIFARE Classic 1K",
    "00 02": "MIFARE Classic 4K",
    "00 03": "MIFARE Ultralight",
    "00 26": "MIFARE Mini",
    "F0 04": "Topaz and Jewel",
    "F0 11": "FeliCa 212K",
    "F0 11": "FeliCa 424K",
    "C1 05": "SmartMX with MIFARE Classic 4K"
}


def search_readers() -> list:
    r = readers()
    return r


def create_connection(reader: PCSCReader) -> CardConnectionDecorator:
    try:
        connection = reader.createConnection()
        connection.connect()
        return connection
    except NoCardException:
        return None
    except CardConnectionException:
        return False


def firmver(connection: CardConnectionDecorator):
    data, sw1, sw2 = connection.transmit(cmdMap["firmver"])
    version = ''.join(chr(i) for i in data)+chr(sw1)+chr(sw2)
    return version


def getinfo(connection: CardConnectionDecorator) -> dict:
    atr = ATR(connection.getATR())
    hb = toHexString(atr.getHistoricalBytes())
    cardname = hb[-17:-12]
    name = cardnameMap.get(cardname, "Unknown " + str(cardname))
    return {
        "Name": name,
        "T0": atr.isT0Supported(),
        "T1": atr.isT1Supported(),
        "T15": atr.isT15Supported()
    }


def loadkey(connection: CardConnectionDecorator, key: str):
    COMMAND = cmdMap.get("loadkey")
    load_key = [key[0:2], key[2:4], key[4:6], key[6:8], key[8:10], key[10:12]]
    for i in range(6):
        load_key[i] = int(load_key[i], 16)
    COMMAND.extend(load_key)
    data, sw1, sw2 = connection.transmit(COMMAND)
    if (sw1, sw2) == (0x90, 0x0):
        return True
    elif (sw1, sw2) == (0x63, 0x0):
        return False


def read_sector(connection: CardConnectionDecorator, sector_num: int):
    COMMAND = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01,
               0x00, sector_num*4, 0x60, 0x00]
    data, sw1, sw2 = connection.transmit(COMMAND)
    if (sw1, sw2) == (0x90, 0x0):
        pass
    elif (sw1, sw2) == (0x63, 0x0):
        COMMAND[8] = 0x61
        data, sw1, sw2 = connection.transmit(COMMAND)
        if (sw1, sw2) == (0x90, 0x0):
            pass
        else:
            return False
    sector_data = b""
    for block in range(sector_num*4, sector_num*4+4):
        COMMAND = [0xFF, 0xB0, 0x00]
        COMMAND.append(block)
        COMMAND.append(16)
        data, sw1, sw2 = connection.transmit(COMMAND)
        sector_data += bytes(data)
    print((sw1, sw2))
    if (sw1, sw2) == (0x90, 0x0):
        return sector_data
    else:
        return False


def read_sector_with_key(sector: int, key: str, reader=None):
    if not reader:
        readers = search_readers()
    else:
        readers = [reader]
    connection = None
    while connection == None:
        connection = create_connection(readers[0])
    if connection == False:
        return False

    if not loadkey(connection, key):
        return False
    else:
        return read_sector(connection, sector)


def mute(connection: CardConnectionDecorator):
    data, sw1, sw2 = connection.transmit(cmdMap["mute"])
    if (sw1, sw2) == (0x90, 0x0):
        return True
    else:
        return False


def unmute(connection: CardConnectionDecorator):
    data, sw1, sw2 = connection.transmit(cmdMap["unmute"])
    if (sw1, sw2) == (0x90, 0x0):
        return True
    else:
        return False


def getuid(connection: CardConnectionDecorator):
    data, sw1, sw2 = connection.transmit(cmdMap["getuid"])
    uid = toHexString(data).replace(" ", "")
    if (sw1, sw2) == (0x90, 0x0):
        return uid
    else:
        return None


if __name__ == "__main__":
    print(toHexString(list(read_sector_with_key(0, "ffffffffffff"))))
    print(toHexString(list(read_sector_with_key(4, "e56ac127dd45"))))
    
