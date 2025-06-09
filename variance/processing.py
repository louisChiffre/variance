import itertools
import logging
import pathlib
import re
import subprocess
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from collections import defaultdict, namedtuple
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


Output = namedtuple(
    "Output", "id txt soup path path_txt changes rchanges pos2annotation"
)


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
        path_txt=txt_filepath,
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
    # we need to sort them first
    def gen():
        # Insertion and move
        yield from [(k.start, k.end) for k in deltas if isinstance(k, (I, DB))]
        # Block commom
        yield from [(k.b_start, k.b_end) for k in deltas if isinstance(k, (BC, R))]

    txt2 = "".join([z2.txt[k[0] : k[1]] for k in sorted(gen())])

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
    xhtml_output_dir: pathlib.Path,
) -> list[pathlib.Path]:
    """Compare two TEI XML files and generate a new TEI XML file describing the changes between the two versions

    Args:
        source_filepath (pathlib.Path): The path to the source TEI XML file.
        target_filepath (pathlib.Path): The path to the target TEI XML file.
        parameters (md.Parameters): The parameters for the comparison.
        output_filepath (pathlib.Path): The path to save the output TEI XML file.

    Returns:
        None
    """
    # we transform the xml in text with medite annotations
    logger.info(f"using [{repr(parameters.sep)}]")
    logger.info(f"process {str(source_filepath)=} {str(target_filepath)=}")

    # we keep track of all
    debug_filepaths = []

    z1 = xml2txt(source_filepath)
    z2 = xml2txt(target_filepath)

    debug_filepaths.append(z1.path_txt)
    debug_filepaths.append(z2.path_txt)
    debug_filepaths.append(source_filepath)
    debug_filepaths.append(target_filepath)

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

    ops2xml = {
        "deletion": ET.SubElement(medite_data, "listDeletion"),
        "addition": ET.SubElement(medite_data, "listAddition"),
        "transpose": ET.SubElement(medite_data, "listTranspose"),
        "substitution": ET.SubElement(medite_data, "listSubstitution"),
    }
    # TODO simplify further as href/id/file sharet the same prefix
    ops2xhtml = {
        "deletion": dict(href="#as", id="lbs", file="s"),
        "addition": dict(href="#bi", id="lai", file="i"),
        "transpose": dict(href="#ad", id="lbd", file="d"),
        "substitution": dict(href="#ar", id="lbr", file="r"),
        "bc": dict(href="#bc", id="ac", file="bc"),
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
    debug_filepaths.append(html_output_filename)

    zbody = ""

    # populate the xlm
    updated = set()

    xhtml_lists = defaultdict(list)
    xhtml_counter = defaultdict(int)
    xhtml_mains = defaultdict(list)

    def add_list_xml(z: Output, start, end, attributes, name):
        """add change to list of change for the list tags of mediteData"""
        txt = op.extract(z.rchanges, start, end)

        elem = ET.SubElement(ops2xml[name], name, attributes)
        elem.text = txt

    def add_main_xhtml(txt, name, main_name, id_suffix):
        ops = ops2xhtml[name]
        name2class_name = {
            "bc": "span_c sync sync-single",
            "deletion": "span_s",
            "substitution": "sync sync-single span_r",
            "transpose": "sync sync-single span_d",
            "addition": "span_i",
        }
        name2element_name = {
            "bc": "a",
            "substitution": "a",
            "deletion": "span",
            "transpose": "a",
            "addition": "span",
        }
        txt_ = txt
        # we rem
        txt = txt2main_xml(txt)

        class_name = name2class_name[name]
        element_name = name2element_name[name]
        href_id = f"{ops['href']}_{id_suffix}"
        li_id = f"{ops['id']}_{id_suffix}"
        xhtml = f'<{element_name} class="{class_name}"  data-tags="" href="{href_id}" id="{li_id}">{txt}</{element_name}>'
        xhtml_mains[main_name].append(xhtml)

    def add_list_xhtml(z: Output, start, end, attributes, name, id_suffix):
        ops = ops2xhtml[name]
        txt = op.extract(z.rchanges, start, end)
        txt_ = txt
        # we rem
        txt = txt2list_xhtml(txt)
        # xhtml_counter[name] += 1
        # id_suffix = f"_{xhtml_counter[name]:05d}"
        href_id = f"{ops['href']}_{id_suffix}"
        li_id = f"{ops['id']}_{id_suffix}"
        li_element = f'<li><a class="sync" data-tags="" href="{href_id}" id="{li_id}">{txt}</a></li>'
        # We verify the li_element is well-formed XML
        # breakpoint()
        assert not has_xml_errors_in_string(li_element)

        xhtml_lists[name].append(li_element)

    def add_list(z: Output, start, end, attributes, name, id_suffix):
        add_list_xml(z=z, start=start, end=end, attributes=attributes, name=name)
        add_list_xhtml(
            z=z,
            start=start,
            end=end,
            attributes=attributes,
            name=name,
            id_suffix=id_suffix,
        )

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

    # Dictionary to store RESULT and BLOCKS for each text
    Z_DATA = {"z1": {"RESULT": [], "BLOCKS": []}, "z2": {"RESULT": [], "BLOCKS": []}}

    def get_block(start, end, z):
        assert z in (z1, z2)
        txt = op.extract(z.rchanges, start, end)

        # Use the appropriate tracking variables based on which text we're processing
        key = "z1" if z == z1 else "z2"
        RESULT = Z_DATA[key]["RESULT"]
        BLOCKS = Z_DATA[key]["BLOCKS"]

        if BLOCKS:
            # We verify that the blocks are contiguous to guarantee the text is invariant
            expected_start = BLOCKS[-1][-1]
            if expected_start != start:
                missing_txt = op.extract(z.rchanges, expected_start, start)
                raise ValueError(
                    f"Text [{missing_txt}] is missing. Expected block to start at {expected_start}, but found {start}. Blocks are not contiguous."
                )

        BLOCKS.append([start, end])
        RESULT.append(txt)
        actual = "".join(RESULT)
        # We verify that we are re-constructing the original text
        if not z.rchanges.text.startswith(actual):
            # Special case when there was the deletion of section at the beginning of the block
            x = op.extract(z.rchanges, start - 1, end)
            if len(RESULT) >= 2:
                xx = RESULT[-2]
                txt = concat_overlap(xx, x)[len(xx) :]
                RESULT[-1] = txt
                actual = "".join(RESULT)
                assert z.rchanges.text.startswith(actual)

        return txt

    # let's go through the deltas
    for i, z in tqdm.tqdm(
        enumerate(res.deltas), desc="processing deltas", total=len(res.deltas)
    ):
        # each type of change requires a different handling
        if isinstance(z, BC):
            logger.debug("BLOC COMMUN".center(120, "$"))
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"

            tag = z1.soup.new_tag(
                "anchor", **{"xml:id": id_v1, "corresp": id_v2, "function": "bc"}
            )
            # zbody+=str(tag)+op.extract(z1.rchanges, z.a_start, z.a_end)
            txt = get_block(z.a_start, z.a_end, z=z1)
            zbody += str(tag) + txt

            add_main_xhtml(txt=txt, name="bc", main_name="source", id_suffix=id_v1)

        elif isinstance(z, S):
            logger.debug("SUPPRESION".center(120, "$"))
            target_id = f"v1_{z.start}_{z.end}"
            tag = metamark(function="del", target=target_id)

            if op.extract(z1.rchanges, z.start, z.end) == "</p><p>":
                attributes = {"type": "paragraph", "corresp": target_id}
            else:
                attributes = {"corresp": target_id}
            # zbody+=str(tag)+op.extract(z1.rchanges, z.start, z.end)
            txt = get_block(z.start, z.end, z=z1)
            zbody += str(tag) + txt
            add_list(
                z=z1,
                start=z.start,
                end=z.end,
                attributes=attributes,
                name="deletion",
                id_suffix=target_id,
            )
            add_main_xhtml(
                txt=txt, name="deletion", main_name="source", id_suffix=id_v1
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
                id_suffix=target_id,
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
                # raise NotImplementedError("Cannot find a reference")
            # zbody+=str(tag)+op.extract(z1.rchanges, z.start, z.end)
            txt = get_block(z.start, z.end, z=z1)
            zbody += str(tag) + txt
            add_list(
                z=z1,
                start=z.start,
                end=z.end,
                attributes=dict(target=id_v1, corresp=id_v2),
                name="transpose",
                id_suffix=id_v1,
            )
            add_main_xhtml(
                txt=txt, name="transpose", main_name="source", id_suffix=id_v1
            )
        elif isinstance(z, DB):
            logger.debug("MOVE B".center(120, "$"))

            txt = z2.txt[z.start : z.end]
            assert txt in txt2delta, f"Cannot find a delta matching with {txt=}"
            z_ = txt2delta[txt]
            id_v2 = f"v2_{z_.start}_{z_.end}"
            tag = metamark(function="trans", target=id_v2)
            zbody += str(tag)

        elif isinstance(z, R):
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
            tag = z1.soup.new_tag(
                "metamark", function="subst", target=id_v1, corresp=id_v2
            )
            # zbody+=str(tag)+op.extract(z1.rchanges, z.a_start, z.a_end)
            txt = get_block(z.a_start, z.a_end, z=z1)
            zbody += str(tag) + txt
            add_list(
                z=z2,
                start=z.b_start,
                end=z.b_end,
                attributes=dict(target=id_v1, corresp=id_v2),
                name="substitution",
                id_suffix=id_v1,
            )
            add_main_xhtml(
                txt=txt, name="substitution", main_name="source", id_suffix=id_v1
            )
        else:
            raise NotImplementedError(f"Element of type {z} is not supported")

    def gen_detlas_target():
        # Insertion and move
        yield from [(k.start, k) for k in res.deltas if isinstance(k, (I, DB))]
        # Block commom
        yield from [(k.b_start, k) for k in res.deltas if isinstance(k, (BC, R))]

    deltas_target = sorted(gen_detlas_target())
    for i, sz in tqdm.tqdm(
        enumerate(deltas_target), desc="processing deltas", total=len(deltas_target)
    ):
        _, z = sz
        if isinstance(z, BC):
            logger.debug("BLOC COMMUN".center(120, "$"))
            id_v2 = f"v2_{z.b_start}_{z.b_end}"

            # zbody+=str(tag)+op.extract(z1.rchanges, z.a_start, z.a_end)
            txt = get_block(z.b_start, z.b_end, z=z2)
            add_main_xhtml(txt=txt, name="bc", main_name="target", id_suffix=id_v2)
        elif isinstance(z, I):
            logger.debug("INSERTION".center(120, "$"))
            target_id = f"v2_{z.start}_{z.end}"
            txt = get_block(z.start, z.end, z=z2)
            add_main_xhtml(
                txt=txt, name="addition", main_name="target", id_suffix=target_id
            )
        elif isinstance(z, DB):
            logger.debug("MOVE B".center(120, "$"))
            target_id = f"v1_{z_.start}_{z_.end}"
            txt = get_block(z.start, z.end, z=z2)
            add_main_xhtml(
                txt=txt, name="transpose", main_name="target", id_suffix=target_id
            )
        elif isinstance(z, R):
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
            txt = get_block(z.b_start, z.b_end, z=z2)
            add_main_xhtml(
                txt=txt, name="substitution", main_name="target", id_suffix=id_v2
            )

    # We verify we have reconstructed the original text
    actual = "".join(Z_DATA["z1"]["RESULT"])
    expected = z1.rchanges.text
    testfixtures.compare(
        actual,
        expected,
        x_label="reconstructed text",
        y_label="original text",
        raises=True,
    )

    # TODO do it for z2 as well

    # pathlib.Path("text.xml").write_text(zbody, encoding="utf-8")
    root.append(ET.fromstring("<body>" + zbody + "</body>"))
    tree = ET.ElementTree(root)
    logger.info(f"Write output to {str(output_filepath)}")
    tree.write(output_filepath, encoding="utf-8", xml_declaration=True, method="xml")

    logger.info("Creating temporary xml string")
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
    debug_filepaths.append(output_filepath)

    from bs4 import BeautifulSoup

    if xhtml_output_dir:
        for name, xhtml_list in xhtml_lists.items():
            assert not has_xml_errors_in_list_of_strings(
                xhtml_list
            ), f"XML errors in {name} list"
            output_filepath = (
                pathlib.Path(xhtml_output_dir) / f"{ops2xhtml[name]['file']}_py.xhtml"
            )
            xml_string = "\n".join(xhtml_list)
            output_filepath.write_text(xml_string, encoding="utf-8")
            logger.info(f"Write {name} list to {str(output_filepath)}")
        for name, xhtml_list in xhtml_mains.items():
            output_filepath = pathlib.Path(xhtml_output_dir) / f"{name}_py.xhtml"
            xhtml_content = "".join(xhtml_list)
            output_filepath.write_text(xhtml_content, encoding="utf-8")
            logger.info(f"Write {name} main to {str(output_filepath)}")

    return debug_filepaths


def has_xml_errors_in_string(xml_string):
    try:
        ET.fromstring(f"<root>{xml_string}</root>")
        return False  # No errors
    except ET.ParseError as e:
        # Extract the position information from the error
        line_no = (
            getattr(e, "position", (None, None))[0]
            if hasattr(e, "position")
            else "unknown"
        )
        col_no = (
            getattr(e, "position", (None, None))[1]
            if hasattr(e, "position")
            else "unknown"
        )

        # Format the error message with line and position
        error_msg = f"XML Error at line {line_no}, column {col_no}: {str(e)}"

        # Print a snippet of the problematic XML for context
        lines = xml_string.split("\n")
        context = (
            "\n".join(lines[max(0, line_no - 2) : line_no + 1])
            if line_no != "unknown"
            else xml_string[:100]
        )

        print(error_msg)
        print(f"XML context:\n{context}")
        print(f"Full problematic XML: {xml_string}")

        return True  # XML is malformed


def has_xml_errors_in_list_of_strings(xml_strings):
    """Check if any string in the list is a malformed XML."""
    return any(has_xml_errors_in_string(xml_string) for xml_string in xml_strings)


def apply_post_processing(input_filepath: pathlib.Path, output_filepath: pathlib.Path):
    logger.info(f"Applying post-processing to {input_filepath}")
    txt = input_filepath.read_text(encoding="utf-8")

    # we replace all the emph tags that are inside the text and replace them with the none-escaped version
    sa = "&lt;emph&gt;"
    sa_ = "<emph      >"
    sb = "&lt;/emph&gt;"
    sb_ = "</emph      >"
    assert len(sa) == len(sa_)
    assert len(sb) == len(sb_)
    NN = len(txt)
    starts = [m.start() for m in re.finditer(sa, txt)]
    for start in starts:
        N = start + len(sa)
        k = txt[N:].find(sb)
        if k == -1:
            continue
        end = N + k
        x = txt[N:end]
        # if the text contains < or >, we skip it
        if "<" in x or ">" in x:
            continue
        txt = txt[:start] + sa_ + x + sb_ + txt[end + len(sb) :]
        assert len(txt) == NN
        end += N + len(sb)

    txt2rep = (
        ("&lt;p/&gt;", "<br></br>"),
        ("&lt;p&gt;", ""),
        ("&lt;/p&gt;", "<br></br>"),
        ("&lt;/div&gt;", ""),
        (sa_, "<emph>"),
        (sb_, "</emph>"),
    )
    for a, b in txt2rep:
        logger.info(f"replacing {a=} with {b}")
        txt = txt.replace(a, b)

    logger.info(f"Writing post-processed text to {output_filepath}")
    output_filepath.write_text(txt, encoding="utf-8")


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


def create_xhtml(source_filepath, output_dir):
    """
    Create XHTML visualization files for source and target comparison.

    Args:
        source_filepath (Path): Path to the TEI XML file
        output_dir (Path): Directory to save the XHTML output

    Returns:
        Path: Path to the generated XHTML file
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Creating XHTML visualization in {output_dir}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Paths for Saxon and XSL
    saxon_jar = Path("tei2xhtml/lib/SaxonHE12-5J/saxon-he-12.5.jar")
    xsl_file = Path("tei2xhtml/tei2xhtml.xsl")

    # Run Saxon transformation
    logger.info(f"Transforming {source_filepath} to {output_dir}")

    cmd = [
        "java",
        "-jar",
        str(saxon_jar),
        "-s:" + str(source_filepath),
        "-xsl:" + str(xsl_file),
        "-o:" + str(output_dir / ".xml"),
    ]
    logger.info(f"Running command: {' '.join(cmd)}")
    try:

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        logger.info("XSLT transformation completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"XSLT transformation failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise


def log_io(filename):
    def decorator(func):
        def wrapper(arg):
            try:
                result = func(arg)
                with open(filename, "a") as f:
                    f.write(f"({arg!r}, {result!r})\n")
                return result
            except Exception:
                with open(filename, "a") as f:
                    f.write(f"({arg!r}, 'ERR')\n")
                raise

        return wrapper

    return decorator


def replace_emph_with_em(txt: str) -> str:
    """Replace <emph> tags with <em> tags in the given text."""

    # we need to detect <emph> tags that are not closed properly
    # we collect the <emph> and </emph> tags in a list
    tags = re.findall(r"</?emph>", txt)
    stack = []
    orphans = []

    for tag in tags:
        if tag == "<emph>":
            stack.append(tag)
        elif tag == "</emph>":
            if stack:
                stack.pop()
            else:
                orphans.append(tag)
    if stack:
        assert not orphans, f"Orphaned emph tags: {orphans}"
        orphans = stack
    if orphans:
        if not len(orphans) == 1:
            raise NotImplementedError(
                f"Cannot handle multiple orphaned emph tags: {orphans}"
            )
        tag = orphans[0]
        if tag == "</emph>":
            txt = "<emph>" + txt
        elif tag == "<emph>":
            txt = txt + "</emph>"
        else:
            raise NotImplementedError(f"Cannot handle orphaned emph tag: {tag}")
    return txt.replace("<emph>", "<em>").replace("</emph>", "</em>")


def remove_pb_tags(txt: str) -> str:
    """Remove entire <pb> tags from the text also removing the content inside them."""
    return re.sub(r"</?pb\b[^>]*>", "", txt)


# In case you want to log the input and output of the function
# @log_io("txt2list_log.txt")
def txt2list_xhtml(txt):
    txt = replace_emph_with_em(txt)
    txt = remove_pb_tags(txt)
    txt2rep = (
        ("\n", ""),
        ("<p/>", "¶"),
        ("<p>", ""),
        ("</p>", "¶"),
        ("</div>", ""),
    )
    for a, b in txt2rep:
        # logger.info(f"replacing {a=} with {b}")
        txt = txt.replace(a, b)
    return txt


PB_TAG = re.compile(r"<pb\s+([^>/]*?)\s*/>")


def _pb_repl(match: re.Match) -> str:
    attrs = dict(re.findall(r'(\w+)="(.*?)"', match.group(1)))
    facs = attrs.get("facs", "")
    pagination = attrs.get("pagination", "")
    img_name = facs.rsplit(".", 1)[0] if "." in facs else facs
    return (
        f'<span class="page-marker" data-image-name="{img_name}">'
        f'<span class="page-number">{pagination}</span>'
        f'<img src="/img/settings/page_left.svg"/></span>'
    )


def pb_to_main_xhtml(xml: str) -> str:
    """Replace every <pb …/> with the required HTML snippet, leave everything else untouched."""
    return PB_TAG.sub(_pb_repl, xml)


# @log_io("txt2main_log.txt")
def txt2main_xml(txt):
    txt2rep = (
        ("\n", ""),
        # ("<p/>", "\n"),
        # ("<p>", ""),
        ("<p/>", "<br></br>"),
        ("<p>", ""),
        ("</p>", "<br></br>"),
        ("</div>", ""),
        ("<div>", ""),
    )
    for a, b in txt2rep:
        txt = txt.replace(a, b)
    txt = pb_to_main_xhtml(txt)
    return txt
