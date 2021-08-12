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

# Default parameters
args = sys.argv
timeframe = None
source = 'https://github.com/ishepard/pydriller'
branch = None
filename = "report.json"

# Check if appropriate parameters are present
if(len(args) > 1):
    # Extract location
    source = args[1]

    # Parse additional arguments
    i = 2
    while i < len(args):
        if args[i] == '-t':
            timeframe = int(args[i+1])
            i += 2
        elif args[i] == '-b':
            branch = args[i+1]
            i += 2
else:
    # No arguments specified => Provide execution information
    print("\nRepotrack may be called as \n\"python repotrack <loc> -t <timeframe> -b <branch>\"")
    print("\nWhere: \n<loc> represents the repositories' location (URL or local directory)")
    print("\n<timeframe> is the number of months for which we consider contributions as recent")
    print("\n<branch> is the branch of interest")
    exit()

# Process the repository using 'Repository' helper methods
repo_name = source.split("/")[len(source.split("/")) - 1]
repo = Repository(repo_name, {}, [])                   # Root node
repo.process_repository(source, branch, timeframe)     # Process the given repository

# Recursively infer the state (metrics) of packages 
repo.infer_state()

# Remove empty folders from the repository 
# (i.e. leftover folders from moving files)
repo.remove_empty_folders()

# (OPTIONAL) Compute aggregate metrics. 
# This is not necessarily required as the 
# frontend aggregates its own values.
repo.compute_roles()

# Write output to file
fl = open("report_" + repo_name + ".json", "w")
fl.write(repo.to_JSON()) 
fl.close()