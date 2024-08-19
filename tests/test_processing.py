import pytest
from variance import processing as p
import pathlib
from pathlib import Path
from collections import namedtuple
from variance.medite import medite as md

DATA_DIR = Path("tests/data/samples")
XML_DATA_DIR = DATA_DIR / Path("exemple_variance")
TXT_DATA_DIR = DATA_DIR / Path("post_processing")


@pytest.mark.parametrize(
    "filename,id",
    [
        ("la_vieille_fille_v1.xml", "lvf_v1"),
    ],
)
def test_xml2txt(filename, id):
    z = p.xml2txt(filepath=XML_DATA_DIR / filename)
    assert z.id == id


Result = namedtuple("Result", "ins sup remp bc bd lg")
Block = namedtuple("Block", "a b")


@pytest.mark.parametrize(
    "filename",
    [
        ("comparaison_la_vieille_fille_v1.xml"),
    ],
)
def test_process(filename):
    filepath = XML_DATA_DIR / filename
    soup = p.read(filepath=filepath)
    dic = soup.find("informations").attrs

    parameters = md.Parameters(
        lg_pivot=int(dic["lg_pivot"]),
        ratio=int(dic["ratio"]),
        seuil=int(dic["seuil"]),
        car_mot=True,  # always,
        case_sensitive=bool(int(dic["caseSensitive"])),
        sep_sensitive=bool(int(dic["sepSensitive"])),
        diacri_sensitive=bool(int(dic["diacriSensitive"])),
        algo="HIS",
    )

    z = [
        p.xml2txt(k)
        for k in XML_DATA_DIR.glob("*.xml")
        if not str(k.name).startswith("comp") and not str(k.name).startswith("diff")
    ]

    # lg_pivot ratio seuil car_mot case_sensitive sep_sensitive diacri_sensitive algo')
    id2filepath = {k.id: k.path for k in z}

    p.process(
        source_filepath=id2filepath[dic["vsource"]],
        target_filepath=id2filepath[dic["vcible"]],
        parameters=parameters,
        output_filepath=filepath.with_suffix(".output.xml"),
    )


@pytest.mark.parametrize(
    "txt,expected",
    [
        (
            "rovinces de France /plus/ /ou/ /moins/ de /chevaliers/ /de/ /Valois/ il en existait",
            "rovinces de France <emph>plus ou moins</emph> de <emph>chevaliers de Valois</emph> il en existait",
        ),
        (
            "rovinces de France /plus/ /ou/ /moins/ /de/ /chevaliers/ /de/ /Valois/ il en existait",
            "rovinces de France <emph>plus ou moins de chevaliers de Valois</emph> il en existait",
        ),
    ],
)
def test_add_emp_tags(txt, expected):
    actual = p.add_emph_tags(txt)
    assert actual == expected


@pytest.mark.parametrize(
    "name,title", [["vf", "La vieille fille"], ["vndtt", "La Vendetta"]]
)
def test_post_processing(name, title):
    p1 = TXT_DATA_DIR / f"1{name}.txt"
    p2 = TXT_DATA_DIR / f"2{name}.txt"
    pub_date_str = "01.07.2024"
    create_tei_xml(path=p1, pub_date_str=pub_date_str, title=title, version_nb=1)
    create_tei_xml(path=p2, pub_date_str=pub_date_str, title=title, version_nb=2)
    print(name)


import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom


def create_tei_xml(path: Path, pub_date_str: str, title: str, version_nb: int):
    assert path.exists(), f"{path} does not exist"
    # Namespaces
    TEI_NS = "http://www.tei-c.org/ns/1.0"
    ET.register_namespace("", TEI_NS)

    # Root element with namespace and attributes
    tei = ET.Element(f"{{{TEI_NS}}}TEI", attrib={"xml:id": "lvf_v1"})

    # teiHeader and its structure
    teiHeader = ET.SubElement(tei, f"{{{TEI_NS}}}teiHeader")

    # fileDesc and its structure
    fileDesc = ET.SubElement(teiHeader, f"{{{TEI_NS}}}fileDesc")

    # titleStmt and its structure
    titleStmt = ET.SubElement(fileDesc, f"{{{TEI_NS}}}titleStmt")
    title = ET.SubElement(titleStmt, f"{{{TEI_NS}}}title")
    title.text = f'{title} V{version_nb}'
    author = ET.SubElement(titleStmt, f"{{{TEI_NS}}}author")
    author.text = ""
    editor = ET.SubElement(titleStmt, f"{{{TEI_NS}}}editor")

    # publicationStmt and its structure
    publicationStmt = ET.SubElement(fileDesc, f"{{{TEI_NS}}}publicationStmt")
    publisher = ET.SubElement(publicationStmt, f"{{{TEI_NS}}}publisher")
    publisher.text = "Variance - UNIL"
    pub_date = ET.SubElement(publicationStmt, f"{{{TEI_NS}}}date")
    pub_date.text = f'{pub_date_str}'

    # sourceDesc and its structure
    sourceDesc = ET.SubElement(fileDesc, f"{{{TEI_NS}}}sourceDesc")
    bibl = ET.SubElement(sourceDesc, f"{{{TEI_NS}}}bibl")
    bibl_date = ET.SubElement(bibl, f"{{{TEI_NS}}}date")
    bibl_date.text = "n/a"

    # text body
    text = ET.SubElement(tei, f"{{{TEI_NS}}}text")
    body = ET.SubElement(text, f"{{{TEI_NS}}}body")

    # Generate the XML tree
    rough_string = ET.tostring(tei, "utf-8")

    # Pretty print using minidom
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Write the pretty-printed XML to a file
    output_path = path.with_suffix(".xml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
