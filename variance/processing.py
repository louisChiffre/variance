import pathlib
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

def xml2txt(filepath:pathlib.Path):
    xml_content = filepath.read_text(encoding='utf-8')
    # Parse the XML content using BeautifulSoup
    soup = BeautifulSoup(xml_content, 'xml')
    
    # Find all <p> elements
    def gen():
        p_elements = soup.find_all('p')
        for p in p_elements:
            for content in p.contents:
                if content.name == 'emph':
                    yield ' '.join([f'/{k}/' for k in content.get_text().split(' ')])
                elif isinstance(content, str):
                    yield content
                elif content.name is None and content.string:
                    yield content.string
            yield """'|""" + '\n'
    txts = list(gen())
    breakpoint()
# def xml2txt(filepath:pathlib.Path):
#     # Define the namespace
#     ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

#     # Parse the XML file
#     tree = ET.parse(filepath)
#     root = tree.getroot()

#     # Find all <p> elements within the specified namespace
#     p_elements = root.findall('.//tei:p', ns)

#     # Extract and print the text from each <p> element
#     for p in p_elements:
#         print(p.text)
#     breakpoint()
