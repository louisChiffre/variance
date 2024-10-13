import pandas as pd
import pathlib
import shutil
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import io
import textwrap as tw
import itertools as it
from collections import namedtuple, defaultdict
from os.path import dirname, basename, splitext, join
from .ansi import Fore, Style


# from constantesDonnees
FICHIER_INFO = "Informations.xml"
## Balises ##
B_ROOT = "root"
B_AUTEUR = "auteur"
B_NOM = "nom"
B_PRENOM = "prenom"
B_NAISSANCE = "naissance"
B_DECES = "deces"
B_OEUVRE = "oeuvre"
B_TITRE = "titre"
B_EDITION = "edition"
B_PUBLICATION = "publication"
B_INFORMATIONS = "informations"
B_VERS_SOURCE = "vsource"
B_ETAT_SOURCE = "fsource"
B_VERS_CIBLE = "vcible"
B_ETAT_CIBLE = "fcible"
B_PARAM_1 = "lg_pivot"
B_PARAM_2 = "ratio"
B_PARAM_3 = "seuil"
B_PARAM_4 = "car_mot"
B_PARAM_5 = "caseSensitive"
B_PARAM_6 = "sepSensitive"
B_PARAM_7 = "diacriSensitive"
B_TRANSFORMATIONS = "transformations"
B_LGSOURCE = "lgsource"
B_INSERTIONS = "insertions"
B_SUPPRESSIONS = "suppressions"
B_DEPLACEMENTS = "deplacements"
B_REMPLACEMENTS = "remplacements"
B_BLOCSCOMMUNS = "blocscommuns"
B_BLOCSDEPLACES = "blocsdeplaces"
B_NONDEF = "blocsNonDefinis"
B_LG = "lg"
B_INS = "ins"
B_SUP = "sup"
B_DEP = "dep"
B_REMP = "remp"
B_BC = "bc"
B_ND = "nd"
B_MOT = "mot"
B_DEB = "d"
B_FIN = "f"
B_DEP = "bd"
B1_D = "b1d"
B1_F = "b1f"
B2_D = "b2d"
B2_F = "b2f"
# B_REMP = 'remp'
B_MOT_AVANT = "motavant"
B_MOT_APRES = "motapres"
B_TEXT_SOURCE = "textsource"
B_TEXT_CIBLE = "textcible"
B_TEXT = "tcommun"
B_TEXT_INSER = "tinsertion"
B_TEXT_SUPP = "tsuppression"
B_TEXT_DEPL = "tdeplacement"
B_TEXT_REMP = "tremplacement"
B_COMMENTAIRE = "commentaire"

B_ARBRE = "arbre"
B_VERSION = "version"
B_ETAT = "etat"
B_ID = "id"

ASSETS_DIRECTORY = join(dirname(dirname(os.path.dirname(__file__))), "assets")
assert os.path.exists(ASSETS_DIRECTORY)

def prettify(elem):
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def read_txt(filename, encoding="utf-8"):
    with io.open(filename, "r", encoding=encoding) as o:
        txt = o.read()
    return txt


