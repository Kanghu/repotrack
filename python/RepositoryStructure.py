import re;
import json;

from Config import Extensions, Stats, CommentsRegExp, Ignore

# Compares two method lists and returns a tuple T(#methods_added, #methods_removed)
def compareMethodList(before, after):
    added = 0
    removed = 0

    for func in before:
        if func not in after:
            removed += 1

    for func in after:
        if func not in before:
            added += 1

    return (added, removed)

# A contributor is represented by a dictionary of metrics and their respective values.
class Contributor:
    def __init__(self, name, contrib):
        self.contrib = contrib
        self.name = name
        self.initStats()

    def printContributor(self, f, offset):
        f.write('\n' + offset + self.name + ": ")
        for m in self.contrib.keys():
            f.write(m + ":" + str(self.contrib[m]) + " / ")

    # Initialize statistic dictionary
    def initStats(self):
        for stat in Stats:
            if stat not in self.contrib:
                self.contrib[stat] = 0

    # Add another contributor's statistics to self
    def addContributor(self, contributor):
        for stat in Stats:
            self.contrib[stat] += contributor.contrib[stat]

    # Update this contributor's metrics according to a modification authored by it.
    def addModification(self, modif):
        # Lines of code added/removed
        self.contrib["LOC+"] += modif.added
        self.contrib["LOC-"] += modif.removed
        # Number of methods added/removed
        self.contrib["FUNC+"] += compareMethodList(modif.methods_before, modif.methods)[0]
        self.contrib["FUNC-"] += compareMethodList(modif.methods_before, modif.methods)[1]
        # Number of contributions of this type
        self.contrib[modif.change_type.__repr__()] += 1
        # Lines of code added/removed for each type of relevant extension
        for ext in Extensions:
            if modif.filename.endswith(ext):
                self.contrib["LOC+" + ext] += modif.added
        # Lines of comments added/removed
        comments_before = 0
        comments_after = 0
        nr_comments_before = 0
        nr_comments_after = 0

        for ext in CommentsRegExp.keys():
            if modif.filename.endswith(ext):
                comments_before = re.findall(r'{}'.format(CommentsRegExp[ext]), modif.source_code_before, re.DOTALL) if modif.source_code_before is not None else []
                comments_after = re.findall(r'{}'.format(CommentsRegExp[ext]), modif.source_code, re.DOTALL) if modif.source_code is not None else []
                nr_comments_before = sum(map(lambda com: len(com), comments_before))
                nr_comments_after = sum(map(lambda com: len(com), comments_after))

        self.contrib["COM+"] += (nr_comments_after - nr_comments_before) if (nr_comments_after - nr_comments_before) > 0 else 0
        self.contrib["COM-"] += (nr_comments_before - nr_comments_after) if (nr_comments_before - nr_comments_after) > 0 else 0
        # Set of changed methods
        self.contrib["FUNC*"] += len(modif.changed_methods)

        # a) Bugfixes (?)
        # We need to identify commits which have caused bugs 
        # (..need another approach such as ML, commit message mining)

        # b) Language specific constructs
        # e.g classes created, class restructuring, method signature restructuring

        #
    def toJSON(self):
        return json.dumps(self.__dict__)

class File:
    def __init__(self, name, contributors):
        self.contributors = contributors
        self.name = name
        self.contributors["All"] = Contributor("All", {})

    def addModification(self, modif, commit):
        if(commit.author.name not in self.contributors):
            self.contributors[commit.author.name] = Contributor(commit.author.name, {})
        
        self.contributors[commit.author.name].addModification(modif)
        self.contributors['All'].addContributor(self.contributors[commit.author.name])

    def checkCommit(self, commit):
        for modif in commit.modifications:
            self.addModification(modif)

    def addContributor(self, contrib):
        self.contributors[contrib.name] = contrib

    def printSelf(self, f, offset):
        f.write(offset + " - " + self.name + ' (' + str(len(self.contributors)) + " contributors" + ')')
        for c in self.contributors:
             self.contributors[c].printContributor(f, offset)
        f.write('\n')

    def toJSON(self):
        jsonStr = '{'
        jsonStr += '\"name\"' + ':' + '\"' + self.name + '\",'

        jsonStr += '\"contributors\"' + ':' + '['   
        i = 0
        for c in self.contributors:
            jsonStr += self.contributors[c].toJSON() 
            if i != len(self.contributors) - 1:
                jsonStr += ','
            i += 1

        jsonStr += ']'
        jsonStr += '}'

        return jsonStr
