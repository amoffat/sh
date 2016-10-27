# Updating the docs

The doc sources live in `/_docs_sources`.  These are
[reStructeredText files](http://sphinx-doc.org/rest.html#rst-primer) that
compose the final output html after being compiled.

# Building

After editing the `.rst` files, run `python compile_docs.py` and pass in the
sh version number to be embedded in the docs:

    python compile_docs.py 1.08

This will allow you to preview your docs before submitting a pull request.
    
# Submitting a PR

When submitting a pull request *only commit the files in `/_docs_sources`*  Do
not commit `.js`, `.css`, `.html`, or any other generated files.  Only the raw
`.rst` files please.  I will then re-generate the regenerated files from the
`.rst` changes.
