A collection of tools and templates to aid in auto-generating DOCX files using [pandoc](https://pandoc.org). See [this article](https://rnwest.engineer/auto-generate-docx-with-pandoc/) for more information on how to use these tools.

The bundled `reference-doc.docx` and its extracted `reference-doc/` contents must
stay synchronized. DOCX exports use the package; HTML typography reads
`reference-doc/word/styles.xml`.

`Image Caption` and `Table Caption` define the typography of both the primary
caption and its `caption-en` translation. Change these shared reference styles
to adjust reusable typography. Project-level `docxStyle` overrides also apply
to both caption languages in DOCX and HTML.
