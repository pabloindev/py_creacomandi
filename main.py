#################### IMPORT ####################
# qt
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
from logging.handlers import RotatingFileHandler

# mie classi
import Utility
from CustomDialog import CustomDialog



#################### FUNZIONI ####################
class MainWindow(QtWidgets.QMainWindow):

    working_dir = None        # percorso alla directory corrente
    config = None             # file di configurazione, dictionary caricato dal file config.json
    file_list = []            # lista temporanea per caricare la path dei file scelti
    abs_path_libwebp_exe = "" # percorso assoluto al file eseguibile cwepb
    worker_proc = None        # processo che lancio per eseguire la conversione delle immagini
    dialog_output = None      # dialog che contiene l'output dei comandi di conversione
    machine = None            # macchina corrente

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

        # setto variili della classe che mi possono essere utili
        self.working_dir = get_working_directory()
        set_working_directory()
        self.config = readConfigJson()
        self.machine = self.config["machine"]

        # carico il file creato con qt designer
        uic.loadUi("main.ui", self)

        # carico i log
        caricaLog(self.working_dir)
        logging.debug('*********************************************')
        logging.debug('Applicazione py_cwebp avviata')


        # modifico ulteriormente la gui poichè non riesco a fare tutto da qtdesigner
        self.changeUI()

        # setto gli eventi ai vari widgets
        self.settaEventi()
        
        
        #machine = config["machine"]
        utilita = Utility.Utility(self.config, self.working_dir)

    
    # -------------------------------------------------------------------------------
    # modifica ulteriore della UI
    # -------------------------------------------------------------------------------
    def changeUI(self):

        # aggiungo item alla combo box che mi dice cosa devo resizare
        self.comboBoxWidthOrHeightCwebp.addItem("Width")
        self.comboBoxWidthOrHeightCwebp.addItem("Height")

        # aggiungo gli item nella combo che contiene i template dei comandi, questo per tutti i tab esistenti
        for x in self.config[self.machine]["cwebp"]["commands"]:
            self.comboBoxCwebpCommands.addItem(x)

        for x in self.config[self.machine]["ffmpeg"]["commands"]:
            self.comboBoxFFmpegCommands.addItem(x)

        # imposta l'icona della finestra
        self.setWindowIcon(QtGui.QIcon('icona.ico'))

    # -------------------------------------------------------------------------------
    # definizione degli eventi 
    # -------------------------------------------------------------------------------
    # entry per settare tutti gli eventi
    def settaEventi(self):
        # toolbar - apro la dialog per scegliere i files da aggiungere
        self.actionAdd_Files.triggered.connect(self.evento_scegliFiles) 
        # toolbar - esco dall'app
        self.actionExit.triggered.connect(self.close) 
        
        # ho messo una dimensione in pixel - abilito la combo che mi chiede se tale dimensione fa riferimento a altezza o larghezza
        self.spinBoxResizeCwebp.valueChanged.connect(self.abilitaDisabilitaComboWidthHeight) 

        # avvio la conversione delle immagini selezionate
        self.pushButtonAvviaConversione.clicked.connect(self.avviaConversione)

        # richiesto cambio tab attivo
        self.tabWidget.currentChanged.connect(self.tabChange) #changed!
        


    # apro la dialog per scegliere i files
    def evento_scegliFiles(self):

        filtroFiles = self.getConfigFromTabAndMachine()["QFileDialog_filtroFiles"]

        self.file_list = []
        dialog = QFileDialog(self)
        dialog.setDirectory(self.working_dir)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        #dialog.setNameFilter("Images (*.png *.jpg)")
        dialog.setNameFilter(filtroFiles)
        dialog.setViewMode(QFileDialog.ViewMode.List)
        if dialog.exec():
            # ritorno una lista di path assoluti 
            self.file_list = dialog.selectedFiles()
            
            #azzero la textarea
            self.PlainTextEditFiles.clear()

            # aggiorno la textarea con i files selezionati
            for x in self.file_list:
                self.PlainTextEditFiles.appendPlainText(x)
            
            # abilito o disabilito il tasto per la conversione - in base al fatto se ho dei file da convertire
            self.abilitaDisabilitaTastoConversione()
            
        #print(self.file_list)
            
        
    # abilito o disabilito la combo che mi chiede quale dimensione mantenere (altezza o larghezza)
    def abilitaDisabilitaComboWidthHeight(self):
        curr_value = self.spinBoxResizeCwebp.value() 
        
        if curr_value != 0:
            self.comboBoxWidthOrHeightCwebp.setEnabled(True)
        else:
            self.comboBoxWidthOrHeightCwebp.setEnabled(False)

    # ho premuto il tasto per iniziare la conversione delle immagini
    def avviaConversione(self):
        
        if self.tabWidget.currentIndex() == 0:
            # sono nel tab di cwebp
            self.avviaConversione_cwebp()
        elif self.tabWidget.currentIndex() == 1:
            # sono nel tab di ffmpeg
            self.avviaConversione_ffmpeg()
        else:
            QMessageBox.about(self, "Alert errori", "tab non gestito")
        
            
    # cambio tab attivo
    def tabChange(self,i): #changed!
        self.abilitaDisabilitaTastoConversione()
        #print(str(i))

    # -------------------------------------------------------------------------------
    # CWEBP - Metodi per la conversione vera e propria
    # -------------------------------------------------------------------------------
    # avvio conversioni per cwebp
    def avviaConversione_cwebp(self):
        
        # controllo che tutti i dati siano coerenti
        arr_err = self.check_errori_conversione_cwebp()
        if len(arr_err) == 0:

            list_comandi = self.creaJobConversioni_cwebp() # lista dei comandi da lanciare per convertire le immagini

            logging.debug('Inizio Conversione di ' + str(len(list_comandi)) + " files")

            # creo la dialog che andrà a contenere l'output del processo di conversione
            #- eseguo poi il processo di conversione nella dialog
            self.dialog_output = CustomDialog(list_comandi, self.getConfigFromTabAndMachine())
            self.dialog_output.exec()
        else:
            err_str = ""
            for x in arr_err:
                err_str += x + "\n"

            QMessageBox.about(self, "Alert errori", err_str)

    # controllo che non ci siano errori prima di effetturare la conversione
    def check_errori_conversione_cwebp(self):
        list_errori = []

        abs_path_libwebp_exe = self.costruisci_percorso_eseguibile_cwebp()

        # controllo che il percorso all'eseguibile esista
        if not os.path.isfile(abs_path_libwebp_exe): 
            list_errori.append("percorso " + abs_path_libwebp_exe + " inesistente")


        # controllo che i files nella textarea esistano e siano delle immagini in base al'estensione
        self.file_list = self.PlainTextEditFiles.toPlainText().splitlines()
        for path in self.file_list:
            if not os.path.isfile(path): 
                list_errori.append("file " + path + " inesistente")
            else:
                filename, file_extension = os.path.splitext(path)
                if file_extension.lower() not in [".jpg", ".jpeg", ".png", ".gif"]:
                    list_errori.append("estensione del file " + path + " non corretta - inserire solo formati immagini")


        return list_errori
    
    # mi costruiscio la lista dei comandi da lanciare per convertire le immagini
    def creaJobConversioni_cwebp(self):

        abs_path_libwebp_exe = self.costruisci_percorso_eseguibile_cwebp()
        list_comandi = []
        comando_template = self.comboBoxCwebpCommands.currentText()

        #list_args = ["-m 6"         # Specify the compression method to use, Possible values range from 0 to 6, 
        #            , "-q " + str(self.spinBoxQualityCwebp.value()) # Specify the compression factor for RGB channels between 0 and 100. The default is 75.
        #            , "-mt"        # Use multi-threading for encoding, if possible.
        #            , "-af"        # Turns auto-filter on. This algorithm will spend additional time optimizing the filtering strength to reach a well-balanced quality.
        #            , "-progress"  # Report encoding progress in percent
        #            ]
        
        opzioni = " -q " + str(self.spinBoxQualityCwebp.value())

        # se ho specifica una dimensione per larghezza o altezza devo ridimensionare l'immagine
        if self.spinBoxResizeCwebp.value() != 0:
            if self.comboBoxWidthOrHeightCwebp.currentText() == "Width":
                #list_args.append("-resize " + str(self.spinBoxResizeCwebp.value()) + " 0")
                opzioni += " -resize " + str(self.spinBoxResizeCwebp.value()) + " 0 "
            else:
                #list_args.append("-resize 0 " + str(self.spinBoxResizeCwebp.value()))
                opzioni += " -resize 0 " + str(self.spinBoxResizeCwebp.value()) + " "

        # recupero la lista dei file dalla textarea
        self.file_list = self.PlainTextEditFiles.toPlainText().splitlines()

        # costruisco una lista di comandi da lanciare
        for path in self.file_list:

            # estraggo la path esclusa l'estenzione, e l'estensione
            filename, file_extension = os.path.splitext(path)

            # mi costruisco il comando da lanciare
            #list_temp = list_args + ["\"" + path + "\"", "-o" , "\"" + filename + ".webp\""]
            #comando = "\"" + abs_path_libwebp_exe + "\" " + ' '.join(list_temp)
            comando = comando_template.replace("<programma>", "\"" + abs_path_libwebp_exe + "\"").replace("<opzioni>", opzioni).replace("<input>", "\"" + path + "\"").replace("<output>", "\"" + filename + ".webp\"")
            list_comandi.append(comando)
        
        return list_comandi

    def costruisci_percorso_eseguibile_cwebp(self):
        # mi costruisco il percorso all'eseguibile            
        abs_path_libwebp_exe = ""
        path_eseguibile = self.config[self.machine]["cwebp"]["path_eseguibile"]
        if os.path.isabs(path_eseguibile):
            abs_path_libwebp_exe = path_eseguibile
        else: 
            abs_path_libwebp_exe = os.path.join(self.working_dir, "vendor", self.machine, path_eseguibile)
        return abs_path_libwebp_exe

    # -------------------------------------------------------------------------------
    # FFMPEG - Metodi per la conversione vera e propria
    # -------------------------------------------------------------------------------
    def avviaConversione_ffmpeg(self):
        # controllo che tutti i dati siano coerenti
        arr_err = self.check_errori_conversione_ffmpeg()
        if len(arr_err) == 0:

            list_comandi = self.creaJobConversioni_ffmpeg() # lista dei comandi da lanciare per convertire le immagini

            logging.debug('Inizio Conversione di ' + str(len(list_comandi)) + " files")

            # creo la dialog che andrà a contenere l'output del processo di conversione
            #- eseguo poi il processo di conversione nella dialog
            self.dialog_output = CustomDialog(list_comandi, self.getConfigFromTabAndMachine())
            self.dialog_output.exec()
        else:
            err_str = ""
            for x in arr_err:
                err_str += x + "\n"

            QMessageBox.about(self, "Alert errori", err_str)

    # controllo che non ci siano errori prima di effetturare la conversione
    def check_errori_conversione_ffmpeg(self):
        list_errori = []

        abs_path_ffmpeg_exe = self.costruisci_percorso_eseguibile_ffmpeg()

        # controllo che il percorso all'eseguibile esista
        if not os.path.isfile(abs_path_ffmpeg_exe): 
            list_errori.append("percorso " + abs_path_ffmpeg_exe + " inesistente")


        # controllo che i files nella textarea esistano e siano delle immagini in base al'estensione
        self.file_list = self.PlainTextEditFiles.toPlainText().splitlines()
        for path in self.file_list:
            if not os.path.isfile(path): 
                list_errori.append("file " + path + " inesistente")
            else:
                filename, file_extension = os.path.splitext(path)
                if file_extension.lower() not in [".ts", ".mkv", ".mp4", ".avi", ".m4a"]:
                    list_errori.append("estensione del file " + path + " non corretta - inserire solo formati video")


        return list_errori
    
    def costruisci_percorso_eseguibile_ffmpeg(self):
        # mi costruisco il percorso all'eseguibile            
        abs_path_ffmpeg_exe = ""
        path_eseguibile = self.config[self.machine]["ffmpeg"]["path_eseguibile"]
        if os.path.isabs(path_eseguibile):
            abs_path_ffmpeg_exe = path_eseguibile
        else: 
            abs_path_ffmpeg_exe = os.path.join(self.working_dir, "vendor", self.machine, path_eseguibile)
        return abs_path_ffmpeg_exe

    # mi costruiscio la lista dei comandi da lanciare per convertire le immagini
    def creaJobConversioni_ffmpeg(self):

        abs_path_ffmpeg_exe = self.costruisci_percorso_eseguibile_ffmpeg()
        list_comandi = []
        comando_template = self.comboBoxFFmpegCommands.currentText()
        birrateVideo = " -b:v " + str(self.spinBoxFFmpegBitrateVideo.value()) + "k "
        birrateAudio = " -b:a " + str(self.spinBoxFFmpegBitrateAudio.value()) + "k "


        # recupero la lista dei file dalla textarea
        self.file_list = self.PlainTextEditFiles.toPlainText().splitlines()

        # costruisco una lista di comandi da lanciare
        for path in self.file_list:

            # estraggo la path esclusa l'estenzione, e l'estensione
            filename, file_extension = os.path.splitext(path)

            # mi costruisco il comando da lanciare
            #list_temp = list_args + ["\"" + path + "\"", "-o" , "\"" + filename + ".webp\""]
            #comando = "\"" + abs_path_libwebp_exe + "\" " + ' '.join(list_temp)
            comando = comando_template.replace("<programma>", "\"" + abs_path_ffmpeg_exe + "\"").replace("<bitrateVideo>", birrateVideo).replace("<bitrateAudio>", birrateAudio).replace("<input>", "\"" + path + "\"").replace("<output>", "\"" + filename + "_NEW.mp4\"")
            list_comandi.append(comando)
        
        return list_comandi


    # -------------------------------------------------------------------------------
    # Metodi privati
    # -------------------------------------------------------------------------------
    # abilita o disabilita il tasto conversione a seconda del fatto che nella textarea ci sono file o cartelle esistenti
    def abilitaDisabilitaTastoConversione(self):
        abilitaTasto = True
        self.file_list = self.PlainTextEditFiles.toPlainText().splitlines()
        for path in self.file_list:
            if not os.path.isfile(path) and not os.path.isdir(path): 
                abilitaTasto = False
        
        self.pushButtonAvviaConversione.setEnabled(abilitaTasto)

    
    # mi ritorna un oggetto pulito contenente i paramateri in base alla macchina che sto utilizzando e il tab selezionato
    def getConfigFromTabAndMachine(self):
        obj = None
        
        if self.tabWidget.currentIndex() == 0: # sono nel tab di cwebp
           obj = self.config[self.machine]["cwebp"]
        elif self.tabWidget.currentIndex() == 1:
            obj = self.config[self.machine]["ffmpeg"]
        
        return obj



