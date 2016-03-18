"""The main CLI for regolith"""
from __future__ import print_function
import os
import json
from argparse import ArgumentParser

from regolith.runcontrol import RunControl, NotSpecified
from regolith.validators import DEFAULT_VALIDATORS
from regolith.database import connect_mongo, connect_tinydb
from regolith.tools import db_backend
from regolith import commands
from regolith import storage

DEFAULT_RC = RunControl(
    _validators=DEFAULT_VALIDATORS,
    builddir='_build',
    mongodbpath=property(lambda self: os.path.join(self.builddir, '_dbpath'))
    )

DISCONNECTED_COMMANDS = {
    'rc': lambda rc: print(rc._pformat()),
    'deploy': commands.deploy,
    'store': storage.main,
    }

CONNECTED_COMMANDS = {
    'add': commands.add_cmd,
    'ingest': commands.ingest,
    'app': commands.app,
    'grade': commands.grade,
    'build': commands.build,
    }


def load_json_rcfile(fname):
    """Loads a JSON run control file."""
    with open(fname, 'r') as f:
        rc = json.load(f)
    return rc


def load_rcfile(fname):
    """Loads a run control file."""
    base, ext = os.path.splitext(fname)
    if ext == '.json':
        rc = load_json_rcfile(fname)
    else:
        raise RuntimeError('could not detemine run control file type from extension.')
    return rc


def create_parser():
    p = ArgumentParser()
    subp = p.add_subparsers(title='cmd', dest='cmd')
    # rc subparser
    rcp = subp.add_parser('rc', help='prints run control')
    # add subparser
    addp = subp.add_parser('add', help='adds a record to a database and collection')
    addp.add_argument('db', help='database name')
    addp.add_argument('coll', help='collection name')
    addp.add_argument('documents', nargs='+', help='documents, in JSON / mongodb format')
    # ingest subparser
    ingp = subp.add_parser('ingest', help='ingest many records from a foreign '
                                          'resource into a database')
    ingp.add_argument('db', help='database name')
    ingp.add_argument('filename', help='file to ingest')
    ingp.add_argument('--coll', dest='coll',  default=None, 
                      help='collection name, if this is not given it is infered from the '
                           'file type or file name.')
    # store subparser
    strp = subp.add_parser('store', help='stores a file into the approriate '
                                         'storage location.')
    strp.add_argument('storename', help='storage name')
    strp.add_argument('documents', nargs='+', help='paths to documents, i.e. '
                                                   'PDFs, images, etc.')
    strp.add_argument('-f', '--force', dest='force', default=False, 
                      action='store_true',
                      help='forces copy of file if one of the same name '
                           'already exists')
    # app subparser
    appp = subp.add_parser('app', help='starts up a flask app for inspecting and '
                                       'modifying regolith data.')
    appp.add_argument('--debug', dest='debug', action='store_true', default=False, 
                      help='starts server in debug mode')
    # grade subparser
    grdp = subp.add_parser('grade', help='starts up a flask app for adding '
                                         'grades to the database.')
    grdp.add_argument('--debug', dest='debug', action='store_true', 
                      default=False, help='starts server in debug mode')
    # builder subparser
    bldp = subp.add_parser('build', help='builds various available targets')
    bldp.add_argument('build_targets', nargs='+', help='targets to build.')
    # deploy subparser
    depp = subp.add_parser('deploy', help='deploys what was built by regolith')
    return p


def filter_databases(rc):
    """Filters the databases list down to only the ones we need, in place."""
    dbs = rc.databases
    public_only = rc._get('public_only', False)
    if public_only:
        dbs = [db for db in dbs if db['public']]
    dbname = rc._get('db') 
    if dbname is not None:
        dbs = [db for db in dbs if db['name'] == dbname]
    rc.databases = dbs
    

def main(args=None):
    rc = DEFAULT_RC
    rc._update(load_rcfile('regolithrc.json'))
    parser = create_parser()
    ns = parser.parse_args(args)
    rc._update(ns.__dict__)
    filter_databases(rc)
    if db_backend(rc) == "tinydb":
        connect = connect_tinydb
    else:
        connect = connect_mongo
    if rc.cmd in DISCONNECTED_COMMANDS:
        DISCONNECTED_COMMANDS[rc.cmd](rc)
    else:
        with connect(rc) as rc.client:
            CONNECTED_COMMANDS[rc.cmd](rc)

if __name__ == '__main__':
    main()
