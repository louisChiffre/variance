import itertools
import logging
import pathlib
import re
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from collections import namedtuple
from pathlib import Path
import bs4
from bs4 import BeautifulSoup
from lxml import etree
from enum import Enum
import copy
import tqdm
import testfixtures

from variance import operations as op

from variance.medite import medite as md
from variance.medite.utils import make_html_output, make_javascript_output

logger = logging.getLogger(__name__)


namespaces = {"": "http://www.tei-c.org/ns/1.0"}
# Register namespaces
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

# we keep track of the escape characters
escape_characters_mapping = {
    # currently em
}

escape_characters_regex = re.escape("|".join(escape_characters_mapping.keys()))
newline = "\n"

REPLACE = namedtuple("REPLACE", "start end old new")
INSERT = namedtuple("INSERT", "start text")
TEXT = namedtuple("TEXT", "conetnt replacements insertions")


def xml2medite(text) -> TEXT:
    """transform xml text to medite text"""

    def gen():
        yield from escape_characters_mapping.keys()
        yield from ["<p>", "</p>"]

    regex = re.escape("|".join(gen()))


def read(filepath: pathlib.Path):
    xml_content = filepath.read_text(encoding="utf-8")
    soup = BeautifulSoup(xml_content, "xml")
    return soup


def remove_emph_tags(input_text):
    return re.sub(r"<emph>(.*?)</emph>", r"\\\1\\", input_text)


def add_emph_tags(txt: str):
    """replace text surrounded by backslash with <emph> tags"""
    # txt_original = txt
    return re.sub(r"\\(.*?)\\", r"<emph>\1</emph>", txt)


def add_escape_characters(txt: str):
    for a, b in escape_characters_mapping.items():
        txt = txt.replace(a, b)
    return txt


def remove_medite_annotations(txt: str) -> str:
    # remove escape characters
    txt = txt.replace(newline, "")

    for b, a in escape_characters_mapping.items():
        txt = txt.replace(a, b)

    return txt


Output = namedtuple("Output", "id txt soup path changes rchanges pos2annotation")


# TODO rename to preprocess_xml or tei2txt
def xml2txt(filepath: pathlib.Path) -> Output:
    """extract text from xml and apply pre-processing step to text"""
    soup = read(filepath=filepath)
    body = soup.find("body")
    text = "".join([str(k) for k in body.find_all("div")])
    logger.info(f"transform {filepath} to text")
    x = op.xml2medite(text)
    txt = x.text

    # we store the txt file in txt
    txt_filepath = filepath.with_suffix(".medite.txt")
    logger.info(
        f"tei file {filepath} transformed to plain text file with medite annotation {txt_filepath}"
    )
    txt_filepath.write_text(txt, encoding="utf-8")

    # the output fo the function contains the txt, but also the original xml document and the character to paragraph mapping
    return Output(
        id=soup.find("TEI")["xml:id"],
        txt=txt,
        soup=soup,
        changes=x,
        path=filepath,
        pos2annotation=None,
        rchanges=op.reverse_transform(x),
    )


Block = namedtuple("Block", "a b")
Result = namedtuple("Result", "appli deltas")

BC = namedtuple("BC", "a_start a_end b_start b_end")
S = namedtuple("S", "start end")
I = namedtuple("I", "start end")
DB = namedtuple("DB", "start end")
DA = namedtuple("DA", "start end")
R = namedtuple("R", "a_start a_end b_start b_end")


def calc_revisions(z1: Output, z2: Output, parameters: md.Parameters) -> Result:
    """apply medite on the two texts and generate pairs of modifications"""

    # we call medite
    appli = md.DiffTexts(chaine1=z1.txt, chaine2=z2.txt, parameters=parameters)

    # we then retrieve the detlas in a structure that will allow us to construct the TEI xml
    def t2n(x):
        return [Block(*k) for k in x]

    N = len(z1.txt)

    def handle(x):
        match x:
            case (("BC", a_start, a_end, []), ("BC", b_start, b_end, [])):
                return BC(a_start, a_end, b_start - N, b_end - N)
            case (("S", start, end, []), None):
                return S(start, end)
            case (None, ("I", start, end, [])):
                return I(start - N, end - N)
            case (("R", a_start, a_end, []), ("R", b_start, b_end, [])):
                return R(a_start, a_end, b_start - N, b_end - N)
            # case when a block was moved and this block replace an existing block
            # it's a Deplacement/Replacement
            # A ---+
            #      |
            #      v
            # C    A
            case (("R", a_start, a_end, dummy_1), ("R", b_start, b_end, dummy_2)):
                return R(a_start, a_end, b_start - N, b_end - N)

            case (None, ("D", start, end, [])):
                return DB(start - N, end - N)
            case (("D", start, end, []), None):
                return DA(start, end)
            case _:
                raise Exception(f"cannot match {x}")

    deltas = [handle(k) for k in appli.bbl.liste]

    # we verify we can reconstruct the two texts from the deltas

    # we reconstruct the first text
    z = [k for k in deltas if isinstance(k, (BC, S, R, DA))]
    assert "".join([z1.txt[k[0] : k[1]] for k in z]) == z1.txt

    # then the second text
    # requires more work
    def gen():
        # Insertion and move
        yield from [(k.start, k.end) for k in deltas if isinstance(k, (I, DB))]
        # Block commom
        yield from [(k.b_start, k.b_end) for k in deltas if isinstance(k, (BC, R))]

    txt2 = "".join([z2.txt[k[0] : k[1]] for k in sorted(gen())])
    # tidbit to facilitate debugging, will flag the first character that has changed
    # act = txt2
    # ref = z2.txt
    # k = next((i for i, z in enumerate(zip(act, ref)) if z[0] != z[1]), None)
    # assert k is None

    assert txt2 == z2.txt
    return Result(appli=appli, deltas=deltas)