class Package:
    def __init__(self, name, contributors, childs):
        self.contributors = contributors
        self.childs = childs
        self.name = name

    def addModification(self, modif, commit):
        parts = modif.new_path.split("\\")

        root = self
        for p in parts:
            if root is not None:
                if root.getChildByName(p) is not None:
                    root = root.getChildByName(p)
                else:
                    print("\nRoot is none: " + modif.new_path )

        if type(root) is File:
            root.addModification(modif, commit)
        else:
            print(parts[len(parts) - 1] + " not found in- " + modif.new_path)

    def checkCommit(self, commit):
        for modif in commit.modifications:
            self.addModification(modif)

    def getChildByPath(self, path):
        parts = path.split("\\")

        root = self
        for p in parts[0 : len(parts) - 1]:
            root = root.getChildByName(p)

        if root is None:
            return None

        for c in root.childs:
            if c.name == parts[len(parts) - 1]:
                return c
        
        return None

    def getChildByName(self, name):
        for ch in self.childs:
            if ch.name == name:
                return ch

    def getChildNames(self):
        return [cn.name for cn in self.childs]


    # Add a file identified by 'filename' within this package hierarchy
    def addChild(self, filename):
        parts = filename.split("\\")
        
        if(len(parts) == 1):
            # Leaf part => File
            self.childs.append(File(parts[0], {}))

        else:
            # Not leaf => Package
            package = parts[0]
            check = [cn for cn in self.getChildNames() if package == cn]

            if(len(check) > 0):
                # Corresponding package has been found
                for c in self.childs:
                    if c.name == package:
                        c.addChild(filename[filename.find("\\")+1 : len(filename)])
            else:
                # Package not found => create it instead
                child = Package(package, {}, [])
                child.addChild(filename[filename.find("\\")+1 : len(filename)])

                self.childs.append(child)

    def addChildFile(self, filename, file):
        parts = filename.split("\\")
        print(parts)
        
        if(len(parts) == 1):
            # Leaf part => File
            self.childs.append(file)

        else:
            # Not leaf => Package
            package = parts[0]
            check = [cn for cn in self.getChildNames() if package == cn]

            if(len(check) > 0):
                # Corresponding package has been found
                for c in self.childs:
                    if c.name == package:
                        c.addChild(filename[filename.find("\\")+1 : len(filename)])
            else:
                # Package not found => create it instead
                child = Package(package, {}, [])
                child.addChild(filename[filename.find("\\")+1 : len(filename)])

                self.childs.append(child)

    # Remove a file identified by 'filename' from this package hierarchy
    def removeChild(self, filename):
        parts = filename.split("\\")

        root = self
        for p in parts[0 : len(parts) - 1]:
            root = root.getChildByName(p)

        if root is not None:
            for c in root.childs:
                if c.name == parts[len(parts) - 1]:
                    root.childs.remove(c)
        else:
            print("Removal failed")

    # Check and remove folders which are empty (recursively)
    def removeEmptyFolders(self):
        if len(self.childs) == 0:
            return True

        else:
            removed = []
            for ch in self.childs:
                if type(ch) is Package:
                    if ch.removeEmptyFolders():
                        removed += [ch]
            
            for ch in removed:
                self.childs.remove(ch)

            if len(self.childs) == 0:
                return True

        return False

    def renameChild(self, old_path, new_path):
        child = self.getChildByPath(old_path)
        self.addChild(new_path)

        # Re-add the file's contribution
        if child is not None:
            for c in child.contributors.values():
                self.getChildByPath(new_path).addContributor(c)

        # Remove reference to old path
        self.removeChild(old_path)

    # Infer the state of this package recursively
    def inferState(self):
        for c in self.childs:
            if(type(c) is Package):
                c.inferState()

            for con in c.contributors:
                if(con not in self.contributors):
                    self.contributors[con] = Contributor(con, {})
                self.contributors[con].addContributor(c.contributors[con])

    # Compute weighted contributions amongst a repository
    def computeContributions(self):
        totals = []         # Totals across each category
        results = {}        # Final weighted results across each category

        counter = 0
        for stat in Stats:
            # Calculate totals among each statistic
            totals.append(0)
            for c in self.contributors.values():
                totals[counter] += c.contrib[stat]
            counter += 1
        
        counter = 0
        for c in self.contributors.keys():
            # Initialize result dictionary
            results[c] = []

        for stat in Stats:
            # Calculate weights among each stat by division with total
            for c in self.contributors.values():
                results[c.name].append(int(round(c.contrib[stat] / (totals[counter] + 1) * 100)))
            counter += 1

        return results

    # Assigns each contributor a value directly proportional to their involvement in one of the
    # following roles: [developer, maintainer, manager]
    def computeRoles(self):
        totals = [0] * 3
        for con in self.contributors.keys():
            if con != 'All':
                totals[0] += self.contributors[con].contrib['LOC+'] + self.contributors[con].contrib['FUNC+']
                totals[1] += self.contributors[con].contrib['FUNC*'] + self.contributors[con].contrib['FUNC-']
                totals[2] += self.contributors[con].contrib['COM+'] + self.contributors[con].contrib['LOC+.xml']

        result = {}
        for con in self.contributors.keys():
            if con != 'All':
                result[con] = []
                result[con].append((self.contributors[con].contrib['LOC+'] + self.contributors[con].contrib['FUNC+']) / totals[0] * 100)
                result[con].append((self.contributors[con].contrib['FUNC*'] + self.contributors[con].contrib['FUNC-']) / totals[1] * 100)
                result[con].append((self.contributors[con].contrib['COM+'] + self.contributors[con].contrib['LOC+.xml']) / totals[2] * 100)

        return result

    def toJSON(self):
        # Start of JSON object
        jsonStr = '{'
        jsonStr += '\"name\"' + ':' + '\"' + self.name + '\",'

        # JSON stringify contributors
        jsonStr += '\"contributors\"' + ':' + '['   
        i = 0
        for c in self.contributors:
            jsonStr += self.contributors[c].toJSON() 
            if i != len(self.contributors) - 1:
                jsonStr += ','
            i += 1
        jsonStr += '],'

        # JSON stringify children recursively
        jsonStr += '\"children\"' + ':' + '['   
        for i in range(0, len(self.childs)):
            jsonStr += self.childs[i].toJSON() 
            if i != len(self.childs) - 1:
                jsonStr += ','
            i += 1
        jsonStr += ']'
        # End of JSON object
        jsonStr += '}'

        # Format the resulting string appropriately
        dump = json.loads(jsonStr)
        return json.dumps(dump, indent=4)