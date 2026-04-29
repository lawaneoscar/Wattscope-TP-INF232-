# analysis.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sqlalchemy.orm import Session
from models import Client, ReleveQuotidien

def get_dataframe_from_db(db: Session):
    releves = db.query(ReleveQuotidien).all()
    if not releves:
        return pd.DataFrame()
    data = {
        "foyer_id": [r.foyer_id for r in releves],
        "date_releve": [r.date_releve for r in releves],
        "index_compteur": [r.index_compteur for r in releves],
        "duree_coupure_minutes": [r.duree_coupure_minutes for r in releves],
        "temperature_exterieure": [r.temperature_exterieure or 0 for r in releves],
        "cout_estime_fcfa": [r.cout_estime_fcfa or 0 for r in releves],
    }
    return pd.DataFrame(data)

def basic_stats(df):
    if len(df) == 0:
        return {"consommation_moyenne_kwh": 0, "consommation_mediane_kwh": 0, "ecart_type_kwh": 0, "total_releves": 0, "coupure_moyenne_minutes": 0}
    return {
        "consommation_moyenne_kwh": round(df["index_compteur"].mean(), 2),
        "consommation_mediane_kwh": round(df["index_compteur"].median(), 2),
        "ecart_type_kwh": round(df["index_compteur"].std(), 2),
        "total_releves": len(df),
        "coupure_moyenne_minutes": round(df["duree_coupure_minutes"].mean(), 2),
    }

def regression_temperature(df):
    if len(df) < 5:
        return {"r2_score": None, "coefficient": None, "message": "Pas assez de données (min 5)"}
    X = df[["temperature_exterieure"]].values
    y = df["index_compteur"].values
    mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
    X, y = X[mask], y[mask]
    if len(X) < 5:
        return {"r2_score": None, "coefficient": None, "message": "Pas assez de données valides"}
    model = LinearRegression()
    model.fit(X, y)
    r2 = model.score(X, y)
    return {"r2_score": round(r2, 4), "coefficient": round(model.coef_[0], 4), "message": f"R²={r2:.2f} : " + ("Corrélation forte" if r2 > 0.6 else "Corrélation modérée" if r2 > 0.3 else "Corrélation faible")}

def cluster_foyers(db: Session):
    clients = db.query(Client).all()
    data = []
    for c in clients:
        releves = [r.index_compteur for r in c.releves]
        if len(releves) >= 5:
            data.append({"foyer_id": c.id, "nom": c.nom_utilisateur, "moyenne_kwh": np.mean(releves), "ecart_type_kwh": np.std(releves)})
    if len(data) < 6:
        return {"message": "Pas assez de clients pour le clustering"}
    df_foyers = pd.DataFrame(data)
    X = df_foyers[["moyenne_kwh", "ecart_type_kwh"]].values
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df_foyers["cluster"] = kmeans.fit_predict(X)
    clusters = {}
    for cluster_id in sorted(df_foyers["cluster"].unique()):
        subset = df_foyers[df_foyers["cluster"] == cluster_id]
        clusters[f"Cluster {cluster_id}"] = {"nombre_foyers": int(len(subset)), "consommation_moyenne": round(float(subset["moyenne_kwh"].mean()), 2), "foyers_exemples": subset["nom"].tolist()[:3]}
    return clusters