def make_informations(appli, source_filename, target_filename, author, title):
    assert dirname(source_filename) == dirname(target_filename)
    result = appli.result
    parameters = appli.parameters
    root = ET.Element(B_ROOT)

    # author
    auteur = ET.SubElement(root, B_AUTEUR)

    author_information = [k.strip() for k in author.split(",")]
    assert (
        len(author_information) == 4
    ), "Author string should be comma separated and have 4 elements"
    first_name, last_name, birth_year, death_year = author_information

    ET.SubElement(auteur, B_PRENOM).text = first_name
    ET.SubElement(auteur, B_NOM).text = last_name
    ET.SubElement(auteur, B_NAISSANCE).text = birth_year
    ET.SubElement(auteur, B_DECES).text = death_year

    # work
    oeuvre = ET.SubElement(root, B_OEUVRE)

    ET.SubElement(oeuvre, B_TITRE).text = title
    ET.SubElement(oeuvre, B_EDITION).text = "edition"
    ET.SubElement(oeuvre, B_PUBLICATION).text = "year"

    def extract_root(filename):
        return splitext(basename(filename))[0]

    # arbre
    arbre = ET.SubElement(root, B_ARBRE)
    ET.SubElement(arbre, B_VERSION).set(B_ID, extract_root(source_filename))
    ET.SubElement(arbre, B_VERSION).set(B_ID, extract_root(target_filename))

    info = ET.SubElement(root, B_INFORMATIONS)
    info.set(B_ETAT_SOURCE, basename(source_filename))
    info.set(B_ETAT_CIBLE, basename(target_filename))

    info.set(B_VERS_SOURCE, extract_root(source_filename))
    info.set(B_VERS_CIBLE, extract_root(target_filename))

    info.set(B_PARAM_1, "%s" % parameters.lg_pivot)
    info.set(B_PARAM_2, "%s" % parameters.ratio)
    info.set(B_PARAM_3, "%s" % parameters.seuil)
    info.set(B_PARAM_4, "%s" % int(parameters.car_mot))
    info.set(B_PARAM_5, "%s" % int(parameters.case_sensitive))
    info.set(B_PARAM_6, "%s" % int(parameters.sep_sensitive))
    info.set(B_PARAM_7, "%s" % int(parameters.diacri_sensitive))
    transfo = ET.SubElement(info, B_TRANSFORMATIONS)
    lg = ET.SubElement(transfo, B_LGSOURCE)
    lg.set(B_LG, str(result.getLgSource()))

    insertions = ET.SubElement(transfo, B_INSERTIONS)
    for deb, fin in result.getListeInsertions():
        node = ET.SubElement(insertions, B_INS)
        node.set(B_DEB, str(deb))
        node.set(B_FIN, str(fin))

    suppressions = ET.SubElement(transfo, B_SUPPRESSIONS)
    for deb, fin in result.getListeSuppressions():
        node = ET.SubElement(suppressions, B_SUP)
        node.set(B_DEB, str(deb))
        node.set(B_FIN, str(fin))

    deplacements = ET.SubElement(transfo, B_DEPLACEMENTS)
    for deb, fin in result.getListeDeplacements():
        node = ET.SubElement(deplacements, B_DEP)
        node.set(B_DEB, str(deb))
        node.set(B_FIN, str(fin))
    # print prettify(root)
    remplacements = ET.SubElement(transfo, B_REMPLACEMENTS)
    for deb, fin in result.getListeRemplacements():
        node = ET.SubElement(remplacements, B_REMP)
        node.set(B_DEB, str(deb))
        node.set(B_FIN, str(fin))

    blocsCommuns = ET.SubElement(transfo, B_BLOCSCOMMUNS)
    for deb, fin in result.getBlocsCommuns():
        node = ET.SubElement(blocsCommuns, B_BC)
        node.set(B_DEB, str(deb))
        node.set(B_FIN, str(fin))

    nonDefined = ET.SubElement(transfo, B_NONDEF)
    for deb, fin in result.getNonDef():
        node = ET.SubElement(nonDefined, B_ND)
        node.set(B_DEB, str(deb))
        node.set(B_FIN, str(fin))

    blocsDeplaces = ET.SubElement(transfo, B_BLOCSDEPLACES)
    for (b1deb, b1fin), (b2deb, b2fin) in result.getPairesBlocsDeplaces():
        node = ET.SubElement(blocsDeplaces, B_DEP)
        node.set(B1_F, str(b1fin))
        node.set(B2_F, str(b2fin))
        node.set(B1_D, str(b1deb))
        node.set(B2_D, str(b2deb))
    return prettify(root)


def make_html_output(appli, html_filename):
    table_html_str = appli.bbl._BiBlocList__listeToHtmlTable()
    with io.open(html_filename, "w", encoding="utf8") as o:
        html = "<html><body><table>{table_html_str}</table></body></html>".format(
            **locals()
        )
        o.write(html)


def make_xml_output(
    appli, source_filename, target_filename, info_filename, author=None, title=None
):
    info = make_informations(
        appli=appli,
        source_filename=source_filename,
        target_filename=target_filename,
        author=author,
        title=title,
    )
    with io.open(info_filename, "w", encoding="utf8") as o:
        o.write(info)


# we link to nltka data that were installed manually using
# python -m nltk.downloader -d Users/laurentmauron/nltk_data all
# and added to the github repo
os.environ["NLTK_DATA"] = os.path.join(
    ASSETS_DIRECTORY, "nltk_data"
)
from nltk.tokenize.punkt import PunktSentenceTokenizer
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.data import load
from nltk.tokenize import sent_tokenize, word_tokenize


def gen_token(txt):
    language = "french"
    tokenizer = load("tokenizers/punkt/{language}.pickle".format(language=language))
    return list(tokenizer.span_tokenize(txt))


def with_newline(txt, gen_token):
    spans = list(gen_token(txt))
    newline = "\n"

    def gen():
        i = 0
        for txt_ in txt.split(newline):
            for start, end in gen_token(txt_):
                breakpoint()

    spans_ = list(gen())
    breakpoint()


