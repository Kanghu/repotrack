import codecs;
import sys;
import json;

# pyDriller dependencies
from pydriller import GitRepository;
from pydriller import RepositoryMining;
from pydriller import ModificationType;

# Internal data structure
from RepositoryStructure import Contributor
from RepositoryStructure import File
from RepositoryStructure import Package

# Extension / statistics configuration
from Config import Extensions, Stats, CommentsRegExp, Ignore

# Parse the repository once to generate appropriate file structure
# Tactic: bottom-up (infer from methods => files => packages)
repoName = 'monitoring-dashboard'
loc = 'D:/Users/Kanghu/Github/' + repoName

repo = Package(repoName, {}, [])        # Root package structure
fileNames = []                          # The list of total files currently present in the project
files = {}                              # The list of total files only by filename

gr = GitRepository(loc)
fileNames = list(filter(lambda f: any([True for ext in Extensions if f.endswith(ext)]), gr.files()))
fileNames = list(map(lambda f: f[f.find(repoName) + len(repoName) + 1 : len(f)], fileNames))
files = list(map(lambda f: f[f.rfind("\\")+1 : len(f)], fileNames))

pips=0
for commit in RepositoryMining(loc).traverse_commits():
    # For now we are only interested in the main branch
    if commit.in_main_branch is False:
        continue

    pips += 1

    # if(pips > 2):
    #      break

    # Files flagged for removal
    flagged = []

    print(commit.hash)
    for modif in commit.modifications:
         old_path = modif.old_path
         path = modif.new_path
         change = modif.change_type

         # TO DO: Take into account moving files between packages
         if change is ModificationType.ADD:
             repo.addChild(path)
             repo.addModification(modif, commit)
             print("\n Added " + modif.new_path)
         elif change is ModificationType.DELETE:
             repo.removeChild(modif.old_path)
             print("\n Deleted " + modif.old_path)
         elif change is ModificationType.MODIFY:
             if repo.getChildByPath(path) is None:
                 print("Not found.. " + path)
             else:
                 print("\n Modified " + modif.new_path)
                 repo.addModification(modif, commit)
         elif change is ModificationType.RENAME:
            repo.renameChild(old_path, path)
            print("\n +++Renamed " + modif.old_path + " to " + modif.new_path)

fl = open("report.json", "w")
repo.inferState()

# for f in files:
#     files[f].printSelf(fl)
#     fl.write("\n\n")

# results = repo.computeContributions()
# for x in results.keys():
#     fl.write('\n' + x[0:4] + ' had a contribution of: ')
#     counter = 0
#     for stat in Stats:
#         fl.write(stat + ':' + str(results[x][counter]) + '%' + ' // ')
#         counter += 1

repo.removeEmptyFolders()

repoJs = repo.toJSON()
dump = json.loads(repoJs)

fl.write(json.dumps(dump, indent=4))

# results = repo.getChildByPath("src\\main\\java\\btp\\model").computeContributions()
# fl.write('\n\nWithin package src/main/java/btp/model:')
# for x in results.keys():
#     fl.write('\n' + x + ' was the main contributor in: ')
#     counter = 0
#     for stat in Stats:
#         if(results[x][counter] >= 100 / 7):
#             fl.write(stat + " , ")
#         counter += 1

# repo.printSelf(fl, "")

c = Contributor("haha", {"x":50, "p":26})


fl.close()