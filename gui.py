import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg') 

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QLabel, QDoubleSpinBox, QSpinBox, 
                             QPushButton, QProgressBar, QTabWidget, QMessageBox, 
                             QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QAction, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

# Importe der eigenen Module
from simulation import Data_Provider, Sim_Rechner
from utils import machEuro, export_csv_data
from storage import Datei_Manager

# Hintergrund-Arbeiter damit das Fenster nicht hängt
class Worker_Thread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.parameter = params

    def run(self):
        try:
            # Rechner initialisieren
            kern = Sim_Rechner()
            
            # Simulation starten
            # Ich brauche 4 Rückgabewerte hier
            matrix, gebuehren, invest_hist, jahres_returns = kern.run_simulation(
                self.parameter['initial_capital'], 
                self.parameter['monthly_savings'], 
                self.parameter['years'],
                dynamik=self.parameter['savings_increase'],
                terKosten=self.parameter['ter'],
                gebuehrProzent=self.parameter['fee_percent'],
                gebuehrFix=self.parameter['fee_fixed'],
                anzahl_sims=self.parameter['num_sims']
            )
            
            # Sparkonto ausrechnen zum Vergleich
            giro_hist = kern.rechne_giro(
                self.parameter['initial_capital'], 
                self.parameter['monthly_savings'], 
                self.parameter['years'],
                zins=self.parameter['savings_interest']
            )
            
            # Analyse machen
            ergebnis = kern.mach_analyse(
                matrix, gebuehren, invest_hist, jahres_returns,
                inflation=self.parameter['inflation'], 
                steuer=self.parameter['tax'],
                ziel=self.parameter['target_amount']
            )
            
            # Restliche Sachen dazu packen
            ergebnis['giro_history'] = giro_hist
            ergebnis['params'] = self.parameter
            
            self.finished.emit(ergebnis)
        except Exception as e:
            self.error.emit(str(e))

class HauptFenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Belegarbeit - Analyse eines Aktienfonds (Altersvorsorge) - MSCI World")
        self.setGeometry(50, 50, 1600, 1000)
        self.letzte_daten = None 
        self.historie = [] 
        
        self.setStyleSheet("""
            QMainWindow { background-color: #f4f7f6; color: #333; }
            QGroupBox { font-weight: bold; border: 1px solid #dce1e4; border-radius: 6px; margin-top: 15px; background: white; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #2c3e50; }
            QPushButton { background-color: #3498db; color: white; border-radius: 4px; padding: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #bdc3c7; }
            QPushButton#btn_export { background-color: #27ae60; }
            QPushButton#btn_save_graph { background-color: #7f8c8d; }
            QTabWidget::pane { border: 1px solid #dce1e4; background: white; border-radius: 4px; }
            QTabBar::tab { background: #ecf0f1; color: #7f8c8d; padding: 10px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: white; color: #2c3e50; border-bottom: 2px solid #3498db; font-weight: bold; }
            QTableWidget { border: none; gridline-color: #ecf0f1; }
            QHeaderView::section { background-color: #f4f7f6; padding: 8px; border: none; font-weight: bold; color: #2c3e50; }
        """)
        
        self.bau_menue()
        self.bau_gui()

    def bau_menue(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Datei')
        
        actSave = QAction('Projekt speichern', self)
        actSave.setShortcut('Ctrl+S')
        actSave.triggered.connect(self.save_Project)
        fileMenu.addAction(actSave)
        
        actLoad = QAction('Projekt laden', self)
        actLoad.setShortcut('Ctrl+O')
        actLoad.triggered.connect(self.load_Project)
        fileMenu.addAction(actLoad)
        
        fileMenu.addSeparator()
        
        actReport = QAction('Bericht exportieren (HTML)', self)
        actReport.setShortcut('Ctrl+P')
        actReport.triggered.connect(self.create_Report)
        fileMenu.addAction(actReport)

    def bau_gui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(420)
        vbox = QVBoxLayout(sidebar)
        
        # 1. Box für Strategie
        box1 = QGroupBox("1. Anlagestrategie")
        form1 = QFormLayout()
        form1.setSpacing(10)
        
        self.inputKapital = QDoubleSpinBox(); self.inputKapital.setRange(0, 1e8); self.inputKapital.setValue(0); self.inputKapital.setPrefix("€ ") # Startkapital auf 0€
        self.inputSparrate = QDoubleSpinBox(); self.inputSparrate.setRange(0, 1e6); self.inputSparrate.setValue(200); self.inputSparrate.setPrefix("€ ") # Monatliche Investition auf 200 €
        self.inputJahre = QSpinBox(); self.inputJahre.setRange(1, 99); self.inputJahre.setValue(30); self.inputJahre.setSuffix(" Jahre") # Standartmäßig auf 30 Jahre
        self.inputDynamik = QDoubleSpinBox(); self.inputDynamik.setValue(0); self.inputDynamik.setSuffix(" % p.a.") # Setzen wir Pauschal auf 0 % um es einfacher zu halten
        self.inputZiel = QDoubleSpinBox(); self.inputZiel.setRange(0, 1e9); self.inputZiel.setValue(500000); self.inputZiel.setPrefix("Ziel: € ") # Eig. irrelevant
        
        form1.addRow("Startkapital:", self.inputKapital)
        form1.addRow("Sparrate (mtl.):", self.inputSparrate)
        form1.addRow("Anlagehorizont:", self.inputJahre)
        form1.addRow("Dynamik:", self.inputDynamik)
        form1.addRow("Zielkapital (Nominal):", self.inputZiel)
        box1.setLayout(form1)
        
        # 2. Box für Kosten
        box2 = QGroupBox("2. Kosten- & Marktparameter")
        form2 = QFormLayout()
        
        self.inputTer = QDoubleSpinBox(); self.inputTer.setValue(0.15); self.inputTer.setSuffix(" % p.a.") # Ich gehe vom HSBC MSCI World UCITS ETF USD (Acc) (ISIN: IE000UQND7H4)
        self.inputFixkosten = QDoubleSpinBox(); self.inputFixkosten.setValue(0); self.inputFixkosten.setPrefix("€ ") # Als Sparplan bei TradersPlace keine gebühr
        self.inputInflation = QDoubleSpinBox(); self.inputInflation.setValue(2.2); self.inputInflation.setSuffix(" % p.a.") # Inflaiton im Jahr 2025 betrug 2,2%
        self.inputSteuer = QDoubleSpinBox(); self.inputSteuer.setValue(26.375); self.inputSteuer.setSuffix(" %") # 25% + Soli (26,375 %)
        self.inputZins = QDoubleSpinBox(); self.inputZins.setValue(1.0); self.inputZins.setSuffix(" % p.a.") # Setz ich auf 1 %
        self.inputSims = QSpinBox(); self.inputSims.setRange(1000, 500000); self.inputSims.setValue(100000) # 100.000 Widerholungen

        form2.addRow("Produktkosten (TER):", self.inputTer)
        form2.addRow("Ordergebühr (Fix):", self.inputFixkosten)
        form2.addRow("Inflation:", self.inputInflation)
        form2.addRow("Referenzzins (Sparkonto)):", self.inputZins)
        form2.addRow("Steuersatz (KapESt):", self.inputSteuer)
        form2.addRow("Monte-Carlo Wiederholungen:", self.inputSims)
        box2.setLayout(form2)
        
        vbox.addWidget(box1)
        vbox.addWidget(box2)
        
        # Buttons
        self.startBtn = QPushButton("Berechnung starten")
        self.startBtn.clicked.connect(self.button_start_clicked)
        vbox.addWidget(self.startBtn)
        
        self.exportBtn = QPushButton("Rohdaten exportieren (CSV)")
        self.exportBtn.setObjectName("btn_export")
        self.exportBtn.clicked.connect(self.button_export_clicked)
        self.exportBtn.setEnabled(False)
        vbox.addWidget(self.exportBtn)
        
        self.saveGraphBtn = QPushButton("Aktuelle Grafik speichern")
        self.saveGraphBtn.setObjectName("btn_save_graph")
        self.saveGraphBtn.clicked.connect(self.button_save_graph_clicked)
        self.saveGraphBtn.setEnabled(False)
        vbox.addWidget(self.saveGraphBtn)
        
        self.progress = QProgressBar(); self.progress.hide()
        vbox.addWidget(self.progress)
        vbox.addStretch()

        # Content Area rechts
        right_widget = QWidget()
        vbox_right = QVBoxLayout(right_widget)
        
        self.tabs = QTabWidget()
        
        def mach_tab(): 
            w = QWidget(); l = QVBoxLayout(w); f = Figure(figsize=(5, 4), dpi=100); c = FigureCanvas(f); l.addWidget(c); return w, c, f
        
        self.tab1, self.cv1, self.fig1 = mach_tab()
        self.tabs.addTab(self.tab1, "📈 Verlauf")
        self.tab2, self.cv2, self.fig2 = mach_tab()
        self.tabs.addTab(self.tab2, "🏗️ Kapitalstruktur")
        self.tab3, self.cv3, self.fig3 = mach_tab()
        self.tabs.addTab(self.tab3, "📅 Jahres-Renditen")
        self.tab4, self.cv4, self.fig4 = mach_tab()
        self.tabs.addTab(self.tab4, "🎲 Renditeverteilung")
        self.tab5, self.cv5, self.fig5 = mach_tab()
        self.tabs.addTab(self.tab5, "📉 Risikoverlauf")
        self.tab6, self.cv6, self.fig6 = mach_tab()
        self.tabs.addTab(self.tab6, "📊 Endergebnis")
        self.tab7, self.cv7, self.fig7 = mach_tab()
        self.tabs.addTab(self.tab7, "🍰 Erfolgswahrscheinlichkeit")
        self.tab8, self.cv8, self.fig8 = mach_tab()
        self.tabs.addTab(self.tab8, "🌊 Maximum Drawdown")
        
        self.tabTbl = QWidget(); l_tbl = QVBoxLayout(self.tabTbl)
        self.table = QTableWidget(); self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Szenario", "Risiko", "Median (Ende)", "Investiert", "Gewinn"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        l_tbl.addWidget(self.table)
        self.figComp = Figure(figsize=(5, 3), dpi=100); self.cvComp = FigureCanvas(self.figComp)
        l_tbl.addWidget(self.cvComp)
        self.tabs.addTab(self.tabTbl, "⚖️ Vergleich")

        vbox_right.addWidget(self.tabs)
        self.statusLabel = QLabel("Bitte Parameter eingeben und Berechnung starten.")
        self.statusLabel.setStyleSheet("padding: 10px; background: white; border: 1px solid #dce1e4; border-radius: 4px; color: #555;")
        vbox_right.addWidget(self.statusLabel)
        
        layout.addWidget(sidebar)
        layout.addWidget(right_widget)

    # --- LOGIK ---

    def button_save_graph_clicked(self):
        if not self.letzte_daten: return
        idx = self.tabs.currentIndex()
        mapping = {
            0: (self.cv1, "verlauf.png"), 1: (self.cv2, "kapitalstruktur.png"),
            2: (self.cv3, "jahres_renditen.png"), 3: (self.cv4, "rendite_dist.png"),
            4: (self.cv5, "risiko.png"), 5: (self.cv6, "verteilung.png"),
            6: (self.cv7, "erfolg.png"), 7: (self.cv8, "drawdown.png"),
            8: (self.cvComp, "vergleich.png")
        }
        if idx in mapping:
            canv, name = mapping[idx]
            opt = QFileDialog.Options()
            fn, _ = QFileDialog.getSaveFileName(self, "Grafik exportieren", name, "PNG (*.png);;SVG (*.svg);;JPG (*.jpg)", options=opt)
            if fn: canv.print_figure(fn, dpi=300)

    def save_Project(self):
        if not self.letzte_daten: return
        fn, _ = QFileDialog.getSaveFileName(self, "Speichern", "", "JSON (*.json)")
        if fn: Datei_Manager.speichere_json(fn, self.letzte_daten)

    def load_Project(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Laden", "", "JSON (*.json)")
        if fn:
            stats = Datei_Manager.lade_json(fn)
            self.letzte_daten = stats
            p = stats['params']
            
            # GUI wieder befüllen
            self.inputKapital.setValue(p['initial_capital'])
            self.inputSparrate.setValue(p['monthly_savings'])
            self.inputJahre.setValue(p['years'])
            self.inputDynamik.setValue(p['savings_increase'])
            self.inputZiel.setValue(p['target_amount'])
            self.inputTer.setValue(p['ter'])
            self.inputFixkosten.setValue(p['fee_fixed'])
            
            self.historie.append(stats)
            self.update_anzeige(stats)
            self.saveGraphBtn.setEnabled(True); self.exportBtn.setEnabled(True)

    def create_Report(self):
        if not self.letzte_daten: return
        fn, _ = QFileDialog.getSaveFileName(self, "Bericht", "Bericht.html", "HTML (*.html)")
        if fn:
            figs = {
                "Vermögensverlauf": self.fig1, "Kapitalstruktur": self.fig2,
                "Jahresrenditen": self.fig3, "Risikoverlauf": self.fig5,
                "Verteilung": self.fig6, "Erfolgschancen": self.fig7
            }
            Datei_Manager.erstelle_report(self.letzte_daten, fn, figs)
            import webbrowser; webbrowser.open('file://' + os.path.realpath(fn))

    def update_anzeige(self, stats):
        name = stats.get('name', 'Geladen')
        loss = stats.get('risk_total', 0.0)
        color = "#c0392b" if loss > 20 else "#d35400" if loss > 5 else "#27ae60"
        self.statusLabel.setText(
            f"<b>Ergebnis ({name}):</b> Investiert: {machEuro(stats['total_invested'])} | "
            f"Verlustrisiko: <span style='color:{color}'>{loss:.1f}%</span> | "
            f"Median (Kaufkraft): {machEuro(stats['median'])}"
        )
        self.plot_hist(stats); self.plot_comp(stats); self.plot_years(stats)
        self.plot_ydist(stats); self.plot_risk(stats); self.plot_dist(stats)
        self.plot_pie(stats); self.plot_draw(stats); self.update_table()

    def button_start_clicked(self):
        self.startBtn.setEnabled(False)
        self.progress.setRange(0, 0); self.progress.show()
        self.statusLabel.setText("Berechnung läuft...")
        
        # Parameter einsammeln
        params = {
            'initial_capital': self.inputKapital.value(), 'monthly_savings': self.inputSparrate.value(),
            'years': self.inputJahre.value(), 'savings_increase': self.inputDynamik.value(),
            'target_amount': self.inputZiel.value(), 'ter': self.inputTer.value(),
            'fee_fixed': self.inputFixkosten.value(), 'fee_percent': 0.0,
            'inflation': self.inputInflation.value(), 'tax': self.inputSteuer.value(),
            'savings_interest': self.inputZins.value(), 'num_sims': self.inputSims.value()
        }
        self.arbeiter = Worker_Thread(params)
        self.arbeiter.finished.connect(self.on_Done)
        self.arbeiter.error.connect(self.on_Err)
        self.arbeiter.start()

    def on_Err(self, msg):
        self.progress.hide(); self.startBtn.setEnabled(True); QMessageBox.critical(self, "Fehler", msg)

    def on_Done(self, stats):
        self.progress.hide(); self.startBtn.setEnabled(True)
        self.exportBtn.setEnabled(True); self.saveGraphBtn.setEnabled(True)
        self.letzte_daten = stats
        stats['name'] = f"Szenario {len(self.historie)+1}"
        self.historie.append(stats)
        self.update_anzeige(stats)

    def button_export_clicked(self):
        if self.letzte_daten:
            success, msg = export_csv_data(self.letzte_daten, self)
            if success: QMessageBox.information(self, "Export", f"Gespeichert: {msg}")

    # --- PLOTTING ---
    def _setup_ax(self, ax, title, xlabel, ylabel):
        ax.set_title(title, fontweight='bold', fontsize=10, pad=10, color='#333')
        ax.set_xlabel(xlabel, fontsize=9, color='#555'); ax.set_ylabel(ylabel, fontsize=9, color='#555')
        ax.grid(True, ls=':', alpha=0.6); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    def _curr(self, x, p): return f'{x:,.0f} €'
    def _pct(self, x, p): return f'{x:.0f} %'

    def plot_hist(self, stats):
        self.fig1.clear(); ax = self.fig1.add_subplot(111)
        if 'raw_history' in stats:
            m = stats['raw_history']; x = np.linspace(0, stats['years'], m.shape[1])
            p5 = np.percentile(m, 5, axis=0); p50 = np.percentile(m, 50, axis=0); p95 = np.percentile(m, 95, axis=0)
            ax.fill_between(x, p5, p95, color='#3498db', alpha=0.15)
            ax.plot(x, p50, color='#2980b9', lw=2, label='Median')
            ax.plot(x, stats['invested_history'], color='#34495e', lw=2, label='Investiert')
        else:
            p50 = stats['median_path_nominal']; x = np.linspace(0, stats['params']['years'], len(p50))
            ax.plot(x, p50, color='#2980b9', lw=2, label='Median')
        self._setup_ax(ax, 'Vermögensentwicklung (Nominal)', 'Jahre', 'Wert')
        ax.yaxis.set_major_formatter(FuncFormatter(self._curr)); ax.legend(loc='upper left'); self.cv1.draw()

    def plot_comp(self, stats):
        self.fig2.clear(); ax = self.fig2.add_subplot(111)
        if 'median_path_nominal' in stats:
            m = stats['median_path_nominal']; inv = stats['invested_history']
            l = min(len(m), len(inv)); m=m[:l]; inv=inv[:l]; x=np.linspace(0, stats['params']['years'], l)
            ax.plot(x, inv, color='#7f8c8d'); ax.plot(x, m, color='#2980b9')
            ax.fill_between(x, inv, 0, color='#bdc3c7', alpha=0.3, label='Einzahlungen')
            ax.fill_between(x, m, inv, where=(m>=inv), interpolate=True, color='#27ae60', alpha=0.3, label='Gewinn')
            ax.fill_between(x, m, inv, where=(m<inv), interpolate=True, color='#c0392b', alpha=0.3, label='Verlust')
            self._setup_ax(ax, "Kapitalstruktur (Median)", "Jahre", "Wert"); ax.yaxis.set_major_formatter(FuncFormatter(self._curr)); ax.legend(); self.cv2.draw()

    def plot_years(self, stats):
        self.fig3.clear(); ax = self.fig3.add_subplot(111)
        r = stats['yearly_returns']; x = range(1, len(r)+1)
        c = ['#27ae60' if v>=0 else '#c0392b' for v in r]
        bars = ax.bar(x, r, color=c, alpha=0.8); ax.axhline(0, color='black')
        for rect in bars:
            h = rect.get_height(); y = h + (1 if h>0 else -4)
            ax.text(rect.get_x()+rect.get_width()/2, y, f'{h:.1f}%', ha='center', fontsize=8, color='#333')
        self._setup_ax(ax, "Jahres-Renditen (Median)", "Jahr", "Rendite"); ax.yaxis.set_major_formatter(FuncFormatter(self._pct)); self.cv3.draw()

    def plot_ydist(self, stats):
        self.fig4.clear(); ax = self.fig4.add_subplot(111)
        r = stats['yearly_returns']; ax.hist(r, bins=15, color='#2980b9', alpha=0.7, edgecolor='white')
        self._setup_ax(ax, "Verteilung Jahresrenditen", "Rendite", "Häufigkeit"); ax.xaxis.set_major_formatter(FuncFormatter(self._pct)); self.cv4.draw()

    def plot_risk(self, stats):
        self.fig5.clear(); ax = self.fig5.add_subplot(111)
        c = stats['risk_curve']; x = np.linspace(0, stats['years'], len(c))
        ax.plot(x, c, color='#c0392b', lw=2); ax.fill_between(x, c, 0, color='#c0392b', alpha=0.1)
        self._setup_ax(ax, "Risiko (Verlustwahrscheinlichkeit)", "Jahre", "%"); ax.yaxis.set_major_formatter(FuncFormatter(self._pct)); self.cv5.draw()

    def plot_dist(self, stats):
        self.fig6.clear(); ax = self.fig6.add_subplot(111)
        vals = stats['raw_history'][:, -1] if 'raw_history' in stats else stats['raw_final_values']
        inv = stats['total_invested']
        _, bins, patches = ax.hist(vals, bins=70, edgecolor='white')
        for b1, b2, p in zip(bins[:-1], bins[1:], patches):
            p.set_facecolor('#c0392b' if (b1+b2)/2 < inv else '#27ae60')
            p.set_alpha(0.7)
        ax.axvline(inv, color='#333', ls='--', label='Investiert')
        self._setup_ax(ax, 'Verteilung Endkapital', 'Kapital', 'Anzahl'); ax.xaxis.set_major_formatter(FuncFormatter(self._curr)); ax.legend(); self.cv6.draw()

    def plot_pie(self, stats):
        self.fig7.clear()
        ax = self.fig7.add_subplot(111)
        vals = stats['raw_history'][:, -1] if 'raw_history' in stats else stats['raw_final_values']
        inv = stats['total_invested']; tgt = stats['target_amount']
        loss = np.sum(vals < inv); win = np.sum((vals >= inv) & (vals < tgt)); goal = np.sum(vals >= tgt)
        sizes = [goal, win, loss]; labels = ['Ziel erreicht', 'Positiv', 'Verlust']; colors = ['#27ae60', '#f1c40f', '#c0392b']
        f_s, f_l, f_c = [], [], []
        for s, l, c in zip(sizes, labels, colors):
            if s > 0: f_s.append(s); f_l.append(l); f_c.append(c)
        def my_autopct(pct): return f'{pct:.1f}%' if pct > 3 else ''
        wedges, texts, autotexts = ax.pie(f_s, colors=f_c, autopct=my_autopct, startangle=90, pctdistance=0.75, textprops=dict(color="black"))
        for at in autotexts: at.set_color('white'); at.set_weight('bold'); at.set_fontsize(9)
        ax.legend(wedges, f_l, title="Legende", loc="lower left", bbox_to_anchor=(0, -0.1), frameon=False, ncol=3, fontsize=8)
        ax.set_title("Erfolgswahrscheinlichkeiten", fontweight='bold', pad=10)
        self.fig7.tight_layout()
        self.cv7.draw()

    def plot_draw(self, stats):
        self.fig8.clear(); ax = self.fig8.add_subplot(111)
        d = stats['drawdown'] * 100; x = np.linspace(0, stats['years'], len(d))
        ax.fill_between(x, d, 0, color='#c0392b', alpha=0.3); ax.plot(x, d, color='#c0392b')
        self._setup_ax(ax, "Maximaler Drawdown", "Jahre", "Verlust"); ax.yaxis.set_major_formatter(FuncFormatter(self._pct)); self.cv8.draw()

    def update_table(self):
        self.table.setRowCount(0)
        for r in self.historie:
            row = self.table.rowCount(); self.table.insertRow(row)
            items = [r['name'], f"{r.get('risk_total',0):.1f}%", machEuro(r['median_path_nominal'][-1]), 
                     machEuro(r['total_invested']), machEuro(r['median_path_nominal'][-1]-r['total_invested'])]
            for i, t in enumerate(items): self.table.setItem(row, i, QTableWidgetItem(str(t)))
        self.figComp.clear(); ax = self.figComp.add_subplot(111)
        for r in self.historie:
            m = r['median_path_nominal']; x = np.linspace(0, r['params']['years'], len(m))
            ax.plot(x, m, lw=2, label=r['name'])
        self._setup_ax(ax, 'Vergleich', 'Jahre', 'Wert'); ax.yaxis.set_major_formatter(FuncFormatter(self._curr)); ax.legend(); self.cvComp.draw()