def make_sentence_lookup(txt):
    # we cut the text in sentences and create a lookup table that tells you to which sentence coresponds a character
    Lookup = namedtuple("Lookup", "sentences character2sentence")
    c2s = {}
    sentences = []
    x1 = [txt[k:v] for k, v in gen_token(txt)]
    x2 = [txt[k:v] for k, v in gen_token(txt.replace("\n", "."))]
    tokens = gen_token(txt.replace("\n", "."))
    for k, start_end in enumerate(tokens):
        start, end = start_end
        sentence = txt[start:end]
        # print(str(k).center(80,'*'))
        # print(sentence)
        sentences.append(sentence)
        for i in range(start + 1, end + 1):
            c2s[i] = k
        assert sentences[k] == sentence
    # let's verify we have everything mapped
    # for every character, verify there is a sentence
    missing_indices = [i for i, _ in enumerate(txt) if i not in c2s]
    # print "following characters have no associated sentence", missing_indices
    # breakpoint()
    # k=[i for i,_ in enumerate(txt) if i not in c2s]
    for i, k in enumerate(txt):
        # if we have a character that has no sentence, we assign it to the previous good characater
        # if i in missing_indices:
        #    c2s[i] = c2s[i_]
        # else:
        #    i_ = i
        # assert i in c2s, 'cannot find sentence for character {i}'.format(**locals())
        if i in c2s:
            si = c2s[i]
            sentences[si]
    return Lookup(sentences=sentences, character2sentence=c2s)


def make_javascript_output(appli, base_dir):
    txt = appli.bbl.texte
    sentence_lookup = make_sentence_lookup(appli.bbl.texte)

    Pair = namedtuple("Pair", "id a b")

    def gen_pairs():
        f = functools.partial(block2fragment, appli, sentence_lookup)
        for i, z in enumerate(appli.bbl.liste):
            a, b = z
            fa = f(a)
            fb = f(b)
            yield Pair(i, fa, fb)

    def annotate(frag, id):
        return '<span class={frag.type} id="frag_{id}" onclick="scroll_this(this)">{frag.txt}</span>'.format(
            **locals()
        )

    def make_text(field):
        def gen():
            for z in gen_pairs():
                yield annotate(
                    getattr(z, field),
                    z.id,
                )

        def add_new_line(txt):
            return txt.replace("\n", "<br>")

        def make_block(frag):
            return {"type": "fragment", "data": {"text": frag}}

        blocks = [make_block(k) for k in ("".join(gen())).split("\n")]
        return json.dumps(blocks, ensure_ascii=False)

    table = make_table(gen_pairs())
    csv_filename = join(base_dir, "csv_output.csv")
    print(("saving to {csv_filename}".format(**locals())))
    table.to_csv(csv_filename, encoding="utf-8")

    tables = make_tables(gen_pairs())

    txt1 = make_text("a")
    txt2 = make_text("b")

    def make_table_html(df):
        assert "id" in list(df.columns)

        def gen():
            yield "<table >"
            yield "<thead>"
            for col in df.columns:
                if not col == "id":
                    yield "<th>" + col + "</th>"
            yield "</thead>"
            yield "<tbody>"
            for _, row in df.iterrows():
                yield '  <tr id="frag_{row.id}" onclick="scroll_this(this)">'.format(
                    **locals()
                )
                for k, v in list(row.items()):
                    if not k == "id":
                        yield "    <td>" + v + "</td>"
                yield "  </tr>"

            yield "</tbody>"
            yield "</table>"

        z = "\n".join(gen())
        return json.dumps(z, ensure_ascii=False)

    replacements_txt = make_table_html(
        tables["Replacement"][["a", "b", "id"]].sort_values("a")
    )
    deletions_txt = make_table_html(tables["Deletion"][["a", "id"]])
    insertions_txt = make_table_html(tables["Insertion"][["b", "id"]])
    tpl = """
var blocks_1 = {txt1};
var blocks_2 = {txt2};
var replacements_txt = {replacements_txt};
var deletions_txt = {deletions_txt};
var insertions_txt = {insertions_txt};
"""
    txt = tpl.format(**locals())
    # this is the javascript
    javascript_filename = join(base_dir, "data.js")
    print((("writing data to {javascript_filename}").format(**locals())))
    with io.open(javascript_filename, "w", encoding="utf8") as o:
        o.write(str(txt))

    assets_directory = ASSETS_DIRECTORY
    print((("source assets directory is {assets_directory}").format(**locals())))

    # copying base template
    template_filename = join(assets_directory, "template.html")
    html_filename = join(base_dir, "diff_table_improved.html")
    print(("copying {template_filename} to {html_filename}".format(**locals())))
    shutil.copyfile(template_filename, html_filename)

    # copying the javascript assets
    dynamic_assets_directory = join(assets_directory, "dynamic_assets")
    target_assets_directory = join(base_dir, "assets")
    assert os.path.exists(dynamic_assets_directory)
    print(
        (
            "copying {dynamic_assets_directory} to {target_assets_directory}".format(
                **locals()
            )
        )
    )
    if os.path.exists(target_assets_directory):
        shutil.rmtree(target_assets_directory)
    shutil.copytree(dynamic_assets_directory, target_assets_directory)


