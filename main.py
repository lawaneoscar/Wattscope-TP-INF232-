# main.py - WattScope (Version finale corrigée)
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import Client, ReleveQuotidien, Appareil
from analysis import get_dataframe_from_db, basic_stats, regression_temperature
import datetime
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WattScope")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- PAGE D'ACCUEIL ----------
@app.get("/", response_class=HTMLResponse)
async def accueil(request: Request, db: Session = Depends(get_db), success: str = ""):
    clients = db.query(Foyer).all()
    
    msg_success = ""
    if success:
        msg_success = f'<div class="alert alert-success alert-dismissible fade show" role="alert">{success}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>'

    options_releve = '<option value="">-- Choisissez un client --</option>'
    for f in clients:
        options_releve += f'<option value="{f.id}">{f.nom_utilisateur} - {f.region}</option>'
    
    clients_html = ""
    if clients:
        for f in clients:
            nb_releves = len(f.releves)
            clients_html += f"""
            <div style="background: rgba(255,215,0,0.2); border-left: 4px solid #ffd700; padding: 12px; margin-bottom: 10px; border-radius: 0 8px 8px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{f.nom_utilisateur}</strong>
                        <span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 10px; margin-left: 8px; font-size: 0.85em;">{f.region}</span>
                        <span style="color: #666; margin-left: 8px;">{f.type_logement}</span>
                        <span class="badge bg-primary ms-2">{nb_releves} relevés</span>
                    </div>
                    <a href="/dashboard/{f.id}" style="text-decoration: none; color: #333; border: 1px solid #333; padding: 4px 12px; border-radius: 4px;">📈 Dashboard</a>
                </div>
            </div>"""
    else:
        clients_html = '<p style="color: #666;">Aucun client enregistré. Ajoutez-en un ci-dessous.</p>'
    
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
            .card-header {{ border-radius: 15px 15px 0 0 !important; font-weight: bold; }}
            .bg-gold {{ background: linear-gradient(90deg, #ffd700, #ffaa00); }}
            .btn-primary {{ background: #ffd700; border: none; color: #000; font-weight: bold; }}
            .btn-success {{ background: #28a745; border: none; font-weight: bold; color: white; }}
            .text-muted-small {{ font-size: 0.8em; color: #888; }}
        </style>
    </head>
    <body>
        <div class="container py-5">
            {msg_success}
            <div class="text-center mb-5">
                <h1 class="display-4 text-white fw-bold">⚡ WattScope</h1>
                <p class="lead text-light opacity-75">Suivi et Analyse de la Consommation Électrique Domestique</p>
            </div>

            <div class="row g-4">
                <div class="col-lg-7">
                    <div class="card shadow mb-4">
                        <div class="card-header bg-success text-white">
                            <h2 class="h5 mb-0">➕ Enregistrer un Client / Foyer</h2>
                        </div>
                        <div class="card-body">
                            <form action="/ajouter_client" method="POST">
                                <div class="row g-3">
                                    <div class="col-md-5">
                                        <label class="form-label">Nom complet ou Identifiant du foyer</label>
                                        <input type="text" class="form-control" name="nom_utilisateur" placeholder="Ex: Jean-Yaoundé" required>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Ville / Région</label>
                                        <input type="text" class="form-control" name="region" placeholder="Ex: Yaoundé" required>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">Type logement</label>
                                        <select class="form-select" name="type_logement">
                                            <option>Studio</option><option>Appartement</option><option>Villa</option>
                                        </select>
                                    </div>
                                    <div class="col-md-2 d-flex align-items-end">
                                        <button type="submit" class="btn btn-success w-100">➕ Ajouter</button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="card shadow">
                        <div class="card-header bg-gold">
                            <h2 class="h5 mb-0">📝 Nouveau Relevé Quotidien</h2>
                        </div>
                        <div class="card-body">
                            <form action="/ajouter_releve" method="POST">
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <label class="form-label">Client / Foyer *</label>
                                        <select class="form-select" name="foyer_id" required>{options_releve}</select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Date du relevé *</label>
                                        <input type="date" class="form-control" name="date_releve" required>
                                    </div>
                                    <div class="col-md-4">
                                        <label class="form-label">Index compteur (kWh) *</label>
                                        <input type="number" step="0.01" min="0" class="form-control" name="index_compteur" placeholder="Ex: 15.5" required>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">Unité</label>
                                        <select class="form-select" name="unite_coupure">
                                            <option value="minutes">Minutes</option><option value="heures">Heures</option>
                                        </select>
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label">Coupure</label>
                                        <input type="number" min="0" step="0.1" class="form-control" name="duree_coupure" value="0">
                                    </div>
                                    <div class="col-md-4">
                                        <label class="form-label">Température (°C) <span class="text-muted-small">(facultatif)</span></label>
                                        <input type="number" step="0.1" class="form-control" name="temperature" placeholder="Ex: 28.5">
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Coût estimé (FCFA) <span class="text-muted-small">(facultatif)</span></label>
                                        <input type="number" min="0" class="form-control" name="cout_estime" value="0">
                                    </div>
                                    <div class="col-12">
                                        <button type="submit" class="btn btn-primary w-100 py-2">📊 Enregistrer le relevé</button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="card shadow mt-4">
                        <div class="card-header bg-dark text-white"><h2 class="h5 mb-0">👥 Clients / Foyers enregistrés</h2></div>
                        <div class="card-body">{clients_html}</div>
                    </div>
                </div>

                <div class="col-lg-5">
                    <div class="card shadow h-100">
                        <div class="card-header bg-info text-white"><h2 class="h5 mb-0">💡 Pourquoi WattScope ?</h2></div>
                        <div class="card-body">
                            <p>Suivez votre consommation électrique, identifiez les appareils énergivores et anticipez vos factures.</p>
                            <ul>
                                <li><strong>📊 Analyse</strong> : régression linéaire, statistiques</li>
                                <li><strong>🔌 Appareils</strong> : détection des équipements coûteux</li>
                                <li><strong>📥 Export</strong> : téléchargez vos données en Excel</li>
                            </ul>
                            <hr><p class="small text-muted">TP <strong>INF 232 EC2</strong> : Analyse de données.</p>
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

# ---------- AJOUTER UN CLIENT ----------
@app.post("/ajouter_client")
async def ajouter_client(request: Request, nom_utilisateur: str = Form(...), region: str = Form(...), type_logement: str = Form("Appartement"), db: Session = Depends(get_db)):
    client = Foyer(nom_utilisateur=nom_utilisateur, region=region, type_logement=type_logement, nombre_habitants=1)
    db.add(client)
    db.commit()
    return RedirectResponse(url=f"/?success=✅ Client '{nom_utilisateur}' enregistré avec succès !", status_code=303)

# ---------- AJOUTER UN RELEVÉ ----------
@app.post("/ajouter_releve")
async def ajouter_releve(request: Request, foyer_id: int = Form(...), date_releve: str = Form(...), index_compteur: float = Form(...), duree_coupure: float = Form(0), unite_coupure: str = Form("minutes"), temperature: str = Form(""), cout_estime: float = Form(0.0), db: Session = Depends(get_db)):
    client = db.query(Foyer).filter(Foyer.id == foyer_id).first()
    if not client:
        raise HTTPException(404, "Client introuvable")
    duree_minutes = int(duree_coupure * 60) if unite_coupure == "heures" else int(duree_coupure)
    temp_value = float(temperature) if temperature and temperature.strip() else None
    releve = ReleveQuotidien(foyer_id=foyer_id, date_releve=datetime.date.fromisoformat(date_releve), index_compteur=index_compteur, duree_coupure_minutes=duree_minutes, temperature_exterieure=temp_value, cout_estime_fcfa=cout_estime)
    db.add(releve)
    db.commit()
    return RedirectResponse(url=f"/dashboard/{foyer_id}?success=✅ Relevé du {date_releve} enregistré !", status_code=303)

# ---------- DASHBOARD ----------
@app.get("/dashboard/{foyer_id}", response_class=HTMLResponse)
async def dashboard(request: Request, foyer_id: int, db: Session = Depends(get_db), success: str = ""):
    client = db.query(Foyer).filter(Foyer.id == foyer_id).first()
    if not client:
        raise HTTPException(404, "Client introuvable")

    msg_success = f'<div class="alert alert-success alert-dismissible fade show" role="alert">{success}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>' if success else ""

    df = get_dataframe_from_db(db)
    stats = basic_stats(df)
    reg_temp = regression_temperature(df)
    releves_client = list(client.releves)
    releves_count = len(releves_client)
    conso_moy = round(sum(r.index_compteur for r in releves_client) / releves_count, 2) if releves_count > 0 else 0

    # Appareils
    appareils = db.query(Appareil).filter(Appareil.foyer_id == foyer_id).all()
    appareils_html = ""
    appareils_js_labels = "[]"
    appareils_js_data = "[]"
    top_energivore = ""
    
    if appareils:
        total_kwh = sum(a.puissance_watts * a.heures_utilisation_jour * a.nombre_appareils / 1000 for a in appareils)
        appareils_tries = sorted(appareils, key=lambda a: a.puissance_watts * a.heures_utilisation_jour * a.nombre_appareils, reverse=True)
        labels_js = []
        data_js = []
        for a in appareils_tries:
            conso_kwh = a.puissance_watts * a.heures_utilisation_jour * a.nombre_appareils / 1000
            pct = round(conso_kwh / total_kwh * 100, 1) if total_kwh > 0 else 0
            badge = "🔴" if pct > 30 else ("🟠" if pct > 15 else "🟢")
            appareils_html += f"<tr><td>{badge} {a.nom_appareil}</td><td>{a.nombre_appareils}</td><td>{a.puissance_watts}W</td><td>{a.heures_utilisation_jour}h/j</td><td><strong>{round(conso_kwh,2)} kWh</strong></td><td><span class='badge {'bg-danger' if pct>30 else ('bg-warning' if pct>15 else 'bg-success')}'>{pct}%</span></td></tr>"
            labels_js.append(a.nom_appareil)
            data_js.append(round(conso_kwh, 2))
        top = appareils_tries[0]
        top_energivore = f"<div class='alert alert-danger'><strong>⚠️ Appareil le plus énergivore :</strong> {top.nom_appareil}<br><small>{round(top.puissance_watts*top.heures_utilisation_jour*top.nombre_appareils/1000,2)} kWh/jour</small></div>"
        appareils_js_labels = "[" + ", ".join([f"'{l}'" for l in labels_js]) + "]"
        appareils_js_data = "[" + ", ".join([str(d) for d in data_js]) + "]"
    else:
        appareils_html = '<tr><td colspan="6" style="text-align:center;color:#666;">Aucun appareil</td></tr>'

    # Relevés
    releves_html = ""
    if releves_client:
        for r in releves_client[:20]:
            temp_aff = f"{r.temperature_exterieure}°C" if r.temperature_exterieure else "N/A"
            cout_aff = f"{r.cout_estime_fcfa} FCFA" if r.cout_estime_fcfa else "N/A"
            coupure_aff = f"{r.duree_coupure_minutes//60}h{r.duree_coupure_minutes%60:02d}" if r.duree_coupure_minutes >= 60 else f"{r.duree_coupure_minutes} min"
            releves_html += f"<tr><td>{r.date_releve}</td><td><strong>{r.index_compteur}</strong></td><td>{coupure_aff}</td><td>{temp_aff}</td><td>{cout_aff}</td></tr>"
    else:
        releves_html = '<tr><td colspan="5" style="text-align:center;color:#666;">Aucun relevé</td></tr>'

    if reg_temp.get("r2_score"):
        reg_html = f"<p><strong>R² :</strong> {reg_temp['r2_score']}</p><p><strong>Coefficient :</strong> {reg_temp['coefficient']}</p><p>{reg_temp['message']}</p>"
    else:
        reg_html = f"<p>{reg_temp.get('message', 'Données insuffisantes')}</p>"

    dates_js = "[" + ", ".join([f"'{r.date_releve}'" for r in releves_client[:30]]) + "]"
    consos_js = "[" + ", ".join([str(r.index_compteur) for r in releves_client[:30]]) + "]"

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - {client.nom_utilisateur} | WattScope</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body{{background:#f4f6f9}} .card{{border-radius:15px;border:none;margin-bottom:1.5rem}} .card-header{{border-radius:15px 15px 0 0!important;font-weight:bold}}
            .stat-box{{background:white;border-radius:12px;padding:1.25rem;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.05)}}
            .stat-value{{font-size:2rem;font-weight:bold;color:#2c5364}} .stat-label{{font-size:0.85rem;color:#666;text-transform:uppercase;letter-spacing:1px}}
            .btn-excel{{background:#217346;color:white;border:none;font-weight:bold}} .btn-excel:hover{{background:#185a32;color:white}}
        </style>
    </head>
    <body>
        <div class="container py-4">
            {msg_success}
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div><h1 class="mb-0">⚡ Dashboard</h1><p class="text-muted mb-0">Client : <strong>{client.nom_utilisateur}</strong> | {client.region} | {client.type_logement}</p></div>
                <div>
                    <a href="/export_excel/{foyer_id}" class="btn btn-excel me-2">📥 Excel</a>
                    <a href="/" class="btn btn-outline-secondary">← Retour</a>
                </div>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-md-3 col-6"><div class="stat-box"><div class="stat-value">{conso_moy}</div><div class="stat-label">kWh/jour</div></div></div>
                <div class="col-md-3 col-6"><div class="stat-box"><div class="stat-value">{stats['total_releves']}</div><div class="stat-label">Total relevés</div></div></div>
                <div class="col-md-3 col-6"><div class="stat-box"><div class="stat-value">{stats['consommation_moyenne_kwh']}</div><div class="stat-label">kWh global</div></div></div>
                <div class="col-md-3 col-6"><div class="stat-box"><div class="stat-value">{releves_count}</div><div class="stat-label">Relevés client</div></div></div>
            </div>

            <div class="row g-4 mb-4">
                <div class="col-lg-7"><div class="card shadow-sm"><div class="card-header bg-danger text-white">🔌 Consommation par Appareil (kWh/jour)</div><div class="card-body"><canvas id="appareilsChart" height="200"></canvas></div></div></div>
                <div class="col-lg-5">
                    <div class="card shadow-sm"><div class="card-header bg-warning text-dark">⚠️ Appareils Énergivores</div>
                        <div class="card-body">
                            {top_energivore}
                            <div class="table-responsive"><table class="table table-sm"><thead><tr><th>Appareil</th><th>Qté</th><th>W</th><th>h/j</th><th>kWh</th><th>%</th></tr></thead><tbody>{appareils_html}</tbody></table></div>
                            <hr><p class="small text-muted">🔴>30% | 🟠15-30% | 🟢<15%</p>
                            <form action="/ajouter_appareil" method="POST" class="mt-2">
                                <input type="hidden" name="foyer_id" value="{foyer_id}">
                                <div class="row g-2">
                                    <div class="col-5"><input type="text" class="form-control form-control-sm" name="nom_appareil" placeholder="Appareil" required></div>
                                    <div class="col-3"><input type="number" class="form-control form-control-sm" name="puissance_watts" placeholder="Watts" required></div>
                                    <div class="col-2"><input type="number" step="0.1" class="form-control form-control-sm" name="heures" placeholder="h/j"></div>
                                    <div class="col-2"><button type="submit" class="btn btn-success btn-sm w-100">+</button></div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row g-4 mb-4">
                <div class="col-lg-8"><div class="card shadow-sm"><div class="card-header bg-primary text-white">📈 Évolution de la consommation</div><div class="card-body"><canvas id="consommationChart" height="200"></canvas></div></div></div>
                <div class="col-lg-4"><div class="card shadow-sm"><div class="card-header bg-info text-white">🔬 Régression</div><div class="card-body">{reg_html}</div></div></div>
            </div>

            <div class="card shadow-sm"><div class="card-header bg-dark text-white">📋 Derniers relevés</div><div class="card-body table-responsive"><table class="table table-hover mb-0"><thead><tr><th>Date</th><th>kWh</th><th>Coupure</th><th>Temp.</th><th>Coût</th></tr></thead><tbody>{releves_html}</tbody></table></div></div>
        </div>

        <script>
            var dates={dates_js},consos={consos_js};
            if(dates.length>0){{new Chart(document.getElementById('consommationChart').getContext('2d'),{{type:'line',data:{{labels:dates,datasets:[{{label:'kWh',data:consos,borderColor:'#ffd700',backgroundColor:'rgba(255,215,0,0.1)',borderWidth:2,tension:0.3,fill:!0}}]}},options:{{responsive:!0,plugins:{{legend:{{display:!1}}}},scales:{{x:{{ticks:{{maxTicksLimit:10}}}},y:{{beginAtZero:!1}}}}}}}});}}
            var appLabels={appareils_js_labels},appData={appareils_js_data};
            if(appLabels.length>0){{new Chart(document.getElementById('appareilsChart').getContext('2d'),{{type:'pie',data:{{labels:appLabels,datasets:[{{data:appData,backgroundColor:['#ff6384','#ff9f40','#ffcd56','#4bc0c0','#36a2eb','#9966ff','#c9cbcf','#ffd700']}}]}},options:{{responsive:!0,plugins:{{legend:{{position:'bottom'}}}}}}}});}}
        </script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# ---------- EXPORT EXCEL ----------
@app.get("/export_excel/{foyer_id}")
async def export_excel(foyer_id: int, db: Session = Depends(get_db)):
    client = db.query(Foyer).filter(Foyer.id == foyer_id).first()
    if not client:
        raise HTTPException(404, "Client introuvable")
    
    releves = list(client.releves)
    appareils = db.query(Appareil).filter(Appareil.foyer_id == foyer_id).all()
    
    wb = openpyxl.Workbook()
    
    ws1 = wb.active
    ws1.title = "Relevés"
    
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="2c5364", end_color="2c5364", fill_type="solid")
    center_align = Alignment(horizontal="center")
    
    headers1 = ["Date", "Index compteur (kWh)", "Durée coupure (min)", "Température (°C)", "Coût estimé (FCFA)"]
    for col, header in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
    
    for row_idx, r in enumerate(releves, 2):
        ws1.cell(row=row_idx, column=1, value=str(r.date_releve))
        ws1.cell(row=row_idx, column=2, value=r.index_compteur)
        ws1.cell(row=row_idx, column=3, value=r.duree_coupure_minutes)
        ws1.cell(row=row_idx, column=4, value=r.temperature_exterieure or 0)
        ws1.cell(row=row_idx, column=5, value=r.cout_estime_fcfa or 0)
    
    for col in range(1, 6):
        ws1.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
    
    ws2 = wb.create_sheet("Appareils")
    headers2 = ["Appareil", "Quantité", "Puissance (W)", "Heures/jour", "Consommation (kWh/jour)"]
    for col, header in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
    
    for row_idx, a in enumerate(appareils, 2):
        conso = a.puissance_watts * a.heures_utilisation_jour * a.nombre_appareils / 1000
        ws2.cell(row=row_idx, column=1, value=a.nom_appareil)
        ws2.cell(row=row_idx, column=2, value=a.nombre_appareils)
        ws2.cell(row=row_idx, column=3, value=a.puissance_watts)
        ws2.cell(row=row_idx, column=4, value=a.heures_utilisation_jour)
        ws2.cell(row=row_idx, column=5, value=round(conso, 2))
    
    for col in range(1, 6):
        ws2.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"WattScope_{client.nom_utilisateur}_{datetime.date.today()}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ---------- AJOUTER UN APPAREIL ----------
@app.post("/ajouter_appareil")
async def ajouter_appareil(request: Request, foyer_id: int = Form(...), nom_appareil: str = Form(...), puissance_watts: int = Form(...), heures: float = Form(1.0), db: Session = Depends(get_db)):
    app = Appareil(foyer_id=foyer_id, nom_appareil=nom_appareil, puissance_watts=puissance_watts, heures_utilisation_jour=heures, nombre_appareils=1)
    db.add(app)
    db.commit()
    return RedirectResponse(url=f"/dashboard/{foyer_id}?success=✅ Appareil '{nom_appareil}' ajouté !", status_code=303)
