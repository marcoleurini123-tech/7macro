import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configurazione Pagina
st.set_page_config(
    page_title='Macro Regime Dashboard | Quant Framework',
    page_icon='🧭',
    layout='wide',
)

# Definizione dei 7 Portafogli Scenari Macro
MACRO_SCENARIOS = {
    'GOLDILOCKS ECONOMY': {
        'etfs': ['QQQ', 'XLK', 'XLY', 'IEF', 'SMH'],
        'color': '#00CC96',
        'desc': (
            'Crescita solida e inflazione controllata. Massima propensione al'
            ' rischio.'
        ),
        'overweight': 'Tech, Discretionary, Semiconduttori (QQQ, XLK, SMH)',
        'underweight': 'Utilities, Beni di prima necessità, Cash',
    },
    'REFLATION': {
        'etfs': ['XLI', 'XLF', 'IWM', 'EEM', 'DBC'],
        'color': '#636EFA',
        'desc': (
            'Forte accelerazione economica con inflazione in risalita e tassi'
            ' stabili.'
        ),
        'overweight': (
            'Industriali, Finanziari, Small Cap, Commodities (XLI, XLF, IWM,'
            ' DBC)'
        ),
        'underweight': 'Treasury a lunga scadenza (TLT), Tech difensivo',
    },
    'STAGFLATION': {
        'etfs': ['GLD', 'DBC', 'XLE', 'TIP', 'VTV'],
        'color': '#FFA15A',
        'desc': (
            'Crescita stagnante e inflazione persistente. Pressione sui'
            ' multipli azionari.'
        ),
        'overweight': (
            'Oro, Petrolio, Materie Prime, TIPS, Value (GLD, DBC, XLE, TIP)'
        ),
        'underweight': (
            'Growth ad alto multiplo, Obbligazionario governativo nominale'
        ),
    },
    'RECESSION': {
        'etfs': ['TLT', 'SHY', 'XLU', 'XLP', 'GLD'],
        'color': '#EF553B',
        'desc': (
            'Contrazione economica marcata e crollo della domanda aggregata.'
        ),
        'overweight': (
            'Treasury Bonds, Utilities, Consumer Staples, Oro (TLT, XLU, XLP,'
            ' GLD)'
        ),
        'underweight': 'Ciclici, Banche, Small Cap, High Yield',
    },
    'DISINFLATION / SOFT LANDING': {
        'etfs': ['TLT', 'LQD', 'QQQ', 'VTI', 'GLD'],
        'color': '#AB63FA',
        'desc': (
            'Inflazione in calo senza grave recessione. Allentamento monetario.'
        ),
        'overweight': (
            'Corporate Bond IG, Indici generali, Tech di qualità (LQD, QQQ,'
            ' VTI)'
        ),
        'underweight': 'Commodities, Settori energivori',
    },
    'DOLLAR WEAKNESS / GLOBAL REBALANCING': {
        'etfs': ['EEM', 'FXF', 'GLD', 'IXUS', 'DBC'],
        'color': '#19D3F3',
        'desc': (
            'Svalutazione del Dollaro con rotazione dei capitali sui mercati'
            ' internazionali.'
        ),
        'overweight': (
            'Mercati Emergenti, Franco Svizzero, Azionario Ex-USA, Oro (EEM,'
            ' FXF, IXUS, GLD)'
        ),
        'underweight': 'Asset denominati unicamente in USD',
    },
    'DEFLATION': {
        'etfs': ['TLT', 'BIL', 'SHY', 'XLP', 'XLU'],
        'color': '#B6E880',
        'desc': (
            'Crollo generalizzato dei prezzi e liquidità congelata.'
            ' Flight-to-safety estremo.'
        ),
        'overweight': 'Cash, T-Bills, Treasury a lunga scadenza (BIL, SHY, TLT)',
        'underweight': 'Materie prime fisiche, Real Estate, Azionario ciclico',
    },
}

