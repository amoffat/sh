# Updating the docs

The doc sources live in `/_docs_sources`.  These are
[reStructeredText files](http://sphinx-doc.org/rest.html#rst-primer) that
compose the final output html after being compiled.

# Building

Run `python compile_docs.py` and pass in the sh version number to be embedded
in the docs:

    python compile_docs.py 1.08
    
Then commit all of the `.html` files, the `_static` directory, and the 
`_sources` directory.

Finally, submit a pull request with your changes.