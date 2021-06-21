import re;
import json;
import datetime;
import pytz

# pyDriller dependencies
from pydriller import GitRepository;
from pydriller import RepositoryMining;
from pydriller import ModificationType;

from Config import Extensions, Stats, CommentsRegExp, Ignore, Backend, Frontend, Configs
from pydriller import ModificationType;

# Ease access to pytz' UTC converter
utc = pytz.UTC

# Compares two method lists and returns a tuple T(#methods_added, #methods_removed)
def compareMethodList(before, after):
    added, removed = 0, 0
    for func in before:
        if func not in after:
            removed += 1

    for func in after:
        if func not in before:
            added += 1

    return (added, removed)

class Method:
    def __init__(self, name):
        pass

# A contributor is represented by a name and dictionary of metrics
class Contributor:
    # Contributor constructor
    def __init__(self, name, contrib):
        self.contrib = contrib
        self.contrib_recent = {}
        self.name = name
        self.init_stats()

    # Initialize the dictionary of metrics according to configuration
    def init_stats(self):
        for stat in Stats:
            if stat not in self.contrib:
                self.contrib[stat] = 0
            if stat not in self.contrib_recent:
                self.contrib_recent[stat] = 0

    # Initialize a new type of metric in the contribution dictionary
    def init_metric(self, metric_name):
        self.contrib[metric_name] = 0

    # Add another contributor's statistics to self contribution
    def add_contributor(self, contributor):
        for stat in Stats:
            self.contrib[stat] += contributor.contrib[stat]
            self.contrib_recent[stat] += contributor.contrib_recent[stat]

    # Update this contributor's metrics according to a modification authored by it.
    # We maintain a separate contribution map for the past 'recent_months'.
    def add_modification(self, modif, commit, recent_months=6):
        isRecent = commit.author_date > utc.localize(datetime.datetime.now() - datetime.timedelta(days=recent_months * 30))
        if isRecent:
            self.extract_metrics(modif, self.contrib_recent)

        self.extract_metrics(modif, self.contrib)

    def extract_metrics(self, modif, contribution_map):
        # Lines of code added/removed (LOC +/-)
        contribution_map["LOC+"] += modif.added
        contribution_map["LOC-"] += modif.removed
        # Number of methods added/removed (FUNC +/-)
        contribution_map["FUNC+"] += compareMethodList(modif.methods_before, modif.methods)[0]
        contribution_map["FUNC-"] += compareMethodList(modif.methods_before, modif.methods)[1]
        # Number of methods changed (FUNC*)
        contribution_map["FUNC*"] += len(modif.changed_methods)
        # Number of contributions of the current type (ModificationType)
        contribution_map[modif.change_type.__repr__()] += 1
        # Lines of code added/removed for each type of found extension (LOC.ext +/-)
        ext = modif.filename[modif.filename.find('.') if modif.filename.find('.') > 0 else 0 : len(modif.filename)]
        if ext not in contribution_map: 
            self.init_metric("LOC+" + ext)
        contribution_map["LOC+" + ext] += modif.added
        # Lines of comments added/removed (COM +/-)
        # Extract the nr. of comments according to the file's extension and predefined regexp
        comments_before, comments_after, nr_comments_before, nr_comments_after = 0, 0, 0, 0
        for ext in CommentsRegExp.keys():
            if modif.filename.endswith(ext):
                comments_before = re.findall(r'{}'.format(CommentsRegExp[ext]), modif.source_code_before, re.DOTALL) if modif.source_code_before is not None else []
                comments_after = re.findall(r'{}'.format(CommentsRegExp[ext]), modif.source_code, re.DOTALL) if modif.source_code is not None else []
                nr_comments_before = sum(map(lambda com: len(com), comments_before))
                nr_comments_after = sum(map(lambda com: len(com), comments_after))

        contribution_map["COM+"] += (nr_comments_after - nr_comments_before) if (nr_comments_after - nr_comments_before) > 0 else 0
        contribution_map["COM-"] += (nr_comments_before - nr_comments_after) if (nr_comments_before - nr_comments_after) > 0 else 0

        ###### Possible extensions ######
        # a) Bugfixes 
        # We need to identify commits which have caused bugs 
        # (..requires another approach such as ML, commit message mining, etc.)

        # b) Language specific constructs
        # e.g classes created, class restructuring, method signature restructuring

    # Return a JSON stringified representation of this object
    def toJSON(self):
        return json.dumps(self.__dict__)

