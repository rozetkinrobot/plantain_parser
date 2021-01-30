import os
import sys
from PyQt5 import QtWidgets
from datetime import datetime
from time import sleep
from smartcard.Exceptions import NoCardException, CardConnectionException

import design
from acr122ulib import *


keys = []


class Card:
    def __init__(self, dump, uid=None):
        self._dump = dump
        if uid:
            self._uid = uid.encode()
        else:
            self._uid = None

    @property
    def dump(self):
        return self._dump

    @property
    def uid(self):
        return self._uid

    def verify_dump(self):
        un_dump = self.dump
        dump_correct = True
        # TODO: some conditions
        if dump_correct:
            return True
        else:
            return False

    def get_uid(self):  # sec 0, blk 0, 0-7 bytes
        if self.uid == None:
            return self.get_data(0, 0, 0, 7)
        else:
            return self.uid

    def _get_addr(self, sec: int, blk: int, offset: int):
        return sec * 16 * 4 + blk * 16 + offset

    def get_data(self, sec: int, blk: int, start: int, end: int):
        return self.dump[self._get_addr(sec, blk, start):self._get_addr(sec, blk, end)]

    def get_number(self):

        uid = self.get_uid()

        def calc_num(b_array_uid: list):
            j = 0
            for i, c in enumerate(b_array_uid):
                j += (c & 255) << (i << 3)
            return j

        def calc_verity(num: str):
            num += "0"
            lenght = len(num)
            i = (lenght - 1) % 2
            i2 = 0
            for count, num_i in enumerate(num):
                num_i = int(num_i)
                if i == (lenght - count - 1) % 2:
                    num_i *= 2
                i2 = num_i % 10 + num_i//10 + i2
            return 10 - (i2 % 10)

        num = str("96433078") + str(calc_num(uid))
        num += str(calc_verity(num))

        return num

    def get_balance(self):  # 4 sec, 0 blk, 0-3 bytes
        return int.from_bytes(self.get_data(4, 0, 0, 3), "little")//100

    def get_ekp_num(self):  # 32 sec, 0 blk, 1-8 bytes (128 blk)
        print(self.get_data(32, 0, 1, 8))
        return int.from_bytes(self.get_data(32, 0, 1, 8), "big")

    def get_last_day(self):  # 8 sec, 0 blk, 10-13 bytes (32 blk)
        b_date = self.get_data(8, 0, 10, 13)
        return f"{int(b_date[2])-1}.{int(b_date[1])}.{int(b_date[0])+2000}"

    def get_passport(self):  # 8 sec, 1 blk, 3-8 bytes serial, 9-12 bytes number
        try:
            serial = self.get_data(8, 1, 3, 8).decode().replace(" ", "")
            number = str(int.from_bytes(self.get_data(8, 1, 9, 12), "little"))
            return int(serial+number)
        except:
            return None

    def get_lastname(self):  # 13 sec, 0 blk, 1-35 bytes
        return self.get_data(13, 0, 1, 34).rstrip().rstrip(b'\x00').decode("cp1251")

    def get_firstname_and_patronymic(self):  # 14 sec, 0 blk, 1-48 bytes
        return self.get_data(14, 0, 1, 47).rstrip().rstrip(b'\x00').decode("cp1251")

    def get_underground_rides(self):  # 9 sec, 0 blk, 0-4 bytes
        return str(int.from_bytes(self.get_data(9, 0, 0, 4), "little"))

    def get_last_land_ride(self):  # 12 sec, 0 blk, 9-15 bytes
        print(self.get_data(12, 0, 0, 32))
        pass  # TODO

    def get_last_underground_ride(self):  # 9 sec, 2 blk, 0-3 bytes
        print(self.get_data(9, 2, 0, 3))

    def get_last_ride_time(self):  # 5 sec, 0 blk, 0-3 bytes
        pass  # TODO

    def get_last_count(self):  # 5 sec, 0 blk, 6-8 bytes
        pass  # TODO

    def get_last_balance_top_up(self):  # 4 sec, 2 blk, 8-11 bytes
        pass  # TODO

    def get_last_balance_top_up_date(self):  # 4 sec, 2 blk, 2-5 bytes
        pass  # TODO

    def get_activation_time(self):  # 5 sec, 0 blk, 0-3 bytes
        pass  # TODO


class PlantainParserApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.Card = None
        self.setupUi(self)
        self.openButton.clicked.connect(self.select_dump)
        self.parse_button.clicked.connect(self.parse_dump)
        self.dumpButton.setEnabled(False)
        self.dumpButton.clicked.connect(self.create_dump)

    def display_error(self, error_message: str) -> None:
        self.error_dialog = QtWidgets.QErrorMessage()
        self.error_dialog.showMessage(error_message)

    def clean_card_fields(self) -> None:
        self.card_type_view.setPlainText("")
        self.card_num_view.setPlainText("")
        self.ekp_num_view.setPlainText("")
        self.fio_view.setPlainText("")
        self.balance_view.setPlainText("")
        self.passport_view.setPlainText("")
        self.last_day_view.setPlainText("")

    def create_dump(self) -> bool:
        try:
            with open("keys.txt", "r") as keyfile:
                for line in keyfile.readlines():
                    if line.strip() not in keys:
                        keys.append(line.strip())
        except FileNotFoundError:
            self.display_error("Файл ключей не найден!")
            return False
        readers = search_readers()
        print(readers)
        if len(readers) == 0:
            self.display_error("Не найдено ни одного ридера!")
            return None
        connection = None
        i = 0
        while connection == None:
            print(f"Connection attempt # {i}")
            connection = create_connection(readers[0])
            print(connection)
            sleep(0.5)
            i += 1

        if connection == False:
            self.display_error("Ошибка соединения!")
            return None
        try:
            print("1")
            uid = getuid(connection)
            print("2")
            info = getinfo(connection)
            print("3")
            if "MIFARE" not in info["Name"]:
                return None
            if "1K" in info["Name"]:
                size = 1024
            else:
                size = 4096
            dump = b""
            for i in range(16):
                print(f"Reading sector {i}")
                dump1 = False
                for key in keys:
                    print(f"    attempt to auth with key {key}")
                    dump1 = read_sector_with_key(i, key)
                    if dump1:
                        break
                if not dump1:
                    self.display_error(f"No key for sector {i}!")
                    return None
                dump += dump1
            self.Card = Card(dump, uid)
            return self.parse_dump(dump=dump)
        except NoCardException:
            return False

    def parse_dump(self, dump=None):
        self.clean_card_fields()
        if not dump:
            p_dump_filename = self.file_name_view.toPlainText()
            print(p_dump_filename)
            try:
                with open(p_dump_filename, "rb") as p_dump_file:
                    self.Card = Card(p_dump_file.read())
                    if not self.Card.verify_dump():
                        self.Card = None
                        return self.display_error('Файл не является валидным дампом!')
                    self.creation_date_view.setPlainText(datetime.fromtimestamp(
                        os.path.getmtime(p_dump_filename)).strftime('%Y-%m-%d %H:%M:%S'))
                    self.parse_button.setEnabled(True)
            except FileNotFoundError as e:
                return self.display_error('Файл не найден!\n' + str(p_dump_filename) + "\n" + str(e))

        if self.Card is None:
            self.display_error("Файл дампа не выбран")
            return False

        balance = str(self.Card.get_balance())
        self.balance_view.setPlainText(balance)
        full_name = str(self.Card.get_lastname() + " " +
                        self.Card.get_firstname_and_patronymic())

        if full_name == " ":
            card_type = "Подорожник"
        else:
            card_type = "Льготный проездной"
            self.fio_view.setPlainText(full_name)

        ekp_num = self.Card.get_ekp_num()
        if ekp_num:
            card_type = "Единая карта Петербуржца + " + card_type
            self.ekp_num_view.setPlainText(str(ekp_num))

        self.card_type_view.setPlainText(card_type)
        card_num = str(self.Card.get_number())
        self.card_num_view.setPlainText(card_num)
        if "Подорожник" not in card_type:
            passport_num = str(self.Card.get_passport())
            self.passport_view.setPlainText(passport_num)
            last_day = str(self.Card.get_last_day())
            self.last_day_view.setPlainText(last_day)

        return True

    def select_dump(self) -> bool:
        p_dump_filename = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите файл дампа")
        print(type(p_dump_filename), p_dump_filename)
        self.file_name_view.setPlainText(p_dump_filename[0])


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = PlantainParserApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
