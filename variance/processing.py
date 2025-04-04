import itertools
import logging
import pathlib
import re
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from collections import namedtuple
from itertools import zip_longest
from pathlib import Path
import bs4
import testfixtures
from bs4 import BeautifulSoup
from intervaltree import IntervalTree
from lxml import etree
from enum import Enum
import copy

from variance.medite import medite as md
from variance.medite.utils import make_html_output, make_javascript_output

logger = logging.getLogger(__name__)


namespaces = {"": "http://www.tei-c.org/ns/1.0"}
# Register namespaces
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

esc = "'"
# we keep track of the escape characters
medite_special_characters = [esc, "|"]
escape_characters_mapping = {
    "…": "'…",
    ".": "'.",
    "»": "'»",
    "«": "«'",
}

escape_characters_regex = re.escape("|".join(escape_characters_mapping.keys()))
newline = """'|""" + "\n"

REPLACE = namedtuple("REPLACE", "start end old new")
INSERT = namedtuple("INSERT", "start text")
TEXT = namedtuple('TEXT', 'content replacements insertions')

def xml2medite(text)->TEXT:
    """transform xml text to medite text"""
    def gen():
        yield from escape_characters_mapping.keys()
        yield from ['<p>','</p>']
    regex = re.escape("|".join(gen()))

    


# TODO rename function to remove_medite_annotations
def remove_medite_annotations_simple(txt: str) -> str:
    txt = txt.replace(newline, "")
    # we remove the newline first as they are replace with <p> tags

    # we remove first the escape characters
    for b, a in escape_characters_mapping.items():
        txt = txt.replace(a, b)

    # then we have to deal with the specaial characters are cut off by xml tags (angchor and metamark)
    for i in [1, 2]:
        x = re.escape(newline[:i])
        y = re.escape(newline[i:])
        pattern = rf"{x}(<[^{x}{y}]+?/>){y}"
        txt = re.sub(pattern, r"\1", txt)

    # special with the newline separated in three
    x = re.escape(newline[0])
    y = re.escape(newline[1])
    z = re.escape(newline[2])
    pattern = rf"{x}(<[^{x}{y}{z}]+?/>){y}(<[^{x}{y}{z}]+?/>){z}"
    txt = re.sub(pattern, r"\1\2", txt)

    # new line in the change list
    for i in [1, 2]:
        x = re.escape(newline[:i])
        pattern = rf"{x}(</[sub|sup|add])"
        txt = re.sub(pattern, r"\1", txt)

    # # special characters in the change list in the change list
    # x = re.escape(newline[0:2])
    # pattern = rf'{x}(</)'
    # breakpoint()
    # txt = re.sub(pattern, r'\1', txt)

    for a, b in escape_characters_mapping.items():
        if b.startswith(esc):
            # case in the body
            x = re.escape(b[:1])
            y = re.escape(b[1:])
            pattern = rf"{x}(<[^{x}{y}]+?/>)({y})"
            txt = re.sub(pattern, r"\1\2", txt)

            # case in the change list
            x = re.escape(b[:1])
            pattern = rf"{x}(</[sub|sup|add])"
            txt = re.sub(pattern, r"\1", txt)

        # TODO implement with "«'",

    return txt


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

    # remove escape characters
    txt = txt.replace(newline, "")

    for a in medite_special_characters:
        txt = txt.replace(a, "")

    return txt


Output = namedtuple("Output", "id txt soup path changes pos2annotation")


def to_txt(filepath: pathlib.Path):
    """transform tei xml in list of lines. This is used for internal consistency checks"""
    soup = read(filepath=filepath)

    def gen():
        for div in soup.find("body").find_all("div"):
            p_elements = div.find_all("p")
            for p in p_elements:

                def gen_p():
                    for content in p.contents:
                        if content.name == "emph":
                            yield content.get_text()
                        elif isinstance(content, str):
                            yield content
                        elif content.name is None and content.string:
                            yield content.string
                        else:
                            pass
                            # raise Exception('Unknown type of content')
                    yield "\n"

                txt = "".join(gen_p())
                yield txt

    return "".join(gen()).split("\n")


