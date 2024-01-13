import shutil, os, urllib, re
from datetime import datetime

class Utility:

    config = None
    working_dir = None
    tempfolder = None
    
    def __init__(self, config, working_dir):
        self.config = config
        self.working_dir = working_dir
        self.tempfolder = os.path.join(self.working_dir, "temp")


    # ritorno la lista dei db presenti, escludendo quelli di sistema
    def getListDb(self):
        sql = "SELECT schema_name FROM information_schema.schemata where schema_name not in ('information_schema','mysql','performance_schema','phpmyadmin','sys') order by schema_name asc"
        res = self.objDB.getQuery(sql)
        listatemp = []
        for x in res:
            listatemp.append(x["schema_name"])
        return listatemp

    # ritorno la lista dei file conf che apache carica
    def getListFilesConf(self):
        folder = self.config[self.config["machine"]]["path_vhost"]
        subfolders = [ {"path": f.path, "name": os.path.basename(f.path)} for f in os.scandir(folder) if f.is_file() and os.path.splitext(f)[1] == ".conf" ]
        return subfolders


    # ritorno la lista delle directory presenti nella cartella root dei siti
    def getListDirfromRootWebsite(self):
        folder = self.config[self.config["machine"]]["path_root_website"]
        subfolders = [ {"path": f.path, "name": os.path.basename(f.path)} for f in os.scandir(folder) if f.is_dir() ]
        return subfolders


    def scarica_ultma_versione_wp(self):
        output_file = os.path.join(self.tempfolder, "latest.zip")
        if(os.path.isfile(output_file) and self.config["sn_wp_force_download"] == "n"):
            pass
        else:
            url = "https://wordpress.org/latest.zip"
            output_file = os.path.join(self.tempfolder, "latest.zip")
            urllib.request.urlretrieve(url, output_file)

        return output_file
    
    
    def aggiorna_permessi(self, path_sito_temp):
        
        if(self.config["type_machine"] == "redhat"):
            # devo aggiornare i permessi della cartella
            #os.system('chown apache:apache -R ' + path_sito_temp)
            #os.system(f"find " + path_sito_temp + " -type d -exec chmod 775 {} \\;")
            #os.system(f"find " + path_sito_temp + " -type f -exec chmod 664 {} \\;")
            self.esegui_cmd_as_sudo('chown apache:apache -R ' + path_sito_temp)
            self.esegui_cmd_as_sudo(f"find " + path_sito_temp + " -type d -exec chmod 775 {} \\;")
            self.esegui_cmd_as_sudo(f"find " + path_sito_temp + " -type f -exec chmod 664 {} \\;")
            #os.system('echo %s|sudo -S %s' % ("o7l8b90a", 'chown apache:apache -R ' + path_sito_temp))
            #os.system('echo %s|sudo -S %s' % ("o7l8b90a", f"find " + path_sito_temp + " -type d -exec chmod 775 {} \\;"))
            #os.system('echo %s|sudo -S %s' % ("o7l8b90a", f"find " + path_sito_temp + " -type f -exec chmod 664 {} \\;"))

        elif(self.config["type_machine"] == "debian"):
            self.esegui_cmd_as_sudo('chown www-data:www-data -R ' + path_sito_temp)
            self.esegui_cmd_as_sudo(f"find " + path_sito_temp + " -type d -exec chmod 775 {} \\;")
            self.esegui_cmd_as_sudo(f"find " + path_sito_temp + " -type f -exec chmod 664 {} \\;")
            

    # rimozione file singolo in base al sistema operativo
    def safe_remove_file(self, pathfile):

        # faccio un check per vedere se esiste la cartella
        if not os.path.exists(pathfile) or not os.path.isfile(pathfile):
            print("(safe_remove_file) attenzione " + pathfile + " non esiste o non è un file")
            return 
        
        if(self.is_linux()):
            self.esegui_cmd_as_sudo("rm " + pathfile)
            #os.system('echo %s|sudo -S %s' % ("o7l8b90a", "rm " + pathfile))
        else:
            os.remove(pathfile)
        

    # rimozione directory in modo ricorsivo in base al sistema operativo
    def safe_remove_dir(self, pathdir):

        # faccio un check per vedere se esiste la cartella
        if not os.path.exists(pathdir) or not os.path.isdir(pathdir):
            print("(safe_remove_dir) attenzione " + pathdir + " non esiste o non è una directory")
            return

        if(self.is_linux()):
            self.esegui_cmd_as_sudo("rm -rf " + pathdir)
            #os.system('echo %s|sudo -S %s' % ("o7l8b90a", "rm -rf " + pathdir))
        else:
            shutil.rmtree(pathdir)

    # sposto una directory, gestendo il fatto cje esista o meno, e se sono un linux o meno
    def safe_move_dir(self, path_src, path_dest):
        # controllo che la cartella sorgente esista
        if not os.path.exists(path_src) or not os.path.isdir(path_src):
            print("(safe_move_dir) attenzione " + path_src + " non esiste o non è un directory - ritorno")
            return
        
        # se la cartella destinazione esiste forse la devo prima cancellare con una chiamata safe_remove_dir??
        if os.path.exists(path_dest) and os.path.isdir(path_dest):
            print("(safe_move_dir) attenzione " + path_dest + " esiste - forse la devi cancellare prima??")
        
        # eseguo il comando vero e proprio
        if(self.is_linux()):
            self.esegui_cmd_as_sudo("mv " + path_src + " " + path_dest)
            #os.system('echo %s|sudo -S %s' % ("o7l8b90a", "mv " + path_src + " " + path_dest))
        else:
            shutil.move(path_src, path_dest)
                
    
    # per i sistemi linux esegui il comando come sudo passando la password
    def esegui_cmd_as_sudo(self, comando):
        if(self.is_linux()):
            os.system('echo %s|sudo -S %s' % ("o7l8b90a", comando))


    # controllo se sono una macchina linux - in base al parametro type_machine nel file config.json
    def is_linux(self):
        return self.config["type_machine"] == "redhat" or self.config["type_machine"] == "debian"


    def riavvia_apache(self):
        if(self.config["type_machine"] == "win" ): # sono nel caso di zampgui , in questo caso non faccio niente 
            print("Per rendere effettive le modifiche riavviare apache")
        
        elif(self.config["type_machine"] == "mac"):
            #self.esegui_cmd_as_sudo("sudo apachectl start")
            self.esegui_cmd_as_sudo("apachectl restart")
        
        elif(self.config["type_machine"] == "debian"):
            self.esegui_cmd_as_sudo("systemctl restart apache2")
        
        elif(self.config["type_machine"] == "redhat"):
            self.esegui_cmd_as_sudo("systemctl restart httpd")


    def sito_in_file_hosts(self, nome_sito):

        contenuto = ""
        path_host = ""

        if(self.is_linux() or self.config["type_machine"] == "mac"):
            path_host = "/etc/hosts"
        else:
            path_host = "C:\Windows\System32\drivers\etc\hosts"

        file = open(path_host, "r")
        contenuto = file.read()
        file.close()

        # print(contenuto)
        n_match = contenuto.count(nome_sito)
        return n_match > 0
            