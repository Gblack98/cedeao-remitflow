"""Tableau de bord CEDEAO-RemitFlow.

Lit les tables d'agrégat construites par dbt dans BigQuery et répond aux
trois questions métier du projet : volume par corridor, impact du risque
de change, coût par canal.

Lancement : streamlit run dashboard/app.py
"""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJET = os.environ.get("REMITFLOW_PROJECT", "crucial-bonsai-418120")
DATASET = os.environ.get("REMITFLOW_DATASET", "dbt_dev_gabar")
KEYFILE = os.path.expanduser(
    os.environ.get("REMITFLOW_KEYFILE", "~/.gcp/remitflow-sa.json")
)

# Palette catégorielle validée (contrôle CVD et contraste). L'ordre des
# emplacements est le mécanisme de sécurité daltonisme, pas un choix
# esthétique : ne pas réordonner sans revalider.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#898781"
GRILLE = "#e1e0d9"
AXE = "#c3c2b7"

# La couleur suit la devise, jamais son rang : un filtre qui retire une
# série ne doit pas repeindre les autres.
COULEUR_DEVISE = {"NGN": "#2a78d6", "GHS": "#eb6834", "XOF": "#1baf7a"}
COULEUR_CORRIDOR = {"Avec risque de change": "#eb6834", "Sans risque de change": "#2a78d6"}
COULEUR_CANAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

st.set_page_config(page_title="CEDEAO-RemitFlow", page_icon="📊", layout="wide")


@st.cache_resource
def client():
    if not os.path.exists(KEYFILE):
        st.error(
            f"Clé de service account introuvable : {KEYFILE}\n\n"
            "Définis REMITFLOW_KEYFILE ou relance ./run.sh."
        )
        st.stop()
    creds = service_account.Credentials.from_service_account_file(KEYFILE)
    return bigquery.Client(project=PROJET, credentials=creds)


@st.cache_data(ttl=600)
def lire(table):
    return client().query(f"select * from `{PROJET}.{DATASET}.{table}`").to_dataframe()


