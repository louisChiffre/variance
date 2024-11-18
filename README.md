
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
python scripts/diff.py tests/data/LaVieilleFille/1vf.xml tests/data/LaVieilleFille/2vf.xml --lg_pivot 7 --ratio 15 --seuil 50 --case-sensitive --diacri-sensitive --output-xml test.xml
```

#### Options Disponibles
- `source_filenames` (arguments) : Les chemins des fichiers TEI XML à comparer. Ils doivent exister dans votre système de fichiers.
- `--lg_pivot` : Définit la longueur pivot pour la comparaison. Par défaut : `10`.
- `--ratio` : Définit le seuil de ratio pour les différences. Par défaut : `10`.
- `--seuil` : Définit le seuil de signification minimale des différences. Par défaut : `30`.
- `--case-sensitive` : Effectue une comparaison sensible à la casse. Par défaut : `False`.
- `--diacri-sensitive` : Tient compte des diacritiques lors de la comparaison. Par défaut : `False`.
- `--output-xml` : Chemin de sortie pour le fichier XML des différences. Par défaut : `diff_output.xml`.

### Transformer un fichier plat txt en fichier TEI XML
Le script `txt2tei.py` permet de transformer un fichier texte brut en un fichier TEI XML.

```bash
python scripts/txt2tei.py tests/data/LaVendetta/1vndtt.txt --pub_date_str "1842" --titre "La Vendetta" --version_nb 1
```

#### Options Disponibles
- `source_filename` (argument) : Le chemin du fichier texte brut à convertir. Il doit exister dans votre système de fichiers.
- `--pub_date_str` : La chaîne représentant la date de publication du texte. Par défaut : "inconnue".
- `--titre` : Le titre du texte. Par défaut : "inconnu".
- `--version_nb` : Le numéro de version du texte. Par défaut : `1`.

Ces options vous permettent de préciser des métadonnées à inclure dans le fichier TEI XML généré afin de faciliter son identification et son utilisation future.
