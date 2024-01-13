from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtWidgets import (
    QApplication, 
    QWidget, 
    QFileDialog, 
    QGridLayout,
    QPushButton, 
    QLabel,
    QListWidget,
    QMessageBox,
    QDialog
)
from PyQt6.QtCore import QThread, QProcess, pyqtSignal #threads


# python standard lib
import sys, os, json, time, logging

# dialog che 
# - si occupa di convertire le immagini
# - contiene l'output del processo di conversione
class CustomDialog(QDialog):

    list_comandi = []     # lista dei comandi che devo eseguire per poter convertire le immagini
    worker_proc = None    # processo che lancio per eseguire la conversione delle immagini
    machine = ""          # macchina che sto utilizzando

    def __init__(self, list_comandi, objParametri):
        super().__init__()
        
        self.list_comandi = list_comandi
        self.objParametri = objParametri
        

        # carico il file creato con qt designer
        uic.loadUi("dialogOutput.ui", self)

        # attacco l'evento per chiudere la dialog
        self.pushButtonClose.clicked.connect(self.close)
        self.pushButtonSave.clicked.connect(self.saveOutput)

        # appena apro la dialog eseguo subito il primo comando nella lista
        self.eseguiUnJob()
        
    # salvo il contenuto della textarea
    def saveOutput(self):
        contenuto = self.plainTextEditOutput.toPlainText()
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File',"Nome del file")
        if fileName:
            with open(fileName, 'w') as f:
                f.write(contenuto)
        

    # eseguo il primo job contenuto nella lista dei comandi
    # in caso contrario se non devo fare niente esco
    def eseguiUnJob(self):

        if len(self.list_comandi) > 0:
            # ci sono ancora dei comandi da eseguire
            # lancio il primo comando
            comando = self.list_comandi.pop() # recupero un elemento e lo elimino dalla lista
            
            if self.objParametri["SN_EseguiProcessi"] != "S":
                # non riesco a eseguire cwebp richiamandolo da python - scrivo il comando da lanciare
                self.addStringa(comando)
                self.eseguiUnJob() 
            else:
                # istanzion il processo
                self.worker_proc = QProcess()
                
                # definisco gli eventi associati all processo
                self.worker_proc.readyReadStandardOutput.connect(self.handle_stdout)
                self.worker_proc.readyReadStandardError.connect(self.handle_stderr)
                self.worker_proc.finished.connect(self.handle_finished)
                
                # lancio il processo con il comando creato
                self.addStringa(comando)
                self.worker_proc.start(comando)
        else:
            # finito non ci sono altri comandi da eseguire
            self.pushButtonClose.setEnabled(True) 
            self.pushButtonSave.setEnabled(True) 
            QMessageBox.about(self, "Status", "Conversione terminata")

    # funzione di logging
    def addStringa(self, stringa):
        strout = stringa.strip()
        if(strout != ""):
            logging.debug(strout)
            self.plainTextEditOutput.appendPlainText(strout)

    # -------------------------------------------------------------------------------
    # Metodi ed eventi legati al processo che creo per convertire le immagini
    # -------------------------------------------------------------------------------
    def handle_stderr(self):
        data = self.worker_proc.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.addStringa(stderr)

    def handle_stdout(self):
        data = self.worker_proc.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.addStringa(stdout)

    def handle_finished(self):
        logging.debug("Process finished.")
        self.worker_proc = None
        self.eseguiUnJob() # provo a eseguire il prossimo job