def mise_en_forme(fig, hauteur=380):
    """Chrome commun : grille discrète, encre sobre, fond unifié."""
    fig.update_layout(
        height=hauteur,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif",
                  color=INK, size=13),
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=SURFACE, font_size=13),
    )
    fig.update_xaxes(gridcolor=GRILLE, linecolor=AXE, zerolinecolor=AXE,
                     tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(gridcolor=GRILLE, linecolor=AXE, zerolinecolor=AXE,
                     tickfont=dict(color=INK_MUTED))
    return fig


st.title("CEDEAO-RemitFlow")
st.caption(
    "Transferts transfrontaliers en zone CEDEAO et impact du risque de change. "
    f"Source : `{PROJET}.{DATASET}`"
)

kpi = lire("agg_kpi_global").iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Transferts", f"{int(kpi.transferts_total):,}".replace(",", " "))
c2.metric("Taux de succès", f"{kpi.taux_succes_pct:.1f} %")
c3.metric("Frais moyen", f"{kpi.frais_moyen_pct:.2f} %")
c4.metric("Volume exposé au change", f"{kpi.part_volume_a_risque_pct:.1f} %")

st.divider()

# --- Question 2 en premier : c'est le cœur du sujet -------------------
st.subheader("Volatilité des devises de réception")
st.caption(
    "Indice base 100 à la première cotation. Les taux bruts — Naira autour "
    "de 1 500, Cedi autour de 13 — sont incomparables sur un même axe ; "
    "indexés, leurs variations relatives se lisent directement."
)

taux = lire("agg_taux_journalier").sort_values("date_id")

fig = go.Figure()
for devise in ["NGN", "GHS", "XOF"]:
    d = taux[taux.devise_cible == devise]
    if d.empty:
        continue
    fig.add_trace(go.Scatter(
        x=d.date_id, y=d.indice_base_100, name=devise, mode="lines",
        line=dict(color=COULEUR_DEVISE[devise], width=2),
        hovertemplate=f"<b>{devise}</b> %{{x|%d/%m/%Y}}<br>indice %{{y:.1f}}<extra></extra>",
    ))
    # Étiquette directe en fin de courbe : l'identité ne repose jamais
    # sur la seule couleur.
    fig.add_annotation(
        x=d.date_id.iloc[-1], y=d.indice_base_100.iloc[-1], text=f" {devise}",
        showarrow=False, xanchor="left", font=dict(color=INK, size=12),
    )
fig.add_hline(y=100, line=dict(color=AXE, width=1, dash="dot"))
fig.update_layout(hovermode="x unified")
fig.update_yaxes(title_text="Indice (100 = première cotation)")
st.plotly_chart(mise_en_forme(fig, 420), use_container_width=True)

impact = lire("agg_impact_change").sort_values("ecart_max_pct", ascending=False)
st.markdown("**Montant reçu pour 100 000 XOF nets envoyés, selon le jour du transfert**")
st.dataframe(
    impact[["devise_cible", "nom_devise", "type_corridor", "transferts",
            "recu_pire_jour", "recu_moyen", "recu_meilleur_jour", "ecart_max_pct"]]
    .rename(columns={
        "devise_cible": "Devise", "nom_devise": "Nom", "type_corridor": "Corridor",
        "transferts": "Transferts", "recu_pire_jour": "Pire jour",
        "recu_moyen": "Moyen", "recu_meilleur_jour": "Meilleur jour",
        "ecart_max_pct": "Écart max (%)"}),
    hide_index=True, use_container_width=True,
)

st.divider()

# --- Question 1 -------------------------------------------------------
st.subheader("Volume par corridor")

corr = lire("agg_corridors")
top = corr.groupby(["pays_cible", "type_corridor"], as_index=False)["volume_xof"].sum()
top = top.sort_values("volume_xof", ascending=True)

fig = go.Figure()
for type_c in ["Sans risque de change", "Avec risque de change"]:
    d = top[top.type_corridor == type_c]
    if d.empty:
        continue
    fig.add_trace(go.Bar(
        y=d.pays_cible, x=d.volume_xof, name=type_c, orientation="h",
        marker=dict(color=COULEUR_CORRIDOR[type_c],
                    line=dict(color=SURFACE, width=2)),
        text=[f"{v/1e6:.1f} M" for v in d.volume_xof],
        textposition="outside", textfont=dict(color=INK, size=12),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} XOF<extra></extra>",
    ))
fig.update_xaxes(title_text="Volume envoyé (XOF)")
st.plotly_chart(mise_en_forme(fig, 400), use_container_width=True)

st.divider()

# --- Question 3 -------------------------------------------------------
st.subheader("Coût de commission par canal")

canaux = lire("agg_couts_canal")
pivot = canaux.groupby(["libelle_canal", "type_corridor"], as_index=False)["frais_moyen_pct"].mean()

fig = go.Figure()
for i, type_c in enumerate(["Sans risque de change", "Avec risque de change"]):
    d = pivot[pivot.type_corridor == type_c]
    if d.empty:
        continue
    fig.add_trace(go.Bar(
        x=d.libelle_canal, y=d.frais_moyen_pct, name=type_c,
        marker=dict(color=COULEUR_CORRIDOR[type_c],
                    line=dict(color=SURFACE, width=2)),
        text=[f"{v:.2f} %" for v in d.frais_moyen_pct],
        textposition="outside", textfont=dict(color=INK, size=12),
        hovertemplate="<b>%{x}</b><br>%{y:.2f} %<extra></extra>",
    ))
fig.update_yaxes(title_text="Frais moyen (%)")
st.plotly_chart(mise_en_forme(fig, 380), use_container_width=True)

with st.expander("Détail par canal et corridor"):
    st.dataframe(
        canaux[["libelle_canal", "type_corridor", "zone_cible", "transferts",
                "frais_moyen_pct", "frais_moyen_xof", "marge_moyenne_xof"]],
        hide_index=True, use_container_width=True,
    )