class IdenticalFilesException(Exception):
    pass


def concat_overlap(a: str, b: str) -> str:
    max_overlap = min(len(a), len(b))
    for i in range(max_overlap, 0, -1):
        if a.endswith(b[:i]):
            return a + b[i:]
    return a + b


def process(
    source_filepath: pathlib.Path,
    target_filepath: pathlib.Path,
    parameters: md.Parameters,
    output_filepath: pathlib.Path,
):
    """Compare two TEI XML files and generate a new TEI XML file describing the changes between the two versions.

    Args:
        source_filepath (pathlib.Path): The path to the source TEI XML file.
        target_filepath (pathlib.Path): The path to the target TEI XML file.
        parameters (md.Parameters): The parameters for the comparison.
        output_filepath (pathlib.Path): The path to save the output TEI XML file.

    Returns:
        None
    """
    """the main function"""
    # we transform the xml in text with medite annotations
    logger.info(f"using [{repr(parameters.sep)}]")
    logger.info(f"process {str(source_filepath)=} {str(target_filepath)=}")

    z1 = xml2txt(source_filepath)
    z2 = xml2txt(target_filepath)
    if z1.txt == z2.txt:
        raise IdenticalFilesException(
            f"{source_filepath} and {target_filepath} are identical"
        )

    # create the skeleton of the xml
    root = ET.Element(
        "{http://www.tei-c.org/ns/1.0}TEI",
        {
            "xml:id": z1.soup.find("TEI")["xml:id"],
            "corresp": z2.soup.find("TEI")["xml:id"],
        },
    )

    root.append(ET.fromstring(str(z1.soup.find("teiHeader"))))

    medite_data = ET.SubElement(root, "mediteData")

    # Add informations element
    ET.SubElement(
        medite_data,
        "informations",
        {
            "car_mot": str(int(parameters.car_mot)),
            "caseSensitive": str(int(parameters.case_sensitive)),
            "diacriSensitive": str(int(parameters.diacri_sensitive)),
            "lg_pivot": str(int(parameters.lg_pivot)),
            "ratio": str(int(parameters.ratio)),
            "sepSensitive": str(int(parameters.sep_sensitive)),
            "seuil": str(int(parameters.seuil)),
            "fsource": f"{z1.id}.txt",
            "fcible": f"{z2.id}.txt",
            "vsource": z1.id,
            "vcible": z2.id,
        },
    )

    lists = {
        "deletion": ET.SubElement(medite_data, "listDeletion"),
        "addition": ET.SubElement(medite_data, "listAddition"),
        "transpose": ET.SubElement(medite_data, "listTranspose"),
        "substitution": ET.SubElement(medite_data, "listSubstitution"),
    }

    # execute medite
    logger.info("calculate differences")
    res = calc_revisions(z1=z1, z2=z2, parameters=parameters)
    logger.info("generate TEI file")

    # we create the html for debugging/verification purpose purpose
    html_output_filename = output_filepath.with_suffix(".html")
    logger.info(f"generating classic html output {html_output_filename}")
    make_html_output(appli=res.appli, html_filename=html_output_filename)
    logger.info("html creation completed")

    zbody = ""

    # populate the xml
    updated = set()

    def add_list(z: Output, start, end, attributes, name):
        """add change to list of change for the list tags of mediteData"""
        txt = op.extract(z.rchanges, start, end)
        elem = ET.SubElement(lists[name], name, attributes)
        elem.text = txt

    def metamark(function: str, target: str):
        """creates a metamark"""
        return z1.soup.new_tag("metamark", function=function, target=target)

    # we need to keep track of moved blocks
    z2_moved_blocks = {}
    z1_moved_blocks = {}
    for z in res.deltas:
        if isinstance(z, DA):
            key = z1.txt[z.start : z.end]
            z1_moved_blocks[key] = z
        elif isinstance(z, DB):
            key = z2.txt[z.start : z.end]
            z2_moved_blocks[key] = z

    # we need to keep track of the moves
    txt2delta = {z1.txt[k.start : k.end]: k for k in res.deltas if isinstance(k, DA)}

    RESULT = []
    BLOCKS = []

    def get_block(start, end):
        """retrieve the original xml text"""
        txt = op.extract(z1.rchanges, start, end)
        if BLOCKS:
            # We verify that the blocks are contiguous to guarantee the text is invariant
            expected_start = BLOCKS[-1][-1]
            if expected_start != start:
                missing_txt = op.extract(z1.rchanges, expected_start, start)
                raise ValueError(
                    f"Text [{missing_txt}] is missing. Expected block to start at {expected_start}, but found {start}. Blocks are not contiguous."
                )

        BLOCKS.append([start, end])
        RESULT.append(txt)
        actual = "".join(RESULT)
        # We verify that we are re-constructing the original text
        if not z1.rchanges.text.startswith(actual):
            # Special case when there was the deletion of section at the beginning of the block
            x = op.extract(z1.rchanges, start - 1, end)
            xx = RESULT[-2]
            txt = concat_overlap(xx, x)[len(xx) :]
            RESULT[-1] = txt
            actual = "".join(RESULT)
            assert z1.rchanges.text.startswith(actual)

        return txt

    # let's go through the deltas
    for i, z in tqdm.tqdm(
        enumerate(res.deltas), desc="processing deltas", total=len(res.deltas)
    ):
        # each type of change requires a different handling
        50253
        if hasattr(z, "a_start"):
            start = z.a_start
        else:
            start = z.start
        if start >= 50253:
            # breakpoint()
            pass
        if isinstance(z, BC):
            logger.debug("BLOC COMMUN".center(120, "$"))
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"

            tag = z1.soup.new_tag(
                "anchor", **{"xml:id": id_v1, "corresp": id_v2, "function": "bc"}
            )
            # zbody+=str(tag)+op.extract(z1.rchanges, z.a_start, z.a_end)
            zbody += str(tag) + get_block(z.a_start, z.a_end)

        elif isinstance(z, S):
            logger.debug("SUPPRESION".center(120, "$"))
            target_id = f"v1_{z.start}_{z.end}"
            tag = metamark(function="del", target=target_id)

            if op.extract(z1.rchanges, z.start, z.end) == "</p><p>":
                attributes = {"type": "paragraph", "corresp": target_id}
            else:
                attributes = {"corresp": target_id}
            # zbody+=str(tag)+op.extract(z1.rchanges, z.start, z.end)
            zbody += str(tag) + get_block(z.start, z.end)
            add_list(
                z=z1,
                start=z.start,
                end=z.end,
                attributes=attributes,
                name="deletion",
            )
        elif isinstance(z, I):
            logger.debug("INSERTION".center(120, "$"))
            target_id = f"v2_{z.start}_{z.end}"
            tag = metamark(function="add", target=target_id)

            zbody += str(tag)

            add_list(
                z=z2,
                start=z.start,
                end=z.end,
                attributes=dict(corresp=target_id),
                name="addition",
            )

        elif isinstance(z, DA):
            logger.debug("MOVE A".center(120, "$"))
            key = z1.txt[z.start : z.end]
            # we retrieve the corresponding block in the second text
            # special case when a moved block is part of a replacement
            # TODO hanlde case propery
            # zbody+=get_block( z.start, z.end)
            if key in z2_moved_blocks:
                z_ = z2_moved_blocks[key]
                id_v1 = f"v1_{z.start}_{z.end}"
                id_v2 = f"v2_{z_.start}_{z_.end}"
                tag = z1.soup.new_tag(
                    "metamark", function="trans", target=id_v1, corresp=id_v2
                )
            else:
                tag = ""
            # zbody+=str(tag)+op.extract(z1.rchanges, z.start, z.end)
            zbody += str(tag) + get_block(z.start, z.end)
            add_list(
                z=z1,
                start=z.start,
                end=z.end,
                attributes=dict(target=id_v1, corresp=id_v2),
                name="transpose",
            )
        elif isinstance(z, DB):
            logger.debug("MOVE B".center(120, "$"))

            txt = z2.txt[z.start : z.end]
            assert txt in txt2delta, f"Cannot find a delta matching with {txt=}"
            z_ = txt2delta[txt]
            id_v1 = f"v1_{z_.start}_{z_.end}"
            tag = metamark(function="trans", target=id_v1)
            zbody += str(tag)

        elif isinstance(z, R):
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
            tag = z1.soup.new_tag(
                "metamark", function="subst", target=id_v1, corresp=id_v2
            )
            # zbody+=str(tag)+op.extract(z1.rchanges, z.a_start, z.a_end)
            zbody += str(tag) + get_block(z.a_start, z.a_end)
            add_list(
                z=z2,
                start=z.b_start,
                end=z.b_end,
                attributes=dict(target=id_v1, corresp=id_v2),
                name="substitution",
            )
        else:
            raise NotImplementedError(f"Element of type {z} is not supported")

    # We verify we have reconstructed the original text
    actual = "".join(RESULT)
    expected = z1.rchanges.text
    testfixtures.compare(
        actual,
        expected,
        x_label="reconstructed text",
        y_label="original text",
        raises=True,
    )
    # pathlib.Path("text.xml").write_text(zbody, encoding="utf-8")
    root.append(ET.fromstring("<body>" + zbody + "</body>"))
    tree = ET.ElementTree(root)
    logger.info(f"Write output to {str(output_filepath)}")
    tree.write(output_filepath, encoding="utf-8", xml_declaration=True, method="xml")

    logger.info(f"Creating temporary xml string")
    xml_str = ET.tostring(root, encoding="unicode")

    # Pretty print using lxml
    parser = etree.XMLParser(remove_blank_text=True)
    logger.info("Creating temporary xml string")
    xml_tree = etree.fromstring(xml_str, parser)
    pretty_xml_str = etree.tostring(xml_tree, pretty_print=True, encoding="unicode")

    processing_instruction = '<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0" ?>\n'
    pretty_xml_str = add_emph_tags(processing_instruction + pretty_xml_str.lstrip())
    # Write to file

    logger.info(f"Write output to {str(output_filepath)}")
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(pretty_xml_str)
    return


