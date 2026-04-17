# -*- coding: utf-8 -*-
"""
Script para descargar datos de acciones desde internet (Yahoo Finance via yfinance)
y calcular valor intrínseco por acción con varios métodos:
 - PER (si se aporta PER sectorial)
 - Modelo de Gordon (dividendos)
 - DCF (flujo de caja descontado con proyección)
También clasifica vs. precio de mercado.

Requisitos:
    pip install yfinance pandas numpy
"""

from typing import List, Dict, Any, Optional
from math import isfinite
import numpy as np
import pandas as pd
import yfinance as yf
from dataclasses import dataclass

import sqlite3
from pathlib import Path
# -----------------------------
# Configuración por defecto
# -----------------------------
@dataclass
class ValuationConfig:
    discount_rate: float = 0.10                     # r para DCF y Gordon
    terminal_growth: float = 0.02                   # g perpetuo (debe ser < r)
    dcf_years: int = 5                              # años de proyección
    revenue_multiple: Optional[float] = None        # si quieres usar múltiplo ingresos (no recomendado por defecto)
    neutrality_band: float = 0.10                   # banda ±10% para clasificar "En línea"
    override_sector_pe: Dict[str, float] = None     # PER sectorial por ticker, e.g. {"AAPL": 25}

    # variables sqlite.
    conectorDB = None

    def chequearBDD(self) -> bool:
        db_path = Path.home() / "Library" / "Application Support" / "mi_app" / "data.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        print("Ruta BDD: ", db_path)
        self.conectorDB = sqlite3.connect(db_path)
        cursor = self.conectorDB.cursor()

        try:
            cursor.execute("""
                    CREATE TABLE IF NOT EXISTS valoracion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    price	NUMERIC,
                    shares_outstanding NUMERIC,
                    eps_ttm NUMERIC,
                    revenue_ttm NUMERIC,
                    net_income_ttm NUMERIC,
                    dps_ttm	NUMERIC,
                    fcf_ttm	NUMERIC,
                    net_debt NUMERIC,
                    value_pe NUMERIC,
                    value_gordon NUMERIC,
                    value_dcf NUMERIC,
                    value_avg NUMERIC,
                    classification TEXT,
                    upside_porc NUMERIC,
                    CHECK (upside_porc = ROUND(upside_porc, 2))
                )""")

            self.conectorDB.commit()
            print("✅ Tabla creada correctamente")
            return True
        except sqlite3.Error as e:
            self.conectorDB.rollback()  # 🔥 Muy importante
            print(f"❌ Error, se hace rollback al crear la tabla {e}")
            return False
        finally:
            print("🔥 Todo ha ido correctamente !!!")
            

    def escribirBDD(self, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15):
        if not self.chequearBDD():
            return 
        cursor = self.conectorDB.cursor()

        try:
            cursor.execute("""
                    INSERT INTO valoracion (
                    ticker,
                    price,
                    shares_outstanding,
                    eps_ttm,
                    revenue_ttm,
                    net_income_ttm,
                    dps_ttm,
                    fcf_ttm,
                    net_debt,
                    value_pe,
                    value_gordon,
                    value_dcf,
                    value_avg,
                    classification,
                    upside_porc
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ROUND(?, 2))""",
                (x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15))

            self.conectorDB.commit()
            print("✅ Transacción completada")
        except sqlite3.Error as e:
            self.conectorDB.rollback()  # 🔥 Muy importante
            print(f"❌ Error, se hace rollback: {e}")
        finally:
            print("🔥 Todo ha ido correctamente !!!")

    def safe_div(self, a: float, b: float) -> Optional[float]:
        try:
            if a is None or b in (None, 0):
                return None
            x = a / b
            return x if isfinite(x) else None
        except Exception:
            return None

    def _row_value_sum_last(self, df: pd.DataFrame, row_names: List[str], periods: int = 4) -> Optional[float]:
        """
        Busca una fila por posibles nombres (case-insensitive, exactos o aproximados)
        y suma los últimos 'periods' valores disponibles.
        """
        if df is None or df.empty:
            return None
        # Normalizamos index a lower-case sin espacios extra
        lower_map = {str(idx).strip().lower(): idx for idx in df.index}
        for candidate in row_names:
            key = candidate.strip().lower()
            # búsqueda aproximada: si no está exacto, intenta contains
            match = None
            if key in lower_map:
                match = lower_map[key]
            else:
                for k_norm, k_orig in lower_map.items():
                    if key in k_norm:
                        match = k_orig
                        break
            if match is not None:
                try:
                    vals = df.loc[match].dropna().astype(float)
                    if vals.empty:
                        return None
                    return float(vals.iloc[:periods].sum())  # columnas suelen estar en orden descendente
                except Exception:
                    continue
        return None

    def _last_row_value(self, df: pd.DataFrame, row_names: List[str]) -> Optional[float]:
        """
        Extrae el último valor disponible de una fila entre posibles nombres.
        """
        if df is None or df.empty:
            return None
        lower_map = {str(idx).strip().lower(): idx for idx in df.index}
        for candidate in row_names:
            key = candidate.strip().lower()
            match = None
            if key in lower_map:
                match = lower_map[key]
            else:
                for k_norm, k_orig in lower_map.items():
                    if key in k_norm:
                        match = k_orig
                        break
            if match is not None:
                try:
                    vals = df.loc[match].dropna().astype(float)
                    if vals.empty:
                        return None
                    return float(vals.iloc[0])
                except Exception:
                    continue
        return None

    def get_company_data(self, ticker: str) -> Dict[str, Any]:
        """
        Descarga datos clave de Yahoo Finance vía yfinance.
        """
        tk = yf.Ticker(ticker)

        # Precio actual
        price = None
        try:
            # Fast info es rápido; fallback a history
            if hasattr(tk, "fast_info") and tk.fast_info is not None:
                price = tk.fast_info.get("last_price") or tk.fast_info.get("last_close")
            if price is None:
                hist = tk.history(period="5d", interval="1d")
                if not hist.empty:
                    price = float(hist["Close"].dropna().iloc[-1])
        except Exception:
            pass

        info = {}
        try:
            info = tk.info or {}
        except Exception:
            info = {}

        shares = info.get("sharesOutstanding")
        trailing_eps = info.get("trailingEps")
        trailing_pe = info.get("trailingPE") or info.get("trailingPe")

        # Dividendos TTM
        dps_ttm = None
        try:
            divs = tk.dividends
            if isinstance(divs, pd.Series) and not divs.empty:
                cutoff = divs.index.max() - pd.Timedelta(days=365)
                dps_ttm = float(divs[divs.index > cutoff].sum())
        except Exception:
            pass

        # Estados financieros trimestrales para TTM de ingresos y net income
        q_is = None
        q_cf = None
        q_bs = None
        try:
            q_is = tk.quarterly_financials
        except Exception:
            pass
        try:
            q_cf = tk.quarterly_cashflow
        except Exception:
            pass
        try:
            q_bs = tk.quarterly_balance_sheet
        except Exception:
            pass

        # Ingresos TTM y Beneficio neto TTM
        revenue_ttm = self._row_value_sum_last(q_is, ["Total Revenue", "Revenue"])
        net_income_ttm = self._row_value_sum_last(q_is, ["Net Income", "Net income"])

        # EPS derivado si hace falta
        eps = trailing_eps
        if eps is None and (net_income_ttm is not None and shares):
            eps = self.safe_div(net_income_ttm, shares)

        # FCF TTM: buscar fila directa; si no, OCF - CapEx
        fcf_ttm = self._row_value_sum_last(q_cf, ["Free Cash Flow", "Free cash flow"])
        if fcf_ttm is None:
            ocf_ttm = self._row_value_sum_last(q_cf, ["Operating Cash Flow", "Total Cash From Operating Activities"])
            capex_ttm = self._row_value_sum_last(q_cf, ["Capital Expenditures", "Capital Expenditure"])

            if ocf_ttm is not None and capex_ttm is not None:
                fcf_ttm = float(ocf_ttm) - float(capex_ttm)

        # Deuda neta aproximada = Deuda total - Caja y equivalentes (último trimestre)
        total_debt = self._last_row_value(q_bs, ["Total Debt", "Short Long Term Debt", "Long Term Debt"])
        cash_eq = self._last_row_value(q_bs, ["Cash And Cash Equivalents", "Cash And Short Term Investments", "Cash"])
        net_debt = None
        if total_debt is not None and cash_eq is not None:
            net_debt = float(total_debt) - float(cash_eq)

        return {
            "ticker": ticker,
            "price": price,
            "shares_outstanding": shares,
            "eps_ttm": eps,
            "trailing_pe": trailing_pe,
            "revenue_ttm": revenue_ttm,
            "net_income_ttm": net_income_ttm,
            "dps_ttm": dps_ttm,
            "fcf_ttm": fcf_ttm,
            "net_debt": net_debt
        }

    # -----------------------------
    # Métodos de valoración
    # -----------------------------
    def method_pe(self, eps: Optional[float], sector_pe: Optional[float]) -> Optional[float]:
        if eps is None or sector_pe is None or sector_pe <= 0:
            return None
        val = eps * sector_pe
        return val if val > 0 else None
    
    def method_gordon(self, dps: Optional[float], r: float, g: float) -> Optional[float]:
        if dps is None or dps <= 0:
            return None
        if g >= r:
            return None
        return dps / (r - g)
    
    def method_dcf(self, fcf_ttm: Optional[float],
                   net_debt: Optional[float],
                   shares: Optional[float],
                   r: float,
                   g_terminal: float,
                   n_years: int = 5,
                   growth_first_years: Optional[float] = None) -> Optional[float]:
        """
        Proyecta FCF desde el TTM:
         - Si growth_first_years no se define, usa min(5%, r-1%) como prudencia.
         - Descuenta a r
         - Valor terminal Gordon sobre FCF del último año: FCF_n * (1+g) / (r - g)
         - EV = PV(Flujos) + PV(Terminal)
         - Equity = EV - net_debt
         - Por acción = Equity / shares
        """
        if fcf_ttm is None or fcf_ttm <= 0 or shares is None or shares <= 0:
            return None
        if g_terminal >= r:
            g_terminal = r - 1e-4
    
        if growth_first_years is None:
            growth_first_years = min(0.05, r - 0.01)  # 5% o r-1%
    
        fcf = fcf_ttm
        pvs = 0.0
        for t in range(1, n_years + 1):
            fcf = fcf * (1 + growth_first_years)
            pvs += fcf / ((1 + r) ** t)
    
        terminal = (fcf * (1 + g_terminal)) / (r - g_terminal)
        pv_terminal = terminal / ((1 + r) ** n_years)
    
        ev = pvs + pv_terminal
        if net_debt is None:
            net_debt = 0.0
        equity = ev - net_debt
        per_share = equity / shares
        return per_share if per_share > 0 else None
    
    def classify_vs_price(self, intrinsic: Optional[float], price: Optional[float], band: float = 0.10) -> Optional[str]:
        if intrinsic is None or price is None or price <= 0:
            return None
        low = intrinsic * (1 - band)
        high = intrinsic * (1 + band)
        if price < low:
            return "Infravalorada"
        elif price > high:
            return "Sobrevalorada"
        return "En línea"
    
    def value_tickers(self, tickers: List[str]) -> pd.DataFrame:
        rows = []
        for t in tickers:
            data = self.get_company_data(t)
            eps = data["eps_ttm"]
            shares = data["shares_outstanding"]
    
            # PER (solo si hay PER sectorial para el ticker)
            sector_pe = None
            if self.override_sector_pe and t in self.override_sector_pe:
                sector_pe = self.override_sector_pe[t]
            pe_val = self.method_pe(eps, sector_pe)
    
            # Gordon
            gordon_val = self.method_gordon(
                dps=data["dps_ttm"],
                r=self.discount_rate,
                g=self.terminal_growth
            )
    
            # DCF
            dcf_val = self.method_dcf(
                fcf_ttm=data["fcf_ttm"],
                net_debt=data["net_debt"],
                shares=shares,
                r=self.discount_rate,
                g_terminal=self.terminal_growth,
                n_years=self.dcf_years
            )
    
            # Promedio de los métodos disponibles
            vals = [v for v in [pe_val, gordon_val, dcf_val] if v is not None]
            avg_val = float(np.mean(vals)) if vals else None
    
            classification = self.classify_vs_price(avg_val, data["price"], self.neutrality_band) if avg_val else None
            upside = (avg_val / data["price"] - 1) * 100 if avg_val and data["price"] else None
    
            rows.append({
                "ticker": t,
                "price": data["price"],
                "shares_outstanding": shares,
                "eps_ttm": eps,
                "revenue_ttm": data["revenue_ttm"],
                "net_income_ttm": data["net_income_ttm"],
                "dps_ttm": data["dps_ttm"],
                "fcf_ttm": data["fcf_ttm"],
                "net_debt": data["net_debt"],
                "value_pe": pe_val,
                "value_gordon": gordon_val,
                "value_dcf": dcf_val,
                "value_avg": avg_val,
                "classification": classification,
                "upside_%": upside
            })
    
            self.escribirBDD(
                t,
                data["price"],
                shares,
                eps,
                data["revenue_ttm"],
                data["net_income_ttm"],
                data["dps_ttm"],
                data["fcf_ttm"],
                data["net_debt"],
                pe_val,
                gordon_val,
                dcf_val,
                avg_val,
                classification,
                upside
            )
        return pd.DataFrame(rows)

# -----------------------------
# Ejemplo de ejecución
# -----------------------------
if __name__ == "__main__":
    # Define tus tickers (usa formato de Yahoo Finance, p.ej. "MSFT", "AAPL", "NESN.SW", "^IBEX" no es acción)
    tickers = ["MSFT", "AAPL", "NVDA", "WKL.AS"]

    # Si conoces PER sectorial de alguna, indícalo aquí (ejemplo):
    override_pe = {
        "MSFT": 30.0,
        "AAPL": 28.0
        # "NVDA": 35.0
    }

    cfg = ValuationConfig(
        discount_rate=0.10,
        terminal_growth=0.02,
        dcf_years=5,
        override_sector_pe=override_pe,
        neutrality_band=0.10
    )

    df = cfg.value_tickers(tickers)
    # Muestra resultados
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    print(df)

    # Guarda a CSV opcional
    df.to_csv("valoraciones_intrinseco.csv", index=False)
    print("\nArchivo generado: valoraciones_intrinseco.csv")

    cfg.conectorDB.close()