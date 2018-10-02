import os
from os.path import getmtime
from pkg_resources import resource_filename as pkg_file

def pickle_status():
    def is_src_file(f):
        if f.endswith('.py') and (not f.startswith('.#')):
            return True
        else:
            return False
    pyfiles = []
    for curdir, subdirs, files in os.walk('.'):
        for pyfile in filter(is_src_file, files):
            pyfiles.append(os.path.join(curdir, pyfile))
    pickle_dir = pkg_file('gonet', 'data/pickles')
    pickle_files = map(lambda f: os.path.join(pickle_dir, f),
                       filter(lambda f: f.endswith('.pkl'), os.listdir(pickle_dir)))
    pickle_files = list(pickle_files)

    if not pickle_files:
        return 'not found'

    newest_pyfile = max(pyfiles, key=lambda f: getmtime(f))
    oldest_pickle = min(pickle_files, key=lambda f: getmtime(f))
    if (getmtime(newest_pyfile) - getmtime(oldest_pickle))> 0.01:
        return 'outdated'
    else:
        return 'up-to-date'