ALL_TICKERS = sorted(
    list(
        set([
            ticker
            for sc in MACRO_SCENARIOS.values()
            for ticker in sc['etfs']
        ])
    )
)


# Funzione con download sicuro e gestione MultiIndex di yfinance
@st.cache_data(ttl=1800)
def fetch_market_data(tickers):
  data = yf.download(
      tickers, period='3y', interval='1d', auto_adjust=True, progress=False
  )
  if isinstance(data.columns, pd.MultiIndex):
    if 'Close' in data.columns.levels[0]:
      df = data['Close']
    else:
      df = data.xs('Close', axis=1, level=0)
  else:
    df = data['Close'] if 'Close' in data.columns else data
  return df.ffill().bfill()


st.title('🧭 Macro Regime Dashboard & Scenario Dominante')
st.caption(
    'Framework Quantitativo di Analisi Intermarket e Regime Asset Allocation'
)

# Caricamento Dati
with st.spinner('Scaricamento dati di mercato in corso...'):
  df_prices = fetch_market_data(ALL_TICKERS)

if df_prices.empty:
  st.error('Impossibile scaricare i dati di mercato. Riprova tra poco.')
  st.stop()

# Calcolo rendimenti a prova di errore (Safe Lookback)
n_rows = len(df_prices)
latest = df_prices.iloc[-1]


def safe_pct(lookback):
  idx = max(0, n_rows - 1 - lookback)
  return (latest / df_prices.iloc[idx] - 1) * 100


ret_1d = safe_pct(1)
ret_1w = safe_pct(5)
ret_1m = safe_pct(21)
ret_3m = safe_pct(63)
ret_1y = safe_pct(252)

df_etfs = pd.DataFrame({
    'Prezzo': latest,
    'Var 1G %': ret_1d,
    'Var 1S %': ret_1w,
    'Var 1M %': ret_1m,
    'Var 3M %': ret_3m,
    'Var 1A %': ret_1y,
})

# Calcolo Metriche dei 7 Panieri
scenario_metrics = []
for name, info in MACRO_SCENARIOS.items():
  etfs = info['etfs']
  sub_df = df_etfs.loc[etfs]

  mean_1d = sub_df['Var 1G %'].mean()
  mean_1w = sub_df['Var 1S %'].mean()
  mean_1m = sub_df['Var 1M %'].mean()
  mean_3m = sub_df['Var 3M %'].mean()
  mean_1y = sub_df['Var 1A %'].mean()

  # Momentum Score Composito
  regime_score = (0.15 * mean_1w) + (0.40 * mean_1m) + (0.45 * mean_3m)

  scenario_metrics.append({
      'Scenario': name,
      'Regime Score': regime_score,
      'Var 1G %': mean_1d,
      'Var 1S %': mean_1w,
      'Var 1M %': mean_1m,
      'Var 3M %': mean_3m,
      'Var 1A %': mean_1y,
      'Color': info['color'],
      'Desc': info['desc'],
      'Overweight': info['overweight'],
      'Underweight': info['underweight'],
  })

df_regimes = (
    pd.DataFrame(scenario_metrics)
    .sort_values(by='Regime Score', ascending=False)
    .reset_index(drop=True)
)
df_regimes['Rank'] = df_regimes.index + 1

dominant = df_regimes.iloc[0]

