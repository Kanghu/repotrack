from pydriller import ModificationType

Extensions = [".java", ".html", ".css", ".js", ".xml", ".properties", ".gitignore"]
Stats = ["LOC+", "LOC-", "FUNC+", "FUNC-", "COM+", "COM-", "FUNC*"] + [('LOC+' + x) for x in Extensions] + [ModificationType.ADD.__repr__(), ModificationType.RENAME.__repr__(), ModificationType.DELETE.__repr__(), ModificationType.MODIFY.__repr__()]
Ignore = [".idea"]

CommentsRegExp = {
    '.java': '(?://[^\n]*|/\*(?:(?!\*/).)*\*/)',
    '.html': '<!--(.*?)-->',
    '.css': '(?://[^\n]*|/\*(?:(?!\*/).)*\*/)',
    '.js': '(?:/\*(?:(?!\*/).)*\*/)'
}
