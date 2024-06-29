import pathlib
import xml.etree.ElementTree as ET
from testfixtures import compare

from bs4 import BeautifulSoup
from collections import namedtuple
from variance.medite import medite as md
from lxml import etree
from intervaltree import Interval, IntervalTree
from variance.medite.utils import pretty_print
import re


namespaces = {"": "http://www.tei-c.org/ns/1.0"}
# Register namespaces
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

escape_characters_mapping = {
    "…": "'…",
    #".": "'.",
    "»": "'»",
    "«": "«'",
}
newline = """'|""" + "\n"


def read(filepath: pathlib.Path):
    xml_content = filepath.read_text(encoding="utf-8")
    soup = BeautifulSoup(xml_content, "xml")
    return soup


def remove_emph_tags(txt: str):
    return " ".join([f"/{k}/" for k in txt.split(" ")])


def add_emph_tags(txt: str):
    blocks = re.findall(r"((?:/\w+/ )+)", txt)
    # Replace each block with the <emph> tag
    for block in blocks:
        words = re.findall(r"/(\w+)/", block)
        emph_text = "<emph>" + " ".join(words) + "</emph>"
        txt = txt.replace(block, emph_text + " ")

    # Ensure that any remaining words surrounded by / are handled
    txt = re.sub(r"/(\w+)/", r"<emph>\1</emph>", txt)

    # Correct any multiple spaces and leading/trailing spaces
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def add_escape_characters(txt: str):
    for a, b in escape_characters_mapping.items():
        txt = txt.replace(a, b)
    return txt


def remove_medit_annotations(txt: str):
    # remove escape characters
    for b, a in escape_characters_mapping.items():
        txt = txt.replace(a, b)
    # remplace new line
    return txt.replace(newline, "")


Output = namedtuple("Output", "id txt soup path tree")


