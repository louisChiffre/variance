
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
python scripts/diff.py tests/data/LaVieilleFille/1vf.xml tests/data/LaVieilleFille/2vf.xml --lg_pivot 7 --ratio 15 --case-sensitive --diacri-sensitive --output-xml test.xml
```
Les séparateurs utilisés par Medite peuvent être spécifié avec l'argument sep.
```bash
python scripts/diff.py tests/data/LaVieilleFille/1vf.xml tests/data/LaVieilleFille/2vf.xml --lg_pivot 7 --ratio 15 --case-sensitive --diacri-sensitive --output-xml test.xml --sep $' !\r,\n:\t;-?"\'`()….»«'
```
Des sorties XHTML peuvent être générées en utilisant l'option `--xhtml-output-dir` :
```bash
python scripts/diff.py tests/data/LaVieilleFille/1vf.xml tests/data/LaVieilleFille/2vf.xml --lg_pivot 7 --ratio 15 --case-sensitive --diacri-sensitive --output-xml test.xml --xhtml-output-dir xhtml
```
#### Options disponibles
- `source_filenames` (arguments) : Les chemins des fichiers TEI XML à comparer. Ils doivent exister dans votre système de fichiers.
- `--lg_pivot` : Définit la longueur minimale des blocs communs (voir la section “lg_pivot” ci-dessous). Par défaut : `10`.
- `--ratio` : Définit le rapport de taille, en pourcentage, nécessaire pour différencier une opération de suppression/insertion d’une substitution (voir la section “ratio” ci-dessous). Par défaut : `10`.
- `--case-sensitive` : Effectue une comparaison sensible à la casse. Par défaut : `False`.
- `--diacri-sensitive` : Tient compte des diacritiques lors de la comparaison. Par défaut : `False`.
- `--output-xml` : Chemin de sortie pour le fichier XML des différences. Par défaut : `diff_output.xml`.

#### `lg_pivot`
Le paramètre `lg_pivot` définit la taille minimale des blocs communs.  
Entre « Alice mange du chocolat » et « Pierre descend du bateau », il y a 2 blocs communs potentiels : « Alice » et «  du ». « Alice » a une longueur de 5 caractères, «  du » de 3.  
Si `lg_pivot` est à 10, ni « Alice » ni «  du » ne seront considérés comme des blocs communs. Si `lg_pivot` est à 5, « Alice » sera l’unique bloc commun, «  du » étant trop court. Si `lg_pivot` est à 1, « Alice » et «  du » seront des blocs communs.

#### `ratio`
Le paramètre `ratio` contrôle la propension de Medite à considérer les différences entre deux blocs communs comme des remplacements ou comme des suppressions/insertions.  
Par exemple, dans les phrases « Alice mange du chocolat » et « Alice descend du chocolat », les deux blocs communs sont « Alice » et «  du chocolat ».  
On peut considérer soit que « mange » a été substitué par « descend », soit que « mange » a été supprimé et « descend » inséré. Medite prend cette décision sur la base du rapport de taille entre les deux chaînes de caractères. Si leurs tailles sont suffisamment proches, Medite considérera qu’il s’agit d’un remplacement ; sinon, d’une suppression et d’une insertion.

Le paramètre `ratio` contrôle cette tolérance. Il peut prendre une valeur entre 1 et 100. Un ratio de 50, par exemple, signifie que si le rapport de taille (mesuré par la taille de la plus petite chaîne divisée par la plus grande, exprimé en %) est inférieur à 50 %, le changement sera considéré comme une suppression + insertion plutôt qu’un remplacement.  
Dans le cas de « mange » (5) et « descend » (7), le rapport de taille est 5/7 ≈ 71,4 % ; avec un ratio de 50, le changement est classé comme une substitution.


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
