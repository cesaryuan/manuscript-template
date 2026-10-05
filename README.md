A collection of tools and templates to aid in auto-generating DOCX files using [pandoc](https://pandoc.org). See [this article](https://rnwest.engineer/auto-generate-docx-with-pandoc/) for more information on how to use these tools.

The bundled `reference-doc.docx` and its extracted `reference-doc/` contents must
stay synchronized. DOCX exports use the package; HTML typography reads
`reference-doc/word/styles.xml`.

`Image Caption English` and `Table Caption English` define the typography of
`caption-en` translations. They inherit `Image Caption` and `Table Caption`,
respectively, and set Times New Roman and English language defaults. Change these
reference styles to adjust reusable typography; Papper does not create or repair
their font defaults during DOCX post-processing. Project-level `docxStyle`
overrides can still adjust either named style.