# Files represent leaf nodes within our tree repository. These are the only nodes that are properly affected
# by modifications. (Whereas packages recursively infer their state from child nodes)
class File:
    def __init__(self, name, contributors):
        self.contributors = contributors
        self.name = name
        self.contributors["All"] = Contributor("All", {})

    # Add contributions from a modification that has affected this file
    def add_modification(self, modif, commit):
        if(commit.author.name not in self.contributors):
            self.contributors[commit.author.name] = Contributor(commit.author.name, {})
        
        self.contributors[commit.author.name].add_modification(modif, commit)
        self.contributors['All'].add_modification(modif, commit)

    # Add a Contributor object to this file's contributor list
    def add_contributor(self, contrib):
        self.contributors[contrib.name] = contrib

    # Returns a JSON stringified version of itself
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

    # Returns a direct child of this package, as identified by name
    def getChildByName(self, name):
        for ch in self.childs:
            if ch.name == name:
                return ch

    # Return a child of this package, as identified by the relative path from this package
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

    # Add a modification to this package (affected file will be found recursively)
    def add_modification(self, modif, commit):
        parts = modif.new_path.split("\\")

        root = self
        for p in parts:
            if root is not None:
                if root.getChildByName(p) is not None:
                    root = root.getChildByName(p)
                else:
                    raise ValueError("\nRoot is none: " + modif.new_path )

        if type(root) is File:
            root.add_modification(modif, commit)
        else:
            raise ValueError(parts[len(parts) - 1] + " not found in- " + modif.new_path)

    # Get a list containing the names of all direct children 
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
            raise ValueError("Removal failed due to null root")

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
                self.getChildByPath(new_path).add_contributor(c)

        # Remove reference to old path
        self.removeChild(old_path)

    # Infer the state of this package recursively
    def infer_state(self):
        for c in self.childs:
            if(type(c) is Package):
                c.infer_state()

            for con in c.contributors:
                if(con not in self.contributors):
                    self.contributors[con] = Contributor(con, {})
                self.contributors[con].add_contributor(c.contributors[con])

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
    # following roles: [developer (FwD), maintainer (Re), manager]
    def computeRoles(self):
        # Totals across the project
        totals = [1] * 3

        for con in self.contributors.keys():
            if con != 'All':
                totals[0] += self.contributors[con].contrib['LOC+'] + self.contributors[con].contrib['FUNC+']
                totals[1] += self.contributors[con].contrib['FUNC*'] + self.contributors[con].contrib['FUNC-']
                totals[2] += self.contributors[con].contrib['COM+'] + sum(list(map(lambda ext: self.contributors[con].contrib[ext], list(filter(lambda ext: ext in Configs, self.contributors[con].contrib.keys())))))

        result = {}
        for con in self.contributors.keys():
            if con != 'All':
                result[con] = []
                result[con].append((self.contributors[con].contrib['LOC+'] + self.contributors[con].contrib['FUNC+']) / totals[0] * 100)
                result[con].append((self.contributors[con].contrib['FUNC*'] + self.contributors[con].contrib['FUNC-']) / totals[1] * 100)
                result[con].append((self.contributors[con].contrib['COM+'] + sum(list(map(lambda ext: self.contributors[con].contrib[ext], list(filter(lambda ext: ext in Configs, self.contributors[con].contrib.keys())))))) / totals[2] * 100)
        
        # Append result to contribution graph
        for con in self.contributors.keys():
            if con != 'All':
                self.contributors[con].contrib['Engineering'] = result[con][0]
                self.contributors[con].contrib['Re-engineering'] = result[con][1]
                self.contributors[con].contrib['Management'] = result[con][2]

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

# Wrapper for a repository. Includes utility methods for processing git repositories
class Repository(Package):
    # Process a git repository from a given location (URL / local file)
    def process_repository(self, loc, branch='master', recent_months=6):
        self.process_commits(RepositoryMining(loc, only_in_branch=branch).traverse_commits())

    # Process a given list of commits into a contributory repository
    def process_commits(self, commits, recent_months=6):
        for commit in commits:
            # For now we only analyze commits in the main branch
            if commit.in_main_branch:
                for modif in commit.modifications:
                    self.process_modif(modif, commit)

    # Process a single modification by collecting contributions & updating tree structure
    def process_modif(self, modif, commit):
         old_path = modif.old_path
         path = modif.new_path
         change = modif.change_type

         if change is ModificationType.ADD:
             self.addChild(path)
             self.add_modification(modif, commit)
             print("\n Added " + modif.new_path)
         elif change is ModificationType.DELETE:
             self.removeChild(modif.old_path)
             print("\n Deleted " + modif.old_path)
         elif change is ModificationType.MODIFY:
             if self.getChildByPath(path) is None:
                 print("Not found.. " + path)
             else:
                 print("\n Modified " + modif.new_path)
                 self.add_modification(modif, commit)
         elif change is ModificationType.RENAME:
            self.renameChild(old_path, path)
            print("\n +++Renamed " + modif.old_path + " to " + modif.new_path)