def find_next_string_element(z: bs4.element.Tag):
    zz = z.next_sibling
    if zz is None:
        return None

    if isinstance(zz, bs4.element.NavigableString):
        return zz
    return find_next_string_element(zz)


def remove_newline_annotation(body):
    for div in body.find_all("div"):
        paragraphs = div.find_all("p")
        for paragraph in paragraphs:
            z = list(paragraph.strings)
            for x in paragraph.contents:
                # if we have a string
                if isinstance(x, bs4.element.NavigableString):
                    # first we replace the medite annotation
                    # then we check if an escape character was not cut off
                    if len(x) > 0 and x.string[-1] == esc:
                        nx = find_next_string_element(x)
                        # if we have a next string
                        assert nx is not None
                        # if the last character and the starts of the next text forms a newline
                        if (x.string[-1] + nx.string).startswith(newline):
                            x.replace_with(str(x)[:-1])
                            assert nx.string == newline[1:]
                            # we replace it with empty
                            nx.replace_with("")


class Tag(Enum):
    START = "START"
    END = "END"


def to_xml_flat(filepath: pathlib.Path):
    """remove non original tags in tei xml so it can be compared post/pre processing"""
    soup = read(filepath=filepath)
    soup = copy.deepcopy(soup)
    for tag_name in ["metamark", "anchor"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # yield all the xml tags, i.e when an element is open, when it is closed
    def gen():
        # we go through the divs
        for div in soup.find("body").find_all("div"):
            # we go through the paragraphs
            p_elements = div.find_all("p")
            for p in p_elements:
                yield Tag.START
                for x in p.contents:
                    yield x
                yield Tag.END

    # z = list(itertools.chain(*gen()))
    xx = list(gen())

    # we then need to merge the string that were separated by metamarks and anchors
    def gen():
        for t, x_iter in itertools.groupby(xx, type):
            if t == bs4.element.NavigableString:
                k = "".join(x_iter)
                # we remove the new line
                if k.strip():
                    yield k
            else:
                x = list(x_iter)
                # if len(x)>1:
                #     breakpoint()
                yield from x

    return list(gen())


# TODO rename to preprocess_xml or tei2txt
def xml2txt(filepath: pathlib.Path) -> Output:
    """extract text from xml and apply pre-processing step to text"""
    soup = read(filepath=filepath)
    body = soup.find("body")
    text=''.join([str(k) for k in body.find_all("div")])
    logger.info(f'transform {filepath} to text')
    x = op.xml2medite(text)
    txt = x.text


    # we store the txt file in txt
    txt_filepath = filepath.with_suffix(".medite.txt")
    logger.info(
        f"tei file {filepath} transformed to plain text file with medite annotation {txt_filepath}"
    )
    txt_filepath.write_text(txt, encoding="utf-8")

    # the output of the function contains the txt, but also the original xml document and the character to paragraph mapping
    return Output(
        id=soup.find("TEI")["xml:id"],
        txt=txt,
        soup=soup,
        changes=x,
        path=filepath,
        pos2annotation=None,
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

from variance import operations as op
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
        raise IdenticalFilesException(f"{source_filepath} and {target_filepath} are identical")

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
    logger.info('process completed')
    return

    # we don't want the script to stop if there is an ntld data issue
    try:
        make_javascript_output(appli=res.appli, base_dir=source_filepath.parent)
    except Exception as e:
        print(f"Could not generate javascript output {e}")

    # populate the xml
    updated = set()

    def get_xml_text_from_range(z: Output, start, end):
        def gen():
            for k in range(start, end):
                if k in z.pos2annotation:
                    yield z.pos2annotation[k]
                else:
                    yield z.txt[k]

        def gen2():
            for group, k_iter in itertools.groupby(gen(), type):
                if group == bs4.element.Tag:
                    yield from k_iter
                else:
                    yield "".join(k_iter)

        return list(gen2())

    # there is a series of utility functions
    # add to the list of changes
    def add_list_(txt, attributes, name):
        """add change to list of change for the list tags of mediteData"""

        list_elem = lists[name]
        elem = ET.SubElement(lists[name], name, attributes)
        if txt:
            elem.text = remove_medite_annotations(txt)

    def add_list(z: Output, start, end, attributes, name):
        """add change to list of change for the list tags of mediteData"""
        breakpoint()
        txts = get_xml_text_from_range(z=z, start=start, end=end)

        list_elem = lists[name]
        # we create a new element with the correct tag and attributes
        elem = ET.SubElement(lists[name], name, attributes)
        elem.text = ""
        for txt in txts:
            if isinstance(txt, bs4.element.Tag):
                elem.append(ET.fromstring(str(txt)))
            else:
                elem.text += remove_medite_annotations(txt)

    def metamark(function: str, target: str):
        """creates a metamark"""
        return z1.soup.new_tag("metamark", function=function, target=target)








    def append_tag(tag, zp):
        logger.debug(f"appending {tag=} on {zp}")
        zp.append(tag)

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

    for key in set(z1_moved_blocks).difference(z2_moved_blocks):
        # r_block = next((k for k in res.deltas if isinstance(k,R) if z2.txt[k.b_start:k.b_end]==key))
        # z2_moved_block[key] =
        # breakpoint()
        pass
    for key in set(z2_moved_blocks).difference(z1_moved_blocks):
        pass

        # breakpoint()
    # we verify that for every moved block in z1 there is a coresponding block in z2
    # currently not active as the TODO above is not implemented
    # assert set(z1_moved_blocks) == set(z2_moved_blocks)
    # TODO rename to original_text_append
    def append_text(tag, start: int, end: int):
        """add text to new xml body, add paragraph and pb tags if necessary"""
        # character range can cross several paragraphs
        for i, P in enumerate(zip_paragraphs(start=start, end=end)):
            id, paragraph, txt = P
            # we retrieve the paragraph from the interval using data
            zp = paragraph.data
            # we remove the existing in the paragraph if it has not been done alreadyy so we can reconstruct it
            reset_paragraph(id=id, zp=zp)
            # we add the tag if it's the first paragraph from the range
            if i == 0:
                append_tag(tag=tag, zp=zp)
            logger.debug(f"appending {txt=} on {zp}")
            # we add the paragraph to the xml
            paragraph_stack.append(zp)
            # breakpoint()
            # and add the text to the paragraph
            assert isinstance(txt, list)
            for k in txt:

                zp.append(k)

    # we need to keep track of the moves

    txt2delta = {z1.txt[k.start : k.end]: k for k in res.deltas if isinstance(k, DA)}

    # let's go through the deltas
    for i, z in enumerate(res.deltas):
        # each type of change requires a different handling
        if isinstance(z, BC):
            logger.debug("BLOC COMMUN".center(120, "$"))
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
        
            tag = z1.soup.new_tag(
                "anchor", **{"xml:id": id_v1, "corresp": id_v2, "function": "bc"}
            )
            z1.changes.insertions.append(op.Insertion(start=z.a_start, text=str(tag)))
            #append_text(tag=tag, start=z.a_start, end=z.a_end)
        elif isinstance(z, S):
            logger.debug("SUPPRESION".center(120, "$"))
            target_id = f"v1_{z.start}_{z.end}"
            tag = metamark(function="del", target=target_id)
            breakpoint()
            z1.changes.insertions.append(op.Insertion(start=z.start, text=str(tag)))
            txt = z1.txt[z.start : z.end]
            breakpoint()
            if txt.strip() == "":
                add_list(
                    z=z1,
                    start=z.start,
                    end=z.end,
                    attributes={"type": "paragraphe", "corresp": target_id},
                    name="deletion",
                )
            else:
                add_list(
                    z=z1,
                    start=z.start,
                    end=z.end,
                    attributes={"corresp": target_id},
                    name="deletion",
                )

        elif isinstance(z, I):
            logger.debug("INSERTION".center(120, "$"))
            target_id = f"v2_{z.start}_{z.end}"
            tag = metamark(function="add", target=target_id)
            z1.changes.insertions.append(op.Insertion(start=z.start, text=str(tag)))
            # breakpoint()
            # current_paragraph = paragraph_stack[-1]
            # reset_paragraph(id=current_paragraph["id"], zp=current_paragraph)
            # append_tag(tag=tag, zp=current_paragraph)
            # breakpoint()
            add_list(
                z=z2,
                start=z.start,
                end=z.end,
                attributes=dict(corresp=target_id),
                name="addition",
            )

        elif isinstance(z, DA):
            logger.debug("MOVE A".center(120, "$"))
            breakpoint()
            key = z1.txt[z.start : z.end]
            # we retrieve the corresponding block in the second text
            # special case when a moved block is part of a replacement
            # TODO hanlde case propery
            if key not in z2_moved_blocks:
                continue
            z_ = z2_moved_blocks[key]
            id_v1 = f"v1_{z.start}_{z.end}"
            id_v2 = f"v2_{z_.start}_{z_.end}"
            tag = z1.soup.new_tag(
                "metamark", function="trans", target=id_v1, corresp=id_v2
            )
            append_text(tag=tag, start=z.start, end=z.end)
            # add_list(
            #     txt=key, attributes=dict(target=id_v1, corresp=id_v2), name="transpose"
            # )
            add_list(
                z=z1,
                start=z.start,
                end=z.end,
                attributes=dict(target=id_v1, corresp=id_v2),
                name="transpose",
            )
        elif isinstance(z, DB):
            logger.debug("MOVE B".center(120, "$"))
            breakpoint()
            # we retrieve the reference to the moved fragment
            txt = z2.txt[z.start : z.end]
            assert txt in txt2delta, f"Cannot find a delta matching with {txt=}"
            z_ = txt2delta[txt]
            id_v1 = f"v1_{z_.start}_{z_.end}"
            current_paragraph = paragraph_stack[-1]
            tag = metamark(function="trans", target=id_v1)
            # not sure we have to do it
            # reset_paragraph(id=current_paragraph["id"], zp=current_paragraph)
            append_tag(tag=tag, zp=current_paragraph)
        elif isinstance(z, R):
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
            tag = z1.soup.new_tag(
                "metamark", function="subst", target=id_v1, corresp=id_v2
            )
            breakpoint()
            append_text(tag=tag, start=z.a_start, end=z.a_end)
            add_list(
                z=z2,
                start=z.b_start,
                end=z.b_end,
                attributes=dict(target=id_v1, corresp=id_v2),
                name="substitution",
            )
        else:
            raise NotImplementedError(f"Element of type {z} is not supported")
    #breakpoint()
    # let's do some cleanups
    # for element in z1.soup.find_all():
    #     if "id" in element.attrs and element["id"].startswith("#"):
    #         del element["id"]
    # # post processing
    # remove newline
    # remove_newline_annotation(z1.soup.find("body"))

    txt_raw = op.medite2xml(z1.changes)
    root.append(ET.fromstring(txt_raw))
    tree = ET.ElementTree(root)
    tree.write(output_filepath, encoding="utf-8", xml_declaration=True, method="xml")

    xml_str = ET.tostring(root, encoding="unicode")

    # Pretty print using lxml
    parser = etree.XMLParser(remove_blank_text=True)
    xml_tree = etree.fromstring(xml_str, parser)
    pretty_xml_str = etree.tostring(xml_tree, pretty_print=True, encoding="unicode")

    processing_instruction = '<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0" ?>\n'
    pretty_xml_str = add_emph_tags(processing_instruction + pretty_xml_str.lstrip())
    # Write to file

    logger.info(f"Write output to {str(output_filepath)}")
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(pretty_xml_str)
    return
    breakpoint()

    # we verfiy the old and the new xml gives the same original text
    x2 = [str(k) for k in to_xml_flat(output_filepath)]
    x1 = [str(k) for k in to_xml_flat(source_filepath)]

    x12 = [(k, v) for k, v in itertools.zip_longest(x1, x2)]
    import pandas as pd

    dfx = pd.DataFrame(x12, columns=["x1", "x2"])
    dfx.to_csv("flat.csv")
    # we only select the rows where the text is different
    df = dfx[dfx["x1"] != dfx["x2"]]
    strict = False
    for x in df.itertuples():
        result = testfixtures.compare(
            x.x1, x.x2, x_label="original text", y_label="processed text", raises=strict
        )
        if result:
            logger.warn("original xml has changed\n{result}\n")
    # TODO add strict parameters that stops the process if inconssiencies are found
    testfixtures.compare(
        x1, x2, x_label="original text", y_label="processed text", raises=strict
    )


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
