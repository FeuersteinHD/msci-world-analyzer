<img src="https://raw.githubusercontent.com/FeuersteinHD/msci-world-analyzer/main/assets/banner.svg" width="100%"/>

<div align="center">

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=16&duration=2600&pause=900&color=ff6600&center=true&vCenter=true&width=560&lines=Monte+Carlo+Bootstrap+%C2%B7+10.000+Simulationen;MSCI+World+Historik+1970%E2%80%932023;PyQt5+%C2%B7+NumPy+%C2%B7+Pandas+%C2%B7+Matplotlib;Belegarbeit+BGY+Sachsen+%C2%B7+Informatiksysteme)](https://git.io/typing-svg)

</div>

---

## Features

<table>
  <tr><td>&#x1F4CA; <b>Simulation</b></td><td>10.000 Bootstrap-Szenarien auf Basis echter MSCI-World-Renditen (1970&ndash;2023)</td></tr>
  <tr><td>&#x1F4C8; <b>8 Charts</b></td><td>Portfolioverlauf, Risikoverlauf, Drawdown, Renditeverteilung, Erfolgswahrscheinlichkeit u.v.m.</td></tr>
  <tr><td>&#x1F4B6; <b>Kostenmodell</b></td><td>TER, Ordergebühren (Fix + %), dynamische Sparratenerhöhung</td></tr>
  <tr><td>&#x1F4C9; <b>Realwert</b></td><td>Inflation &amp; Kapitalertragssteuer einkalkuliert</td></tr>
  <tr><td>&#x1F504; <b>Szenarien</b></td><td>Mehrere Parametersätze gleichzeitig vergleichen</td></tr>
  <tr><td>&#x1F4C1; <b>Export</b></td><td>CSV (deutsches Excel), HTML-Report mit Charts, JSON Speichern/Laden</td></tr>
</table>

---

## Vorschau

<div align="center">
<img src="https://raw.githubusercontent.com/FeuersteinHD/msci-world-analyzer/main/assets/screenshot.png" width="100%"/>
</div>

---

## Installation

```bash
git clone https://github.com/FeuersteinHD/msci-world-analyzer.git
cd msci-world-analyzer
pip install -r requirements.txt
python main.py
```

---

## So funktioniert die Simulation

Statt einfacher Durchschnittswerte wird **Bootstrap Resampling** verwendet:

1. Echte MSCI-World-Jahresrenditen (1970&ndash;2023) als Datenpool
2. Für jede der 10.000 Simulationen werden Jahre zufällig gezogen
3. Jahresrenditen werden in monatliche Faktoren umgerechnet (Zinseszins-Formel)
4. Sparraten, TER und Ordergebühren werden Monat für Monat abgezogen
5. Ergebnis: 5. / 50. / 95. Perzentil (Worst Case / Median / Best Case)

---

## Tech Stack

<div align="center">

[![Python](https://img.shields.io/badge/Python-f97316?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![PyQt5](https://img.shields.io/badge/PyQt5-ff6600?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![NumPy](https://img.shields.io/badge/NumPy-c2410c?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org)
[![Pandas](https://img.shields.io/badge/Pandas-ea580c?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-ff8c00?style=for-the-badge&logoColor=white)](https://matplotlib.org)

</div>

---

## Projektstruktur

```
msci-world-analyzer/
├── main.py          # Einstiegspunkt
├── gui.py           # PyQt5 Hauptfenster, Charts, UI-Logik
├── simulation.py    # Bootstrap-Simulation & Auswertung
├── storage.py       # JSON Speichern/Laden, HTML-Report-Export
├── utils.py         # Währungsformat, CSV-Export
└── requirements.txt
```

---

<div align="center">
<sub>BGY Sachsen &middot; 12. Klasse &middot; Informatiksysteme</sub>
</div>

<img src="https://capsule-render.vercel.app/api?type=soft&color=0:060200,50:3d0800,100:060200&height=80&section=footer&reversal=true" width="100%"/>