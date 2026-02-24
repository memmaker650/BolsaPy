
import sys
import os
import math
import datetime as dt
from datetime import datetime, timedelta

try:
    import pandas as pd
except ImportError:
    print("[ERROR] Falta pandas. Instala con: pip install pandas openpyxl yfinance")
    sys.exit(1)

try:
    import yfinance as yf
except ImportError:
    print("[ERROR] Falta yfinance. Instala con: pip install yfinance")
    sys.exit(1)

# -----------------------------
# Configuración
# -----------------------------
TICKERS = {
    "Repsol": "REP.MC",
    "Wolters Kluwer": "WKL.AS",
    "Apple": "AAPL",
    "OHLA": "OHLA.MC",
    "Atos": "ATO.PA",
    "Alten": "ATE.PA",
    "Sopra Steria": "SOP.PA",
    "Indra": "IDR.MC",
    "Inditex (Zara)": "ITX.MC",
    "YPF": "YPF",
}

SALIDA_XLSX = "bolsa_resumen_auto.xlsx"
HOJA = "Resumen"

# Columnas solicitadas
COLUMNAS = [
    "Nombre", "Ticker", "Mercado", "Valor actual", "Variación respecto ayer",
    "Variación respecto hace una semana", "Variación respecto hace 3 meses",
    "Mínimo último mes", "Mínimo último año", "Máximo último mes", "Máximo último año",
    "Máximo de siempre", "Última noticia relevante"
]

# -----------------------------
# Utilidades de fechas
# -----------------------------

def last_close_before(df, target_date):
    """Devuelve el último cierre disponible en o antes de target_date (fecha calendario)."""
    if df.empty:
        return None
    # Asegurar índice tipo datetime y ordenado
    s = df.sort_index()
    s = s.loc[s.index <= pd.to_datetime(target_date)]
    if s.empty:
        return None
    return float(s["Close"].iloc[-1].squeeze())


def pct(a, b):
    """Variación porcentual (a vs b). Devuelve string con % y 2 decimales."""
    if a is None or b is None or b == 0 or (isinstance(b, float) and (math.isnan(b) or b == 0)):
        return ""
    return f"{(a/b - 1)*100:.2f}%"


# -----------------------------
# Descarga y cálculo por ticker
# -----------------------------
import pandas as pd

resumen_rows = []

for nombre, ticker in TICKERS.items():
    print(f"Procesando {nombre} ({ticker})...")
    try:
        # Serie 400 días para cálculos 1w, 1m, 3m, 1y
        hist = yf.download(ticker, period="400d", interval="1d", auto_adjust=False, progress=False)
        # Serie completa para máximo histórico
        hist_all = yf.download(ticker, period="max", interval="1d", auto_adjust=False, progress=False)
    except Exception as e:
        print(f"  [WARN] No se pudo descargar {ticker}: {e}")
        hist = pd.DataFrame()
        hist_all = pd.DataFrame()

    # Mercado (sufijo simplificado por exchange)
    mercado = ""
    if ticker.endswith(".MC"):
        mercado = "BME"
    elif ticker.endswith(".PA"):
        mercado = "EPA"
    elif ticker.endswith(".AS"):
        mercado = "AMS"
    elif ticker.upper() == "AAPL":
        mercado = "NASDAQ"
    elif ticker.upper() == "YPF":
        mercado = "NYSE"

    # Valor actual y variación diaria
    valor_actual = ""
    var_dia = ""
    if not hist.empty:
        last_close = float(hist["Close"].iloc[-1].squeeze())
        valor_actual = last_close
        if len(hist) >= 2:
            prev_close = float(hist["Close"].iloc[-2].squeeze())
            var_dia = pct(last_close, prev_close)

    # Fechas objetivo
    hoy = pd.to_datetime(dt.date.today())
    hace_7 = hoy - pd.Timedelta(days=7)
    hace_90 = hoy - pd.Timedelta(days=90)
    hace_30 = hoy - pd.Timedelta(days=30)
    hace_365 = hoy - pd.Timedelta(days=365)

    # Variaciones 1 semana y 3 meses
    var_1w = ""
    var_3m = ""
    if not hist.empty:
        c_hoy = last_close_before(hist, hoy)
        c_1w = last_close_before(hist, hace_7)
        c_3m = last_close_before(hist, hace_90)
        var_1w = pct(c_hoy, c_1w)
        var_3m = pct(c_hoy, c_3m)

    # Mín/Máx 30 días y 365 días
    min_30 = ""; max_30 = ""; min_365 = ""; max_365 = ""; max_all = ""
    if not hist.empty:
        rec_30 = hist.loc[hist.index >= hace_30]
        if not rec_30.empty:
            min_30 = float(rec_30["Low"].min().squeeze())
            max_30 = float(rec_30["High"].max().squeeze())
        rec_365 = hist.loc[hist.index >= hace_365]
        if not rec_365.empty:
            min_365 = float(rec_365["Low"].min().squeeze())
            max_365 = float(rec_365["High"].max().squeeze())
    if not hist_all.empty:
        max_all = float(hist_all["High"].max().squeeze())

    # Última noticia
    noticia = ""
    try:
        t = yf.Ticker(ticker)
        news = getattr(t, 'news', None)
        if news:
            first = news[0]
            tit = first.get('title', '')
            pub = first.get('publisher', '')
            ts = first.get('providerPublishTime') or first.get('publishedAt')
            if ts:
                fecha = dt.datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%d') if isinstance(ts, (int, float, str)) else ''
            else:
                fecha = ''
            noticia = f"{tit} ({pub}, {fecha})"
    except Exception:
        pass

    # Formateo de números con símbolo monetario según mercado (aprox)
    def fmt(v):
        if v == "" or v is None:
            return ""
        if mercado in ("BME", "EPA", "AMS"):
            return f"€{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        else:
            return f"${v:,.2f}"

    fila = {
        "Nombre": nombre,
        "Ticker": ticker,
        "Mercado": mercado,
        "Valor actual": fmt(valor_actual) if valor_actual != "" else "",
        "Variación respecto ayer": var_dia,
        "Variación respecto hace una semana": var_1w,
        "Variación respecto hace 3 meses": var_3m,
        "Mínimo último mes": fmt(min_30),
        "Mínimo último año": fmt(min_365),
        "Máximo último mes": fmt(max_30),
        "Máximo último año": fmt(max_365),
        "Máximo de siempre": fmt(max_all),
        "Última noticia relevante": noticia,
    }
    resumen_rows.append(fila)

# Construcción del DataFrame final
resumen_df = pd.DataFrame(resumen_rows, columns=COLUMNAS)

# Guardar Excel (una sola hoja "Resumen")
with pd.ExcelWriter(SALIDA_XLSX, engine="openpyxl") as writer:
    resumen_df.to_excel(writer, sheet_name=HOJA, index=False)

print(f"[OK] Archivo actualizado: {SALIDA_XLSX}")
