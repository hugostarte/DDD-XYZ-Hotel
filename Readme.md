## Projet DDD - XYZ Hôtel

#### les supports 
Le fichier uniquious_langage et la context-maps se toruvent dans rendus/  
  

#### Application 
Elle se trouve dans le repertoire app/


#### Installation

1. **Installer les dependances Python** :
```bash
cd app
pip install -r requirements.txt
```

2. **Démarrer la base de données** :
```bash
docker-compose up -d
```

#### Utilisation

**Lancer le CLI interactif** :
```bash
python hotel_cli.py
```

Le menu principal propose :
- Gestion des clients (création, liste)
- Gestion du portefeuille (crédit, solde)
- Gestion des reservations (création, paiement)
- Admin - statistiques (vue d'ensemble)
- Démo complète (pour eviter a avoir a creer les users de tests a la main)

**Lancer l'API FastAPI** :
```bash
python -m uvicorn src.infrastructure.api.main:app --reload
```
L'API est disponible sur `http://localhost:8000`


**Lancer les tests** :
```bash
pytest tests/ -v
```
Les tests unitaires se trouvent dans `tests/test_domain.py` 

**Acceder au swagger** :
- Swagger UI : http://localhost:8000/docs