def create_tei_xml(
    path: Path, pub_date_str: str, title_str: str, version_nb: int
) -> Path:
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
    title.text = f"{title_str} V{version_nb}"
    author = ET.SubElement(titleStmt, f"{{{TEI_NS}}}author")
    author.text = ""
    editor = ET.SubElement(titleStmt, f"{{{TEI_NS}}}editor")

    # publicationStmt and its structure
    publicationStmt = ET.SubElement(fileDesc, f"{{{TEI_NS}}}publicationStmt")
    publisher = ET.SubElement(publicationStmt, f"{{{TEI_NS}}}publisher")
    publisher.text = "Variance - UNIL"
    pub_date = ET.SubElement(publicationStmt, f"{{{TEI_NS}}}date")
    pub_date.text = f"{pub_date_str}"

    # sourceDesc and its structure
    sourceDesc = ET.SubElement(fileDesc, f"{{{TEI_NS}}}sourceDesc")
    bibl = ET.SubElement(sourceDesc, f"{{{TEI_NS}}}bibl")
    bibl_date = ET.SubElement(bibl, f"{{{TEI_NS}}}date")
    bibl_date.text = "n/a"

    # text body
    text = ET.SubElement(tei, f"{{{TEI_NS}}}text")
    body = ET.SubElement(text, f"{{{TEI_NS}}}body")
    div = ET.SubElement(body, f"{{{TEI_NS}}}div")
    # Split body_text by newlines and create <p> elements for each paragraph
    txt = path.read_text(encoding="utf-8")
    paragraphs = txt.split(newline)
    # if the last character is a new line, split will create an empty paragraph at the end, we need to correct that
    if txt.endswith(newline):
        paragraphs = paragraphs[:-1]

    for para in paragraphs:
        p_element = ET.SubElement(div, f"{{{TEI_NS}}}p")
        txt = remove_medite_annotations(txt=para)

        p_element.text = remove_medite_annotations(txt=txt)

    # for para in paragraphs:
    #     if para.strip():  # Check if the paragraph is not empty
    #         p_element = ET.SubElement(body, f'{{{TEI_NS}}}p')
    #         p_element.text = para.strip()
    # Generate the XML tree
    rough_string = ET.tostring(tei, "utf-8")

    # Pretty print using minidom
    reparsed = minidom.parseString(rough_string)
    pretty_xml = add_emph_tags(reparsed.toprettyxml(indent="  "))

    # Write the pretty-printed XML to a file
    output_path = path.with_suffix(".xml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    return output_path
