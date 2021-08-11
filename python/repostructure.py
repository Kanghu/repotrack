import re;
import json;
import datetime;
import pytz

# pyDriller dependencies
from pydriller import GitRepository;
from pydriller import RepositoryMining;
from pydriller import ModificationType;
from pydriller import ModificationType;

# Configuration import
from config import Extensions, Stats, CommentsRegExp, Ignore, Backend, Frontend, Configs

# Ease access to pytz' UTC converter
utc = pytz.UTC

# Compares two method lists and returns a tuple T(#methods_added, #methods_removed)
# where 'methods_added' represents the set of methods present within the second list but not within the first
# and 'methods_removed' represents the set of methods present within the first list but not within the second
def compare_method_list(before, after):
    added, removed = 0, 0
    for func in before:
        if func not in after:
            removed += 1

    for func in after:
        if func not in before:
            added += 1

    return (added, removed)

# The contributor essentially captures all metrics ('contrib') attained by a 
# specific developer (as identified by 'name') within a node of the repository 
# (file or package). 
class Contributor:

    # Contributor constructor. A contributor is initialized through a specified name
    # and hashmap of contributions (usually set as empty)
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

    # Add another contributor's statistics to the current contributor
    def add_contributor(self, contributor):
        for stat in Stats:
            self.contrib[stat] += contributor.contrib[stat]
            self.contrib_recent[stat] += contributor.contrib_recent[stat]

    # Update this contributor's metrics according to a modification authored by it.
    # We maintain a separate contribution map for the past 'recent_months' (set by default to 6).
    def add_modification(self, modif, commit, recent_months=6):
        isRecent = commit.author_date > utc.localize(datetime.datetime.now() - datetime.timedelta(days=recent_months * 30))
        if isRecent:
            self.extract_metrics(modif, self.contrib_recent)

        self.extract_metrics(modif, self.contrib)

    # Extract metrics from a given pydriller Modification object. The method assumes the modification's author
    # to be the current contributor
    def extract_metrics(self, modif, contribution_map):
        # Lines of code added/removed (LOC +/-)
        contribution_map["LOC+"] += modif.added
        contribution_map["LOC-"] += modif.removed
        # Number of methods added/removed (FUNC +/-)
        contribution_map["FUNC+"] += compare_method_list(modif.methods_before, modif.methods)[0]
        contribution_map["FUNC-"] += compare_method_list(modif.methods_before, modif.methods)[1]
        # Number of methods changed (FUNC*)
        contribution_map["FUNC*"] += len(modif.changed_methods)
        # Number of contributions of the current type (ModificationType)
        contribution_map[modif.change_type.__repr__()] += 1
        # Lines of code added/removed for each type of found extension (LOC.ext +/-)
        ext = modif.filename[modif.filename.find('.') if modif.filename.find('.') > 0 else 0 : len(modif.filename)]
        if ext not in contribution_map: 
            contribution_map["LOC+" + ext] = 0
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
    def to_JSON(self):
        return json.dumps(self.__dict__)

# Files represent leaf nodes within our tree repository. These are the only nodes that are "properly" affected
# by modifications. Packages recursively infer their associated contributors by parsing all child leaf nodes.
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

    # Add a Contributor object to this file's known contributor list
    def add_contributor(self, contrib):
        self.contributors[contrib.name] = contrib

    # Returns a JSON stringified version of itself
    def to_JSON(self):
        jsonStr = '{'
        jsonStr += '\"name\"' + ':' + '\"' + self.name + '\",'

        jsonStr += '\"contributors\"' + ':' + '['   
        i = 0
        for c in self.contributors:
            jsonStr += self.contributors[c].to_JSON() 
            if i != len(self.contributors) - 1:
                jsonStr += ','
            i += 1

        jsonStr += ']'
        jsonStr += '}'

        return jsonStr

