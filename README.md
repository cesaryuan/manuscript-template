A collection of tools and templates to aid in auto-generating DOCX files using [pandoc](https://pandoc.org). See [this article](https://rnwest.engineer/auto-generate-docx-with-pandoc/) for more information on how to use these tools.

The bundled `reference-doc.docx` and its extracted `reference-doc/` contents must
stay synchronized. DOCX exports use the package; HTML typography reads
`reference-doc/word/styles.xml`.

`Image Caption` and `Table Caption` define the typography of both the primary
caption and its `caption-en` translation. Change these shared reference styles
to adjust reusable typography. Project-level `docxStyle` overrides also apply
to both caption languages in DOCX and HTML.

### Automatically build the reference document on commit

Install [uv](https://docs.astral.sh/uv/) and enable this repository's hook once:

```sh
git config --local core.hooksPath .githooks
```

On Linux/macOS, also run `chmod +x .githooks/pre-commit`. Hooks are local Git
configuration, so enable them again after a fresh clone or submodule checkout.

Every normal `git commit` in **this repository** now rebuilds and stages
`reference-doc.docx` from the **staged** `reference-doc/` files when their package
contents differ. There is no need to run `edit-reference-doc.ps1`, and committing
does not open Word. Unstaged XML edits and untracked files stay out of the
generated document. Unchanged package contents keep their existing DOCX bytes.
Generation failures stop the commit. If rebuilding would overwrite unstaged
DOCX edits, the hook stops: preserve those edits first, using
`apply-reference-doc-edits.ps1` to import edits made in Word when appropriate.
`edit-reference-doc.ps1` remains available for manually building and opening
the working copy in Word.

When used as Papper's submodule, commit here first, then stage and commit
`pandoc/manuscript-template` in Papper to record the updated submodule revision.
Committing only in Papper does not commit changes inside this repository.
`git commit --no-verify` skips the hook.