def caricaLog(working_dir):
    # creo la cartella dei log se non esiste
    if not os.path.exists(os.path.join(working_dir,"logs")): 
        os.makedirs(os.path.join(working_dir,"logs")) 

    # imposto logging su file
    logging.basicConfig(
        # appendo log al file, non vado a sovrascrivere, non specifico filemode poichè di default è già append
        format='%(asctime)s - %(levelname)s - %(message)s'  # formato
        , level=logging.DEBUG
        , handlers=[
            #logging.FileHandler(LOG_FILENAME), # nome del file di log, di questo handler non ho bisogno poichè sul file disk scrive già RotatingFileHandler
            logging.StreamHandler(sys.stdout),  # quando vado a inserire un log stampo anche su console
            logging.handlers.RotatingFileHandler(os.path.join(working_dir,"logs","app.log"), maxBytes=1000000, backupCount=5, encoding='utf-8') # log rotating 1MB
        ]
    )

# #leggo il file di config con tutti le configurazioni del programma
def readConfigJson():
    with open('config.json') as json_data_file:
        appsetting = json.load(json_data_file)
        return appsetting

def set_working_directory():
    absPath = get_working_directory()
    os.chdir(absPath)

def get_working_directory():
    absPath = ""
    # mi costruisco il percorso assoluto della directory che contiene il file main.py
    if(os.path.isabs(sys.argv[0])):
        absPath = os.path.dirname(sys.argv[0])
    else:
        #provo a costruirmi la directory in questo modo (sonogià dentro la directory del programma)
        absPath = os.path.dirname(os.path.abspath('.') + "/" + sys.argv[0])

    return absPath


#################### ENTRY PROGRAMMA ####################
if __name__ == "__main__":
    #main(sys.argv[1:])
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


    