# Packages represent non-leaf nodes within our tree repository. 
class Package:
    def __init__(self, name, contributors, childs):
        self.contributors = contributors
        self.childs = childs
        self.name = name

    # Returns a direct child of this package, as identified by name
    def get_child_by_name(self, name):
        for ch in self.childs:
            if ch.name == name:
                return ch

    # Return a child of this package, as identified by the relative path from this package
    def get_child_by_path(self, path):
        parts = path.split("\\")

        root = self
        for p in parts[0 : len(parts) - 1]:
            root = root.get_child_by_name(p)

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
                if root.get_child_by_name(p) is not None:
                    root = root.get_child_by_name(p)
                else:
                    raise ValueError("\nRoot is none: " + modif.new_path )

        if type(root) is File:
            root.add_modification(modif, commit)
        else:
            raise ValueError(parts[len(parts) - 1] + " not found in- " + modif.new_path)

    # Get a list containing the names of all direct children 
    def get_child_names(self):
        return [cn.name for cn in self.childs]

    # Add a file identified by 'filename' within this package hierarchy
    # The child will be added in the appropriate location as specified by the filename.
    # e.g. 'usr/loc/file.txt' will parse nodes 'usr', 'loc' and then create the file
    # If a module within the filename cannot be found, it will be automatically created
    def add_child(self, filename):
        parts = filename.split("\\")
        
        if(len(parts) == 1):
            # Leaf part => File
            self.childs.append(File(parts[0], {}))
        else:
            # Not leaf => Package
            package = parts[0]
            check = [cn for cn in self.get_child_names() if package == cn]

            if(len(check) > 0):
                # Corresponding package has been found
                for c in self.childs:
                    if c.name == package:
                        c.add_child(filename[filename.find("\\")+1 : len(filename)])
            else:
                # Package not found => create it instead
                child = Package(package, {}, [])
                child.add_child(filename[filename.find("\\")+1 : len(filename)])

                self.childs.append(child)

    # Add a child file object to this node.
    # The child will be added in the appropriate location as specified by the filename.
    # e.g. 'usr/loc/file.txt' will parse nodes 'usr', 'loc' and then create the file
    # If a module within the filename cannot be found, it will be automatically created
    def add_child_file(self, filename, file):
        parts = filename.split("\\")
        
        if(len(parts) == 1):
            # Leaf part => File
            self.childs.append(file)
        else:
            # Not leaf => Package
            package = parts[0]
            check = [cn for cn in self.get_child_names() if package == cn]

            if(len(check) > 0):
                # Corresponding package has been found
                for c in self.childs:
                    if c.name == package:
                        c.add_child(filename[filename.find("\\")+1 : len(filename)])
            else:
                # Package not found => create it instead
                child = Package(package, {}, [])
                child.add_child(filename[filename.find("\\")+1 : len(filename)])

                self.childs.append(child)

    # Remove a file identified by 'filename' from this package hierarchy
    def remove_child(self, filename):
        parts = filename.split("\\")

        root = self
        for p in parts[0 : len(parts) - 1]:
            root = root.get_child_by_name(p)

        if root is not None:
            for c in root.childs:
                if c.name == parts[len(parts) - 1]:
                    root.childs.remove(c)
        else:
            # raise ValueError("Removal failed due to null root")
            return

    # Recursively check for and remove empty folders
    def remove_empty_folders(self):
        if len(self.childs) == 0:
            return True
        else:
            removed = []
            for ch in self.childs:
                if type(ch) is Package:
                    if ch.remove_empty_folders():
                        removed += [ch]
            
            for ch in removed:
                self.childs.remove(ch)

            if len(self.childs) == 0:
                return True

        return False

    # Move a child of this node elsewhere within this package
    def rename_child(self, old_path, new_path):
        child = self.get_child_by_path(old_path)
        self.add_child(new_path)

        # Re-add the file's contribution
        if child is not None:
            for c in child.contributors.values():
                self.get_child_by_path(new_path).add_contributor(c)

        # Remove reference to old path
        self.remove_child(old_path)

    # Infer the state of this package recursively from its child nodes
    def infer_state(self):
        for c in self.childs:
            if(type(c) is Package):
                c.infer_state()

            for con in c.contributors:
                if(con not in self.contributors):
                    self.contributors[con] = Contributor(con, {})
                self.contributors[con].add_contributor(c.contributors[con])

    # Compute weighted contributions amongst the current repository
    def compute_contributions(self):
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
    def compute_roles(self):
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

    def to_JSON(self):
        # Start of JSON object
        jsonStr = '{'
        jsonStr += '\"name\"' + ':' + '\"' + self.name + '\",'

        # JSON stringify contributors
        jsonStr += '\"contributors\"' + ':' + '['   
        i = 0
        for c in self.contributors:
            jsonStr += self.contributors[c].to_JSON() 
            if i != len(self.contributors) - 1:
                jsonStr += ','
            i += 1
        jsonStr += '],'

        # JSON stringify children recursively
        jsonStr += '\"children\"' + ':' + '['   
        for i in range(0, len(self.childs)):
            jsonStr += self.childs[i].to_JSON() 
            if i != len(self.childs) - 1:
                jsonStr += ','
            i += 1
        jsonStr += ']'
        # End of JSON object
        jsonStr += '}'

        # Format the resulting string appropriately
        dump = json.loads(jsonStr)
        return json.dumps(dump, indent=4)

# Wrapper for a proper repository project. Includes utility methods for processing git repositories
class Repository(Package):

    # Process a git repository from a given location (URL / local file)
    # Additional arguments specify the branch and timeframe of interest
    # If a branch is not given, the main one will be taken as default
    def process_repository(self, loc, branch=None, recent_months=6):
        if branch is None:
            self.process_commits(RepositoryMining(loc).traverse_commits(), only_in_main_branch=True)
        else:
            self.process_commits(RepositoryMining(loc, only_in_branch=branch).traverse_commits())

    # Process a given list of commits into a fully fledged Repository object
    def process_commits(self, commits, only_in_main_branch=False):
        for commit in commits:
            if only_in_main_branch == True and commit.in_main_branch == False:
                continue

            print("Processing commit " + commit.hash)
            for modif in commit.modifications:
                self.process_modif(modif, commit)

    # Process a single modification by collecting all its associated contributions & updating
    # the project's structure accordingly (e.g. structural changes such as file addition or deletion)
    def process_modif(self, modif, commit):
         old_path = modif.old_path
         path = modif.new_path
         change = modif.change_type

         if change is ModificationType.ADD:
             self.add_child(path)
             self.add_modification(modif, commit)
         elif change is ModificationType.DELETE:
             self.remove_child(modif.old_path)
         elif change is ModificationType.MODIFY:
             if self.get_child_by_path(path) is not None:
                 self.add_modification(modif, commit)
         elif change is ModificationType.RENAME:
            self.rename_child(old_path, path)
