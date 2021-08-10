# Standard dependencies
import codecs;
import sys;
import json;

# pyDriller dependencies
from pydriller import GitRepository;
from pydriller import RepositoryMining;
from pydriller import ModificationType;

# Internal data structure
from repostructure import Contributor
from repostructure import File
from repostructure import Package
from repostructure import Repository

# Extension / statistics configuration
from config import Extensions, Stats, CommentsRegExp, Ignore

args = sys.argv
source = 'https://github.com/ishepard/pydriller'
timeframe = 6
branch = None
filename = "report.json"

# Check if there are extra parameters and parse as necessary
if(len(args) > 1):
    i = 1
    while i < len(args):
        if args[i] == '-t':
            timeframe = args[i+1]
            i += 2
        elif args[i] == '-b':
            branch = args[i+1]
            i += 2

# Process the repository using 'Repository' helper methods
repo_name = source.split("\\")[len(source.split("\\")) - 1]
repo = Repository(repo_name, {}, [])        # Root node
repo.process_repository(source, branch, timeframe)     # Process the given repository

repo.infer_state()
repo.remove_empty_folders()
repo.compute_roles()

# Write output to file
fl = open("report_" + repoName + ".json", "w")
fl.write(repo.toJSON()) 
fl.close()