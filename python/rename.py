# Configuration file for representing supported file formats, metrics and comment capturing regular expressions
from pydriller import ModificationType

# We classify extensions under these rough categories
Backend = [".java", ".py", ".c", ".cpp", ".cs"]
Frontend = [".html", ".css", ".js"]
Configs = [".xml", ".yaml", ".properties", ".md", ".gitignore"]
Extensions = Backend + Frontend + Configs

# LOC by extension
LOC_by_extension = [('LOC+' + x) for x in Extensions]
modif_types = [ModificationType.ADD.__repr__(), ModificationType.RENAME.__repr__(), ModificationType.DELETE.__repr__(), ModificationType.MODIFY.__repr__()]
Stats = ["LOC+", "LOC-", "FUNC+", "FUNC-", "COM+", "COM-", "FUNC*"] + LOC_by_extension + modif_types
Ignore = [".idea"]

# We define different comment patterns here and assign them appropriately
regex_C_like = '(?://[^\n]*|/\*(?:(?!\*/).)*\*/)'
regex_XML_like = '<!--(.*?)-->'
regex_PY_like = '#[^\n\r]+?(?:\*\)|[\n\r])'

CommentsRegExp = {
    # C-like comments
    '.java': regex_C_like,
    '.cpp': regex_C_like,
    '.cc' : regex_C_like,
    '.cxx' : regex_C_like,
    '.c++' : regex_C_like,
    '.c': regex_C_like,
    '.cs': regex_C_like,
    '.css': regex_C_like,

    # XML-like comments
    '.html': regex_XML_like,
    '.xml' : regex_XML_like,

    # PY-like comments
    '.yaml' : regex_PY_like,
    '.py' : regex_PY_like,

    # JS like comments
    '.js': '(?:/\*(?:(?!\*/).)*\*/)'
}
