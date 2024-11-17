
# Medite 2024

## Aperçu
Ce projet est une refonte du moteur MEDITE pour la réimplémentation du projet variance [https://variance.unil.ch/](https://variance.unil.ch/). Le moteur MEDITE a été initialement développé par Julien Bourdaillet (julien.bourdaillet@lip6.fr) et Jean-Gabriel Ganascia (jean-gabriel.ganascia@lip6.fr). Cette refonte a impliqué la mise à niveau du code pour supporter Python 3.12 et l'ajout de la prise en charge des entrées et sorties TEI XML.

## Installation

### Prérequis
- Installer [Poetry](https://python-poetry.org/) : Un outil pour la gestion des dépendances et le packaging en Python.

### Étapes d'Installation
1. Clonez le dépôt sur votre machine locale :
    ```bash
    git clone https://github.com/louisChiffre/variance
    cd variance
    ```

2. Installez les dépendances du projet à l'aide de Poetry :
    ```bash
    poetry install
    ```

3. Générez l'extension de l'arbre des suffixes requise pour `medite` :
    ```bash
    poetry run python setup.py build_ext --inplace
    ```

## Utilisation

### Entrer dans l'interface de commande Poetry
Avant d'exécuter les scripts, entrez dans le shell Poetry pour activer l'environnement virtuel :
```bash
poetry shell
```

### Générer des Différences à partir de Fichiers TEI XML
Utilisez le script `diff.py` pour générer des différences entre des fichiers TEI XML :
```bash
python scripts/diff.py tests/data/samples/exemple_variance/la_vieille_fille_v1.xml tests/data/samples/exemple_variance/la_vieille_fille_v2.xml --lg_pivot 7 --ratio 15 --seuil 50 --case-sensitive --diacri-sensitive --output-xml test.xml
```

## Options Supplémentaires
- `--lg_pivot` : Définir la longueur pivot pour la comparaison.
- `--ratio` : Définir le seuil de ratio pour les différences.
- `--seuil` : Définir le seuil de signification minimale des différences.
- `--case-sensitive` : Effectuer une comparaison sensible à la casse.
- `--diacri-sensitive` : Tenir compte des diacritiques lors de la comparaison.

### Transformer fichier plat txt en fichier TEI XML
Utile pour effectuer des tests avec des anciens fichiers Medite
```bash
python scripts/txt2tei.py tests/data/LaVendetta/1vndtt.txt
```

