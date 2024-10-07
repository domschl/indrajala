# Requires `npm install -g jsdoc` 
jsdoc js_indrajala/indralib/scripts/ -d docs/jsdoc -r
# Requires `pip install sphinx`
make -C docs/pydoc -f Makefile html
# Swift docc seems broken with Swift 6...
