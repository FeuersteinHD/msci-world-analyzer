import numpy as np

# Die echten Daten vom MSCI World (ca. 1970 - 2023)
# Quelle: https://www.msci.com/eqb/esg/performance/106.0.all.xls
Msci_History = [
    -5.71, 15.59, 19.96, -17.08, -27.83, 28.91, 10.31, -2.46, 
    12.68, 7.21, 21.46, -7.92, 5.82, 18.56, 1.77, 37.02, 39.11, 
    14.34, 21.19, 14.75, -18.65, 16.00, -7.14, 20.39, 3.36, 18.70, 
    11.72, 14.17, 22.78, 23.56, -14.05, -17.83, -21.06, 30.81, 12.84, 
    7.56, 17.95, 7.09, -42.08, 26.98, 9.55, -7.61, 13.18, 24.10, 2.93, 
    -2.74, 5.32, 20.11, -10.44, 25.19, 14.06, 20.14, -19.46, 21.77, 
    17.00, 19.49
]

class Data_Provider:
    def hol_daten(self):
        # Umrechnen in Prozent-Faktor (z.B. 0.05 statt 5)
        arr = np.array(Msci_History) / 100.0
        return np.mean(arr), np.std(arr)

class Sim_Rechner:
    
    def __init__(self):
        pass

    # Das ist die Hauptfunktion für die Simulation
    def run_simulation(self, startKapital, rate_monat, jahre, 
                       dynamik=0.0, terKosten=0.0, 
                       gebuehrProzent=0.0, gebuehrFix=0.0,
                       anzahl_sims=10000):
        
        monate_gesamt = int(jahre * 12)
        # Historische Daten laden
        daten_pool = np.array(Msci_History) / 100.0
        
        # --- Bootstrapping Methode ---
        # Ich ziehe zufällige Jahre aus der Vergangenheit
        rand_indices = np.random.randint(0, len(daten_pool), (anzahl_sims, jahre))
        jahres_renditen = daten_pool[rand_indices]
        
        # Umrechnung: Jahresrendite in monatliche Schritte
        # Formel: (1 + Jahr)^(1/12)
        jahres_faktor = 1.0 + jahres_renditen
        monats_faktor_basis = np.power(jahres_faktor, 1.0/12.0)
        
        # Das auf alle Monate verteilen
        wachstums_matrix = np.repeat(monats_faktor_basis, 12, axis=1)

        # Kosten abziehen (TER)
        # TER ist pro Jahr, also durch 12 für Monat
        kosten_faktor = 1 - (terKosten / 100 / 12)
        
        # Hier speichern wir alles
        portfolio = np.zeros((anzahl_sims, monate_gesamt + 1))
        
        # Startkosten abziehen
        kauf_kosten = (startKapital * gebuehrProzent / 100) + gebuehrFix
        portfolio[:, 0] = max(0, startKapital - kauf_kosten)
        
        aktuelle_rate = rate_monat
        gebuehren_summe = np.zeros(anzahl_sims) + kauf_kosten
        
        invest_verlauf = np.zeros(monate_gesamt + 1)
        invest_verlauf[0] = startKapital
        
        # Schleife durch die Zeit
        for t in range(monate_gesamt):
            # Zuerst wächst das Geld (oder fällt)
            faktor = wachstums_matrix[:, t] * kosten_faktor
            neuer_wert = portfolio[:, t] * faktor
            
            # Dann kommt die Sparrate dazu
            # Gebühren für die Sparrate berechnen
            gebuehr = (aktuelle_rate * gebuehrProzent / 100) + gebuehrFix
            netto_sparrate = max(0, aktuelle_rate - gebuehr)
            gebuehren_summe += gebuehr
            
            portfolio[:, t+1] = neuer_wert + netto_sparrate
            invest_verlauf[t+1] = invest_verlauf[t] + aktuelle_rate
            
            # Dynamik: Einmal im Jahr (alle 12 Monate) Sparrate erhöhen
            if (t + 1) % 12 == 0:
                aktuelle_rate *= (1 + dynamik / 100)
        
        return portfolio, gebuehren_summe, invest_verlauf, jahres_renditen

    # Zum Vergleich ein normales Sparkonto
    def rechne_giro(self, start, rate, jahre, zins):
        monate = int(jahre * 12)
        verlauf = np.zeros(monate + 1)
        verlauf[0] = start
        zins_monat = zins / 100 / 12
        
        for i in range(monate):
            verlauf[i+1] = verlauf[i] * (1 + zins_monat) + rate
        return verlauf

    # Hier werden die Ergebnisse ausgewertet
    def mach_analyse(self, portfolio, gebuehren, invest_hist, jahres_returns_sim, inflation, steuer, ziel):
        endwerte = portfolio[:, -1]
        gesamt_investiert = invest_hist[-1]
        
        # Risiko berechnen: Wie oft hab ich weniger als eingezahlt?
        verluste = np.sum(endwerte < gesamt_investiert)
        risiko_quote = (verluste / len(endwerte)) * 100
        
        # Risiko Kurve berechnen
        monate = portfolio.shape[1] - 1
        jahres_schritte = np.arange(0, monate + 1, 12)
        risiko_kurve = []
        
        for idx in jahres_schritte:
            inv_now = invest_hist[idx]
            wert_now = portfolio[:, idx]
            if inv_now > 0:
                anteil = (np.sum(wert_now < inv_now) / len(wert_now)) * 100
                risiko_kurve.append(anteil)
            else:
                risiko_kurve.append(0.0)
        
        # Median finden (die Mitte)
        mitte_idx = np.argsort(endwerte)[len(endwerte)//2]
        median_weg = portfolio[mitte_idx, :]
        median_gebuehr = gebuehren[mitte_idx]
        
        # Inflation rausrechnen
        jahre = (portfolio.shape[1] - 1) / 12
        discount = (1 + inflation / 100) ** jahre
        
        # Steuer abziehen
        gewinn = np.maximum(0, endwerte - gesamt_investiert)
        steuern = gewinn * (steuer / 100)
        netto_nominal = endwerte - steuern
        netto_real = netto_nominal / discount
        
        # Renditen für das Diagramm holen
        jahres_renditen = jahres_returns_sim[mitte_idx] * 100
        
        # Drawdown berechnen (Maximaler Verlust)
        hochpunkt = np.maximum.accumulate(median_weg)
        # Damit es nicht durch 0 teilt
        with np.errstate(divide='ignore', invalid='ignore'):
            dd = (median_weg - hochpunkt) / hochpunkt
            dd[0] = 0

        # Hab ich mein Ziel erreicht?
        ziel_erreicht = (np.sum(netto_nominal >= ziel) / len(endwerte)) * 100
        
        # Alles in ein Dictionary packen
        return {
            'worst_case': np.percentile(netto_real, 5),
            'median': np.percentile(netto_real, 50),
            'best_case': np.percentile(netto_real, 95),
            'raw_final_values': netto_real,
            'raw_history': portfolio,
            'invested_history': invest_hist,
            'risk_total': risiko_quote,
            'risk_curve': risiko_kurve,
            'drawdown': dd,
            'years': jahre,
            'median_fees': median_gebuehr,
            'yearly_returns': jahres_renditen,
            'median_path_nominal': median_weg,
            'success_prob': ziel_erreicht,
            'target_amount': ziel,
            'total_invested': gesamt_investiert
        }