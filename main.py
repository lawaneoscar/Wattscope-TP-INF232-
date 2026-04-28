# main.py - Version sans Jinja2 (compatible Python 3.14)
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import Foyer, ReleveQuotidien
from analysis import get_dataframe_from_db, basic_stats, regression_temperature
import datetime

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WattScope")

# Pas besoin de Jinja2Templates ni de dossier templates
# app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- PAGE D'ACCUEIL ----------

@app.get("/", response_class=HTMLResponse)
async def accueil(request: Request, db: Session = Depends(get_db)):
    foyers = db.query(Foyer).all()
    
    # Génération des options pour le select
    options_html = ""
    for f in foyers:
        options_html += f'<option value="{f.id}">{f.nom_utilisateur} ({f.region})</option>'
    
    # Génération de la liste des foyers
    foyers_html = ""
    if foyers:
        for f in foyers:
            foyers_html += f"""
            <div style="background: rgba(255,215,0,0.2); border-left: 4px solid #ffd700; padding: 12px; margin-bottom: 10px; border-radius: 0 8px 8px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{f.nom_utilisateur}</strong>
                        <span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 10px; margin-left: 8px; font-size: 0.85em;">{f.region}</span>
                        <span style="color: #666; margin-left: 8px;">{f.type_logement}</span>
                    </div>
                    <a href="/dashboard/{f.id}" style="text-decoration: none; color: #333; border: 1px solid #333; padding: 4px 12px; border-radius: 4px;">📈 Dashboard</a>
                </div>
            </div>"""
    else:
        foyers_html = '<p style="color: #666;">Aucun foyer enregistré. Lancez data_generator.py</p>'
    
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WattScope - Accueil</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); min-height: 100vh; }}
            .card {{ border-radius: 15px; border: none; }}
            .card-header {{ border-radius: 15px 15px 0 0 !important; background: linear-gradient(90deg, #ffd700, #ffaa00); }}
            .btn-primary {{ background: #ffd700; border: none; color: #000; font-weight: bold; }}
            .btn-primary:hover {{ background: #ffcc00; }}
        </style>
    </head>
    <body>
        <div class="container py-5">
            <div class="text-center mb-5">
                <h1 class="display-4 text-white fw-bold">⚡ WattScope</h1>
                <p class="lead text-light opacity-75">Suivi et Analyse de la Consommation Électrique Domestique</p>
            </div>

            <div class="row g-4">
                <div class="col-lg-7">
                    <div class="card shadow">
                        <div class="card-header">
                            <h2 class="h5 mb-0">📝 Nouveau Relevé Quotidien</h2>
                        </div>
                        <div class="card-body">
                            <form action="/ajouter_releve" method="POST">
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <label for="foyer_id" class="form-label">Foyer *</label>
                                        <select class="form-select" id="foyer_id" name="foyer_id" required>
                                            <option value="">Sélectionnez un foyer...</option>
                                            {options_html}
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label for="date_releve" class="form-label">Date du relevé *</label>
                                        <input type="date" class="form-control" id="date_releve" name="date_releve" required>
                                    </div>
                                    <div class="col-md-4">
                                        <label for="index_compteur" class="form-label">Index compteur (kWh) *</label>
                                        <input type="number" step="0.01" min="0" class="form-control" id="index_compteur" name="index_compteur" placeholder="Ex: 15.5" required>
                                    </div>
                                    <div class="col-md-4">
                                        <label for="duree_coupure" class="form-label">Durée coupure (min)</label>
                                        <input type="number" min="0" class="form-control" id="duree_coupure" name="duree_coupure" value="0">
                                    </div>
                                    <div class="col-md-4">
                                        <label for="temperature" class="form-label">Température (°C)</label>
                                        <input type="number" step="0.1" class="form-control" id="temperature" name="temperature" placeholder="Ex: 28.5" value="0">
                                    </div>
                                    <div class="col-md-6">
                                        <label for="cout_estime" class="form-label">Coût estimé (FCFA)</label>
                                        <input type="number" min="0" class="form-control" id="cout_estime" name="cout_estime" value="0">
                                    </div>
                                    <div class="col-12">
                                        <button type="submit" class="btn btn-primary w-100 py-2">📊 Enregistrer le relevé</button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="card shadow mt-4">
                        <div class="card-header">
                            <h2 class="h5 mb-0">🏠 Foyers enregistrés</h2>
                        </div>
                        <div class="card-body">
                            {foyers_html}
                        </div>
                    </div>
                </div>

                <div class="col-lg-5">
                    <div class="card shadow h-100">
                        <div class="card-header">
                            <h2 class="h5 mb-0">💡 Pourquoi WattScope ?</h2>
                        </div>
                        <div class="card-body">
                            <p>Dans de nombreux pays africains, les foyers subissent des coupures d'électricité fréquentes et peinent à estimer leur consommation avant la facture.</p>
                            <ul>
                                <li><strong>Économies</strong> : identifiez les appareils énergivores</li>
                                <li><strong>Anticipation</strong> : voyez les tendances avant la facture</li>
                                <li><strong>Comparaison</strong> : situez-vous par rapport aux foyers similaires</li>
                            </ul>
                            <hr>
                            <p class="small text-muted">
                                Application développée pour le TP <strong>INF 232 EC2</strong> : Analyse de données.<br>
                                Intègre : régression linéaire, stats descriptives.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ---------- AJOUTER UN RELEVÉ ----------

@app.post("/ajouter_releve")
async def ajouter_releve(
    request: Request,
    foyer_id: int = Form(...),
    date_releve: str = Form(...),
    index_compteur: float = Form(...),
    duree_coupure: int = Form(0),
    temperature: float = Form(0.0),
    cout_estime: float = Form(0.0),
    db: Session = Depends(get_db)
):
    foyer = db.query(Foyer).filter(Foyer.id == foyer_id).first()
    if not foyer:
        raise HTTPException(404, "Foyer introuvable")

    releve = ReleveQuotidien(
        foyer_id=foyer_id,
        date_releve=datetime.date.fromisoformat(date_releve),
        index_compteur=index_compteur,
        duree_coupure_minutes=duree_coupure,
        temperature_exterieure=temperature,
        cout_estime_fcfa=cout_estime
    )
    db.add(releve)
    db.commit()
    return RedirectResponse(url=f"/dashboard/{foyer_id}", status_code=303)


# ---------- DASHBOARD ----------

@app.get("/dashboard/{foyer_id}", response_class=HTMLResponse)
async def dashboard(request: Request, foyer_id: int, db: Session = Depends(get_db)):
    foyer = db.query(Foyer).filter(Foyer.id == foyer_id).first()
    if not foyer:
        raise HTTPException(404, "Foyer introuvable")

    df = get_dataframe_from_db(db)
    stats = basic_stats(df)
    reg_temp = regression_temperature(df)

    releves_foyer = list(foyer.releves)
    releves_count = len(releves_foyer)
    
    if releves_count > 0:
        conso_moy = round(sum(r.index_compteur for r in releves_foyer) / releves_count, 2)
    else:
        conso_moy = 0

    # Génération du tableau des relevés
    releves_html = ""
    if releves_foyer:
        for r in releves_foyer[:20]:
            releves_html += f"""
            <tr>
                <td>{r.date_releve}</td>
                <td><strong>{r.index_compteur}</strong></td>
                <td>{r.duree_coupure_minutes}</td>
                <td>{r.temperature_exterieure or 'N/A'}</td>
                <td>{r.cout_estime_fcfa or 'N/A'}</td>
            </tr>"""
    else:
        releves_html = '<tr><td colspan="5" style="text-align: center; color: #666;">Aucun relevé</td></tr>'

    # Régression
    if reg_temp.get("r2_score"):
        reg_html = f"""
        <p><strong>R² :</strong> {reg_temp['r2_score']}</p>
        <p><strong>Coefficient :</strong> {reg_temp['coefficient']}</p>
        <p>{reg_temp['message']}</p>"""
    else:
        reg_html = f"<p>{reg_temp.get('message', 'Données insuffisantes')}</p>"

    # Données pour Chart.js
    dates_js = "[" + ", ".join([f"'{r.date_releve}'" for r in releves_foyer[:30]]) + "]"
    consos_js = "[" + ", ".join([str(r.index_compteur) for r in releves_foyer[:30]]) + "]"

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WattScope - Dashboard {foyer.nom_utilisateur}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ background: #f4f6f9; }}
            .card {{ border-radius: 15px; border: none; margin-bottom: 1.5rem; }}
            .card-header {{ border-radius: 15px 15px 0 0 !important; font-weight: bold; }}
            .stat-box {{ background: white; border-radius: 12px; padding: 1.25rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            .stat-value {{ font-size: 2rem; font-weight: bold; color: #2c5364; }}
            .stat-label {{ font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        </style>
    </head>
    <body>
        <div class="container py-4">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1 class="mb-0">⚡ Dashboard</h1>
                    <p class="text-muted mb-0">Foyer : <strong>{foyer.nom_utilisateur}</strong> | {foyer.region} | {foyer.type_logement}</p>
                </div>
                <a href="/" class="btn btn-outline-secondary">← Retour</a>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-md-3 col-6">
                    <div class="stat-box">
                        <div class="stat-value">{conso_moy}</div>
                        <div class="stat-label">kWh/jour (moy.)</div>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="stat-box">
                        <div class="stat-value">{stats['total_releves']}</div>
                        <div class="stat-label">Relevés totaux</div>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="stat-box">
                        <div class="stat-value">{stats['consommation_moyenne_kwh']}</div>
                        <div class="stat-label">kWh global</div>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="stat-box">
                        <div class="stat-value">{releves_count}</div>
                        <div class="stat-label">Relevés foyer</div>
                    </div>
                </div>
            </div>

            <div class="row g-4">
                <div class="col-lg-8">
                    <div class="card shadow-sm">
                        <div class="card-header bg-primary text-white">📈 Évolution de la consommation (kWh)</div>
                        <div class="card-body">
                            <canvas id="consommationChart" height="200"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="card shadow-sm">
                        <div class="card-header bg-info text-white">🔬 Régression : Température vs Conso</div>
                        <div class="card-body">
                            {reg_html}
                        </div>
                    </div>
                </div>
            </div>

            <div class="card shadow-sm mt-4">
                <div class="card-header bg-dark text-white">📋 Derniers relevés du foyer</div>
                <div class="card-body table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Index compteur (kWh)</th>
                                <th>Durée coupure (min)</th>
                                <th>Température (°C)</th>
                                <th>Coût estimé (FCFA)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {releves_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            var dates = {dates_js};
            var consos = {consos_js};
            
            if (dates.length > 0) {{
                var ctx = document.getElementById('consommationChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: dates,
                        datasets: [{{
                            label: 'Consommation (kWh)',
                            data: consos,
                            borderColor: '#ffd700',
                            backgroundColor: 'rgba(255,215,0,0.1)',
                            borderWidth: 2,
                            tension: 0.3,
                            fill: true,
                            pointBackgroundColor: '#2c5364'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{ legend: {{ display: false }} }},
                        scales: {{
                            x: {{ ticks: {{ maxTicksLimit: 10 }} }},
                            y: {{ beginAtZero: false }}
                        }}
                    }}
                }});
            }}
        </script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