def xml2txt(filepath: pathlib.Path) -> Output:
    """extract text from xml and apply pre-processing step to text"""
    soup = read(filepath=filepath)

    doc = {}
    tree = IntervalTree()
    # Find all <p> elements
    body = soup.find("body")

    # Add unique IDs to each element
    for i, element in enumerate(soup.find_all('p')):
        element["id"] = f"#{i}"
    esc = add_escape_characters
    def gen():
        cursor = 0
        for div in body.find_all("div"):
            p_elements = div.find_all("p")
            for p in p_elements:

                def gen_p():
                    for content in p.contents:
                        if content.name == "emph":
                            yield remove_emph_tags(content.get_text())
                        elif isinstance(content, str):
                            yield content
                        elif content.name is None and content.string:
                            yield content.string
                    #yield newline

                #txt = "".join([add_escape_characters(k) for k in gen_p()])
                txt_ = "".join(gen_p())
                txt = esc(txt_)
                txt = txt + newline
                #compare(txt_ + newline, txt)
                old_cursor, cursor = cursor, cursor + len(txt)
                tree[old_cursor:cursor] = p
                yield txt

    txts = list(gen())
    txt = "".join(txts)
    filepath.with_suffix(".txt").write_text(txt, encoding="utf-8")

    ps = [k.data for k in sorted(tree, key=lambda x: x.begin)]
    ps_ = txt.split(newline)
    print("\n")
    for h, t in zip(ps, ps_):
        print("paragraph".center(80, "*"))
        print(h.string)
        print("txt".center(80, "*"))
        print(t)
        print("*" * 64)
        print("\n\n")

    # for it, txt_ in zip(sorted(tree,key=lambda x:x.begin),ps_):
    # breakpoint()

    n_p = len(tree)
    n_p_ = len(txt.split(newline)[:-1])
    assert n_p == n_p_

    return Output(
        id=soup.find("TEI")["xml:id"], txt=txt, soup=soup, tree=tree, path=filepath
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

    def t2n(x):
        return [Block(*k) for k in x]

    appli = md.DiffTexts(chaine1=z1.txt, chaine2=z2.txt, parameters=parameters)
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
            case (None, ("D", start, end, [])):
                return DB(start - N, end - N)
            case (("D", start, end, []), None):
                return DA(start, end)
            case _:
                assert False

    deltas = [handle(k) for k in appli.bbl.liste]
    return Result(appli=appli, deltas=deltas)


def process(
    source_filepath: pathlib.Path,
    target_filepath: pathlib.Path,
    parameters: md.Parameters,
    output_filepath: pathlib.Path,
):
    z1 = xml2txt(source_filepath)
    z2 = xml2txt(target_filepath)

    # let's generte the xml
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

    def add_list(txt, attributes, name):
        list_elem = lists[name]
        elem = ET.SubElement(lists[name], name, attributes)
        if txt:
            elem.text = txt

    res = calc_revisions(z1=z1, z2=z2, parameters=parameters)
    updated = set()

    def metamark(function: str, target: str):
        return z1.soup.new_tag("metamark", function=function, target=target)

    def zip_paragraphs(start: int, end: int):
        txt = z1.txt[start:end]
        para_txts = [k for k in txt.split(newline)]
        para_htms = sorted(z1.tree[start:end], key=lambda x: x.begin)
        ids = [k.data["id"] for k in para_htms]
        assert len(para_htms) > 0
        assert len(para_txts) >= len(para_htms)
        print(f"paragraphs between {start} end {end}".center(80, "#"))
        print(f"text: [{txt}]")
        for i, x in enumerate(zip(para_txts, para_htms)):
            t, h = x
            print(f"paragraph {i}".center(80, "*"))
            print(f"text:\n[{t}]\n------\n")
            print(f"html:\n{h.data}\n------\n")
        print(f"end paragraph".center(80, "#"))


        yield from zip(ids, para_htms, para_txts)

    # we set the current paragraph, this will used when inserting
    paragraph_stack = [sorted(z1.tree, key=lambda x: x.begin)[0].data]

    def reset_paragraph(id, zp):
        print(updated)
        if not id in updated:
            print(f"resetting paragraph \n{zp}\n")
            zp.string = ""
            updated.add(id)

    def append_tag(tag, zp):
        print(f"appending {tag=} on {zp}")
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

    def append_text(tag, start: int, end: int):
        for i, P in enumerate(zip_paragraphs(start=start, end=end)):
            id, paragraph, txt = P
            zp = paragraph.data
            reset_paragraph(id=id, zp=zp)
            # we add the tag if it's the first paragraph
            if i == 0:
                append_tag(tag=tag, zp=zp)
            print(f"appending {txt=} on {zp}")
            paragraph_stack.append(zp)
            zp.append(remove_medit_annotations(txt))

    for z in res.deltas:
        if isinstance(z, BC):
            print("BLOC COMMUN".center(120, "$"))
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
            tag = z1.soup.new_tag(
                "anchor", **{"xml:id": id_v1, "corresp": id_v2, "function": "bc"}
            )
            append_text(tag=tag, start=z.a_start, end=z.a_end)
        elif isinstance(z, S):
            print("SUPPRESION".center(120, "$"))
            target_id = f"v1_{z.start}_{z.end}"
            tag = metamark(function="del", target=target_id)
            append_text(tag=tag, start=z.start, end=z.end)
            txt = z1.txt[z.start : z.end]
            if txt.strip() == "":
                add_list(txt="", attributes={"type": "paragraphe"}, name="deletion")
            else:
                add_list(
                    txt=remove_medit_annotations(txt),
                    attributes=dict(corresp=target_id),
                    name="deletion",
                )

        elif isinstance(z, I):
            print("INSERTION".center(120, "$"))
            target_id = f"v2_{z.start}_{z.end}"
            tag = metamark(function="ins", target=target_id)
            current_paragraph = paragraph_stack[-1]
            reset_paragraph(id=current_paragraph["id"], zp=current_paragraph)
            append_tag(tag=tag, zp=current_paragraph)
            add_list(
                txt=remove_medit_annotations(z2.txt[z.start : z.end]),
                attributes=dict(corresp=target_id),
                name="addition",
            )

        elif isinstance(z, DA):
            print("MOVE A".center(120, "$"))
            key = z1.txt[z.start : z.end]
            # we retrieve the corresponding block in the second text
            z_ = z2_moved_blocks[key]
            id_v1 = f"v1_{z.start}_{z.end}"
            id_v2 = f"v2_{z_.start}_{z_.end}"
            tag = z1.soup.new_tag(
                "metamark", function="trans", target=id_v1, corresp=id_v2
            )
            append_text(tag=tag, start=z.start, end=z.end)
            add_list(
                txt=key, attributes=dict(target=id_v1, corresp=id_v2), name="transpose"
            )
        elif isinstance(z, DB):
            print("MOVE B".center(120, "$"))
            # key = z2.txt[z.start:z.end]

        elif isinstance(z, R):
            id_v1 = f"v1_{z.a_start}_{z.a_end}"
            id_v2 = f"v2_{z.b_start}_{z.b_end}"
            tag = z1.soup.new_tag(
                "metamark", function="rempl", target=id_v1, corresp=id_v2
            )
            append_text(tag=tag, start=z.a_start, end=z.a_end)
            add_list(
                txt=remove_medit_annotations(z2.txt[z.b_start : z.b_end]),
                attributes=dict(target=id_v1, corresp=id_v2),
                name="substitution",
            )
        else:
            raise NotImplementedError(f"Element of type {z} is not supported")

    # remove the ids
    for element in z1.soup.find_all():
        if "id" in element.attrs and element["id"].startswith("#"):
            del element["id"]

    root.append(ET.fromstring(str(z1.soup.find("body"))))
    tree = ET.ElementTree(root)
    tree.write(output_filepath, encoding="utf-8", xml_declaration=True, method="xml")

    xml_str = ET.tostring(root, encoding="unicode")

    # Pretty print using lxml
    parser = etree.XMLParser(remove_blank_text=True)
    xml_tree = etree.fromstring(xml_str, parser)
    pretty_xml_str = etree.tostring(xml_tree, pretty_print=True, encoding="unicode")

    processing_instruction = '<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0" ?>\n'
    pretty_xml_str = processing_instruction + pretty_xml_str.lstrip()
    # Write to file
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(pretty_xml_str)

    # now we verify the original text has not changed
    z = xml2txt(output_filepath)
    compare(z.txt,z1.txt)


