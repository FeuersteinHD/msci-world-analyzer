import sys
import os
from PyQt5.QtWidgets import QApplication
from gui import HauptFenster

# Das hier braucht man für Windows Bildschirme mit hoher Auflösung
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

if __name__ == "__main__":
    # App starten
    meineApp = QApplication(sys.argv)
    meineApp.setStyle("Fusion") 
    
    # Fenster anzeigen
    fenster = HauptFenster()
    fenster.show()
    
    # Warten bis man das Fenster schließt
    sys.exit(meineApp.exec_())