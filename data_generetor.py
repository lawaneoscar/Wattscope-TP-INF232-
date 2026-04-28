import random
from datetime import date, timedelta
from database import SessionLocal, engine, Base
from models import Foyer, ReleveQuotidien, Appareil

Base.metadata.create_all(bind=engine)
db = SessionLocal()

regions = ["Yaounde", "Douala", "Bafoussam", "Garoua", "Maroua"]
logements = ["Studio", "Appartement", "Villa"]
foyers = []

for i in range(1, 11):
    f = Foyer(
        nom_utilisateur=f"Foyer_{i}",
        region=random.choice(regions),
        type_logement=random.choice(logements),
        nombre_habitants=random.randint(1, 8)
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    foyers.append(f)
    print(f"Foyer cree : {f.nom_utilisateur} (ID {f.id})")

start_date = date(2025, 1, 1)
for foyer in foyers:
    conso_base = random.uniform(5, 25)
    for j in range(100):
        jour = start_date + timedelta(days=j)
        temperature = round(random.uniform(22, 36), 1)
        coupure = random.choices([0, 30, 60, 120, 240], weights=[60, 20, 10, 7, 3])[0]
        index_compteur = round(conso_base + (temperature - 25) * 0.3 + random.uniform(-2, 2), 2)
        index_compteur = max(index_compteur, 1)
        cout = round(index_compteur * random.choice([75, 85, 95]), 0)

        r = ReleveQuotidien(
            foyer_id=foyer.id,
            date_releve=jour,
            index_compteur=index_compteur,
            duree_coupure_minutes=coupure,
            temperature_exterieure=temperature,
            cout_estime_fcfa=cout
        )
        db.add(r)
    db.commit()
    print(f"100 releves generes pour {foyer.nom_utilisateur}")

appareils_types = [
    ("Refrigerateur", 200, 24),
    ("Climatiseur", 1500, 8),
    ("Televiseur", 100, 5),
    ("Congelateur", 350, 24),
    ("Machine a laver", 500, 1),
    ("Fer a repasser", 1200, 0.5),
    ("Ventilateur", 75, 10),
]

for foyer in foyers:
    for _ in range(random.randint(2, 5)):
        nom, puissance, heures = random.choice(appareils_types)
        a = Appareil(
            foyer_id=foyer.id,
            nom_appareil=nom,
            puissance_watts=puissance,
            heures_utilisation_jour=heures,
            nombre_appareils=random.randint(1, 3)
        )
        db.add(a)
    db.commit()
    print(f"Appareils ajoutes pour {foyer.nom_utilisateur}")

print("\nGeneration terminee ! 10 foyers, 1000 releves, ~35 appareils.")
db.close()