def make_table(pair_generator):
    pairs = list(pair_generator)

    def gen():
        for pair in pairs:
            typ = pair.a.type if pair.a.type else pair.b.type
            yield {
                "type": typ,
                "context_a": "".join(pair.a.context),
                "a": pair.a.txt,
                "b": pair.b.txt,
                "context_b": "".join(pair.b.context),
                "b_type": pair.b.type,
                "id": pair.id,
            }

    df = pd.DataFrame(gen())[["id", "type", "context_a", "a", "b", "context_b"]]
    return df


def make_tables(pairs_generator):
    # let's construct the lookup tables
    D = defaultdict(list)
    [D[(k.a.type, k.b.type)].append(k) for k in pairs_generator]

    def deletion_func(z):
        return {}

    def replacement_func(pair):
        return {
            "context_a": "".join(pair.a.context),
            "a": pair.a.txt,
            "b": pair.b.txt,
            "context_b": "".join(pair.b.context),
            "id": pair.id,
        }

    def deletion_func(pair):
        return {
            "context_a": "".join(pair.a.context),
            "a": pair.a.txt,
            "id": pair.id,
        }

    def insertion_func(pair):
        return {
            "context_b": "".join(pair.a.context),
            "b": pair.b.txt,
            "id": pair.id,
        }

    Group = namedtuple("Group", "key name row_func")
    groups = {
        Group(key=("R", "R"), name="Replacement", row_func=replacement_func),
        Group(key=("S", ""), name="Deletion", row_func=deletion_func),
        Group(key=("", "I"), name="Insertion", row_func=insertion_func),
    }
    k2type = {
        ("S", ""): "Deletion",
        ("R", "R"): "Replacement",
        # ('BC', 'BC'),
        # ('', 'D'),
        # ('D', ''),
        ("", "I"): "Insertion",
    }

    def gen_tables():
        for group in groups:

            def gen():
                func = group.row_func
                for pair in D[group.key]:
                    yield func(pair)

            x = list(gen())
            yield (group.name, pd.DataFrame(x))

    tables = dict(gen_tables())
    return tables


def block2fragment(appli, lookup, block):
    if not block:
        return Fragment("", "", [])
    start = block[1]
    end = block[2]
    txt = appli.bbl.texte[start:end]
    c2s = lookup.character2sentence
    S = lookup.sentences
    # first the sentences indices
    sids = sorted({c2s[k] for k in range(start, end - 1) if k in c2s})
    context = [lookup.sentences[k] for k in sids]
    return Fragment(block[0], txt, context)


import functools

Fragment = namedtuple("fragment", "type txt context")


def pretty_print(appli):
    sentence_lookup = make_sentence_lookup(appli.bbl.texte)
    W = 40
    f = functools.partial(block2fragment, appli, sentence_lookup)
    template = (
        "{la:<4}|{lcode}{ta:<__W__}{reset}|{rcode}{tb:<__W__}{reset}|{lb:>4}".replace(
            "__W__", str(W)
        )
    )
    for a, b in appli.bbl.liste:
        fa = f(a)
        fb = f(b)
        type2code = {"BC": Fore.BLACK, "R": Fore.RED, "I": Fore.BLUE, "": Fore.YELLOW}
        lcode = type2code.get(fa.type, Fore.YELLOW)
        rcode = type2code.get(fb.type, Fore.YELLOW)
        for la, lb, ta, tb in it.izip_longest(
            [fa.type], [fb.type], tw.wrap(fa.txt, W), tw.wrap(fb.txt, W), fillvalue=" "
        ):
            print(
                (
                    template.format(
                        lcode=lcode,
                        rcode=rcode,
                        reset=Style.RESET_ALL,
                        la=la,
                        lb=lb,
                        ta=ta,
                        tb=tb,
                    )
                )
            )
            if fa.type == "R":
                print(("context A".center(80, "*")))
                print(("\r".join(fa.context)))
                print(("".center(80, "*")))
                print(("context B".center(80, "*")))
                print(("\r".join(fb.context)))
                print(("".center(80, "*")))