# --- 1. BANNER REGIME DOMINANTE ---
st.markdown('---')
st.markdown(f"""
<div style="background-color: #1E222D; padding: 22px; border-radius: 12px; border-left: 8px solid {dominant['Color']};">
    <div style="font-size: 13px; color: #8F9CAE; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Regime Macroeconomico Dominante (Quant Momentum)</div>
    <div style="font-size: 30px; font-weight: 800; color: #FFFFFF; margin-top: 5px;">🏆 {dominant['Scenario']}</div>
    <div style="font-size: 15px; color: #D1D4DC; margin-top: 8px;">{dominant['Desc']}</div>
    <div style="display: flex; gap: 25px; margin-top: 15px;">
        <div><b>Score Composito:</b> <span style="color: {dominant['Color']}; font-size: 18px; font-weight: 700;">{dominant['Regime Score']:+.2f}</span></div>
        <div><b>Var. 1 Mese:</b> {dominant['Var 1M %']:+.2f}%</div>
        <div><b>Var. 3 Mesi:</b> {dominant['Var 3M %']:+.2f}%</div>
        <div><b>Var. 1 Anno:</b> {dominant['Var 1A %']:+.2f}%</div>
    </div>
    <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid #2A2E39; font-size: 14px;">
        🟢 <b>Sovrappesare:</b> {dominant['Overweight']}<br>
        🔴 <b>Sottopesare / Hedge:</b> {dominant['Underweight']}
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown('---')

# --- 2. GRAFICO & TABELLA RANKING ---
col_chart, col_table = st.columns([1.1, 0.9])

with col_chart:
  st.subheader('📊 Classifica Forza Relativa dei Regimi')
  fig = go.Figure()
  fig.add_trace(
      go.Bar(
          y=df_regimes['Scenario'][::-1],
          x=df_regimes['Regime Score'][::-1],
          orientation='h',
          marker=dict(
              color=df_regimes['Color'][::-1], line=dict(color='#363A45', width=1)
          ),
          text=[f'{val:+.2f}' for val in df_regimes['Regime Score'][::-1]],
          textposition='auto',
      )
  )
  fig.update_layout(
      height=380,
      margin=dict(l=10, r=20, t=20, b=20),
      xaxis_title='Composite Momentum Score (1S + 1M + 3M)',
      yaxis_title='',
      template='plotly_dark',
  )
  st.plotly_chart(fig, use_container_width=True)

with col_table:
  st.subheader('📋 Tabellone Punteggi')
  display_table = df_regimes[[
      'Rank',
      'Scenario',
      'Regime Score',
      'Var 1S %',
      'Var 1M %',
      'Var 3M %',
  ]].copy()
  st.dataframe(
      display_table.style.format({
          'Regime Score': '{:+.2f}',
          'Var 1S %': '{:+.2f}%',
          'Var 1M %': '{:+.2f}%',
          'Var 3M %': '{:+.2f}%',
      }).background_gradient(
          subset=['Regime Score', 'Var 1M %', 'Var 3M %'], cmap='RdYlGn'
      ),
      height=380,
      use_container_width=True,
  )

# --- 3. DETTAGLIO PER REGIME ---
st.subheader('🔍 Breakdown Componenti per Scenario')
tabs = st.tabs(list(MACRO_SCENARIOS.keys()))

for i, (name, info) in enumerate(MACRO_SCENARIOS.items()):
  with tabs[i]:
    etf_list = info['etfs']
    sub_df = df_etfs.loc[etf_list].copy()

    col_info, col_grid = st.columns([0.35, 0.65])
    with col_info:
      st.markdown(f'### {name}')
      st.write(info['desc'])
      st.markdown(f"**Paniere:** `{'`, `'.join(etf_list)}`")
      st.info(
          f"🟢 **Focus Tattico:** {info['Overweight']}\n\n🔴 **Coperture:**"
          f" {info['Underweight']}"
      )

    with col_grid:
      st.dataframe(
          sub_df.style.format({
              'Prezzo': '{:.2f} $',
              'Var 1G %': '{:+.2f}%',
              'Var 1S %': '{:+.2f}%',
              'Var 1M %': '{:+.2f}%',
              'Var 3M %': '{:+.2f}%',
              'Var 1A %': '{:+.2f}%',
          }).background_gradient(
              subset=['Var 1G %', 'Var 1S %', 'Var 1M %', 'Var 3M %'],
              cmap='RdYlGn',
          ),
          use_container_width=True,
      )
      