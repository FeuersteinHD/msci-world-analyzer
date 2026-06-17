import json
import numpy as np
import os
import io
import base64
import pandas as pd

class Datei_Manager:
    
    @staticmethod
    def speichere_json(dateiname, stats):
        export_dict = {}
        # Durch alle Daten gehen
        for k, v in stats.items():
            if k == 'raw_history': continue # Das ist zu riesig zum speichern
            
            if isinstance(v, np.ndarray):
                export_dict[k] = v.tolist()
            elif isinstance(v, dict):
                export_dict[k] = Datei_Manager._fix_dict(v)
            elif isinstance(v, (np.int64, np.int32)):
                export_dict[k] = int(v)
            elif isinstance(v, (np.float64, np.float32)):
                export_dict[k] = float(v)
            else:
                export_dict[k] = v
                
        with open(dateiname, 'w', encoding='utf-8') as f:
            json.dump(export_dict, f, indent=4, ensure_ascii=False)
        return True

    @staticmethod
    def lade_json(dateiname):
        if not os.path.exists(dateiname): 
            raise FileNotFoundError(f"Datei gibts nicht: {dateiname}")
            
        with open(dateiname, 'r', encoding='utf-8') as f: 
            daten = json.load(f)
            
        # Wir müssen die Listen wieder in Numpy Arrays umwandeln für die Graphen
        listen_keys = ['raw_final_values', 'drawdown', 'giro_history', 'median_path_nominal', 
                       'yearly_returns', 'invested_history', 'risk_curve']
        for k in listen_keys:
            if k in daten: 
                daten[k] = np.array(daten[k])
        return daten

    @staticmethod
    def _fix_dict(d):
        neu = {}
        for k, v in d.items():
            if isinstance(v, (np.int64, np.int32)): neu[k] = int(v)
            elif isinstance(v, (np.float64, np.float32)): neu[k] = float(v)
            else: neu[k] = v
        return neu

    @staticmethod
    def erstelle_report(stats, dateiname, bilder=None):
        p = stats['params']
        median_wert = stats.get('median_path_nominal', [0])[-1]
        investiert = stats.get('total_invested', 0)
        gewinn = median_wert - investiert
        
        # Bilder einfügen
        bilder_html = ""
        if bilder:
            bilder_html += "<div class='page-break'></div><h2>5. Grafiken</h2><div class='grid'>"
            for titel, fig in bilder.items():
                puffer = io.BytesIO()
                fig.savefig(puffer, format='png', bbox_inches='tight', dpi=100)
                puffer.seek(0)
                b64_string = base64.b64encode(puffer.read()).decode('utf-8')
                bilder_html += f"""
                <div class="card chart-card">
                    <h3>{titel}</h3>
                    <img src="data:image/png;base64,{b64_string}" style="width: 100%; height: auto;">
                </div>"""
            bilder_html += "</div>"

        # HTML Code zusammenbauen
        html = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <title>Report: {stats.get('name', 'Simulation')}</title>
            <style>
                body {{ font-family: sans-serif; max-width: 1100px; margin: 0 auto; background-color: #f4f7f6; color: #333; }}
                h1 {{ color: #2c3e50; border-bottom: 4px solid #3498db; padding-bottom: 15px; margin-bottom: 40px; }}
                h2 {{ color: #34495e; border-left: 5px solid #3498db; padding-left: 15px; margin-top: 40px; }}
                h3 {{ color: #7f8c8d; font-size: 1.1rem; margin-bottom: 15px; }}
                .container {{ background: white; padding: 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin: 40px; border-radius: 8px; }}
                .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
                .card {{ background: #fff; border: 1px solid #eee; padding: 20px; border-radius: 6px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                td {{ padding: 10px 0; border-bottom: 1px solid #f9f9f9; }}
                .label {{ color: #7f8c8d; font-weight: 500; width: 60%; }}
                .value {{ font-family: monospace; font-weight: 600; color: #2c3e50; text-align: right; }}
                .green {{ color: #27ae60; }}
                .red {{ color: #c0392b; }}
                .footer {{ margin-top: 60px; text-align: center; color: #bdc3c7; font-size: 0.8rem; border-top: 1px solid #eee; padding-top: 20px; }}
                @media print {{ body {{ background: white; }} .container {{ box-shadow: none; margin: 0; }} .page-break {{ page-break-before: always; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>ANALYSE AKTIENFONDS (MSCI WORLD)</h1>
                <div style="text-align:center; color:#95a5a6; margin-bottom: 40px;">Datum: {pd.Timestamp.now().strftime('%d.%m.%Y')}</div>
                
                <div class="grid">
                    <div class="card">
                        <h3>1. Setup</h3>
                        <table>
                            <tr><td class="label">Startkapital</td><td class="value">{p['initial_capital']:,.2f} €</td></tr>
                            <tr><td class="label">Sparrate</td><td class="value">{p['monthly_savings']:,.2f} €</td></tr>
                            <tr><td class="label">Laufzeit</td><td class="value">{p['years']} Jahre</td></tr>
                            <tr><td class="label">Dynamik</td><td class="value">{p['savings_increase']} %</td></tr>
                        </table>
                    </div>
                    <div class="card">
                        <h3>2. Kosten</h3>
                        <table>
                            <tr><td class="label">TER</td><td class="value">{p['ter']} % p.a.</td></tr>
                            <tr><td class="label">Ordergebühr</td><td class="value">{p.get('fee_fixed', 0):.2f} €</td></tr>
                            <tr><td class="label">Steuer</td><td class="value">{p['tax']} %</td></tr>
                            <tr><td class="label">Gebühren Ø</td><td class="value red">{stats.get('median_fees', 0):,.2f} €</td></tr>
                        </table>
                    </div>
                </div>

                <h2>3. Ergebnisse (Median)</h2>
                <div class="card" style="border-left: 5px solid #3498db;">
                    <table>
                        <tr><td class="label">Investiert (Gesamt)</td><td class="value">{investiert:,.2f} €</td></tr>
                        <tr><td class="label">Endkapital (Nominal)</td><td class="value">{median_wert:,.2f} €</td></tr>
                        <tr><td class="label">Gewinn (Nominal)</td><td class="value green">+{gewinn:,.2f} €</td></tr>
                        <tr><td class="label" style="color:#333;">Real (Kaufkraft)</td><td class="value" style="font-size:1.2em;">{stats['median']:,.2f} €</td></tr>
                    </table>
                </div>

                <h2>4. Risiko</h2>
                <div class="grid">
                    <div class="card">
                        <h3>Verlust</h3>
                        <table>
                            <tr><td class="label">Verlustrisiko</td><td class="value red">{stats.get('risk_total', 0):.1f} %</td></tr>
                            <tr><td class="label">Max. Drawdown</td><td class="value red">-{np.min(stats.get('drawdown', [0]))*100:.1f} %</td></tr>
                        </table>
                    </div>
                    <div class="card">
                        <h3>Ziel</h3>
                        <table>
                            <tr><td class="label">Ziel erreicht?</td><td class="value green">{stats['success_prob']:.1f} %</td></tr>
                            <tr><td class="label">Best Case</td><td class="value green">{stats['best_case']:,.2f} €</td></tr>
                        </table>
                    </div>
                </div>

                {bilder_html}
                
                <div class="footer">Belegarbeit Wirtschaftslehre/Recht - 12. Klasse - Franke, Elias</div>
            </div>
        </body>
        </html>
        """
        with open(dateiname, 'w', encoding='utf-8') as f:
            f.write(html)