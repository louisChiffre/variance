# Data processing for web display

XSLT transformation to convert a TEI file with the results of the comparison into 6XHTML files:

- `source.xhtml`: 1st version that is considered to be the source
- `target.xhtml`: 2nd version which is compared to the 1st version
- `s.xhtml`: list the elements that have been deleted in the 2nd version
- `i.xhtml`: list the elements that have been added in the 2nd version
- `r.xhtml`: list the elements that have been substituted in the 2nd version
- `d.xhtml`: list the elements that have been transposed in the 2nd version

## How to run

The script has been tested with both Saxon 11 and 12.

```
java -jar lib/SaxonHE12-5J/saxon-he-12.5.jar -s:SOURCE_FILE_OR DIR -xsl:tei2xhtml.xsl -o:OUTPUT
```

## Documentation

Open in a browser `doc/tei2xhtml.html`.

