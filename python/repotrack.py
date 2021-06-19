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
from RepositoryStructure import Repository

# Extension / statistics configuration
from Config import Extensions, Stats, CommentsRegExp, Ignore

# Parse the repository once to generate appropriate file structure
# Tactic: bottom-up (infer from methods => files => packages)
repoName = 'spring-framework'
branch = 'master'
loc = 'https://github.com/spring-projects/' + repoName

repo = Repository(repoName, {}, [])         # Root package structure
repo.process_repository(loc, branch)        # Process the given repository

repo.infer_state()
repo.removeEmptyFolders()
repo.computeRoles()

# Write output to file
fl = open("report_" + repoName + ".json", "w")
fl.write(repo.toJSON()) 
fl.close()