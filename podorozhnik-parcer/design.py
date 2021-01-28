# This Python file uses the following encoding: utf-8
import sys
from PySide2.QtWidgets import QApplication, QMainWindow


class design(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)


if __name__ == "__main__":
    app = QApplication([])
    window = design()
    window.show()
    sys.exit(app.exec_())
