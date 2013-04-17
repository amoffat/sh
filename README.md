# Updating the docs

The doc sources live in `/_docs_sources`.  These are
[reStructeredText files](http://sphinx-doc.org/rest.html#rst-primer) that
compose the final output html after being compiled.

# Building

After editing the `.rst` files, run `python compile_docs.py` and pass in the
sh version number to be embedded in the docs:

    python compile_docs.py 1.08
    
Then commit all of the `.html` files, all `.js` and `.css` files,
and the `_static`, `_docs_sources`, `_sources` directories.

Finally, submit a pull request with your changes.