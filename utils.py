import locale
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QFileDialog

# Funktion damit die Zahlen schön als Euro angezeigt werden
def machEuro(wert):
    try:
        locale.setlocale(locale.LC_ALL, '')
        return locale.currency(wert, grouping=True)
    except:
        return f"{wert:,.2f} €"

# Das hier speichert die Daten für Excel
def export_csv_data(statistiken, elternFenster):
    optionen = QFileDialog.Options()
    fileName, _ = QFileDialog.getSaveFileName(
        elternFenster, 
        "Speichern unter...", 
        "Meine_Analyse.csv", 
        "CSV Dateien (*.csv)", 
        options=optionen
    )
    
    if not fileName:
        return False, "Abgebrochen"

    try:
        # Daten holen
        matrix_daten = statistiken['raw_history']
        anzahl_monate = matrix_daten.shape[1]
        
        # Ich nehme nur jedes 12. Element, also einmal pro Jahr
        jahres_indices = np.arange(0, anzahl_monate, 12)
        jahreListe = np.arange(0, len(jahres_indices))
        
        # Hier berechne ich die Linien für das Diagramm
        mitte = np.percentile(matrix_daten, 50, axis=0)[jahres_indices]
        schlecht = np.percentile(matrix_daten, 5, axis=0)[jahres_indices]
        gut = np.percentile(matrix_daten, 95, axis=0)[jahres_indices]
        
        giro_konto = statistiken['giro_history'][jahres_indices]
        
        # Wie viel habe ich selbst eingezahlt?
        monatsRate = statistiken['params']['monthly_savings']
        startGeld = statistiken['params']['initial_capital']
        invested_sum = startGeld + (monatsRate * 12 * jahreListe)
        
        # Tabelle erstellen mit pandas
        meineTabelle = pd.DataFrame({
            'Jahr': jahreListe,
            'Investiert': invested_sum,
            'Girokonto': giro_konto,
            'Durchschnitt_ETF': mitte,
            'Pech_Fall': schlecht,
            'Gluecks_Fall': gut,
            'Reiner_Gewinn': mitte - invested_sum
        })
        
        # Runden damit es besser aussieht
        meineTabelle = meineTabelle.round(2)
        
        # Speichern (mit Semikolon für deutsches Excel)
        meineTabelle.to_csv(fileName, index=False, sep=';', decimal=',')
        
        return True, fileName
        
    except Exception as fehler:
        return False, str(fehler)