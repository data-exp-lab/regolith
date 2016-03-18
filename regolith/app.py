"""Flask app for looking at information in regolith."""
import traceback

from flask import Flask, abort, request, render_template, redirect, url_for
from bson import json_util, objectid

from regolith.tools import insert_one, delete_one, db_backend
from tinydb import Query

app = Flask('regolith')


@app.route('/', methods=['GET', 'POST'])
def root():
    rc = app.rc
    if request.method == 'POST':
        form = request.form
        return redirect('/db/{dbname}/coll/{collname}'.format(**form))
    return render_template('index.html', rc=rc, db_backend=db_backend(rc))


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    shutdown_server()
    return 'Regolith server shutting down...\n'


@app.route('/db/<dbname>/coll/<collname>', methods=['GET', 'POST'])
def collection_page(dbname, collname):
    rc = app.rc
    try:
        if db_backend(rc) == "tinydb":
            coll = rc.client[dbname].table(collname)
        else:
            coll = rc.client[dbname][collname]
    except (KeyError, AttributeError):
        abort(404)
    status = status_id = None
    if request.method == 'POST':
        form = request.form
        if 'shutdown' in form:
            return shutdown()
        elif 'cancel' in form:
            body = json_util.loads(form['body'].strip())
            status = 'canceled'
            status_id = str(body['_id'])
        elif 'save' in form:
            try:
                body = json_util.loads(form['body'].strip())
            except Exception:
                traceback.print_exc()
                raise
            if db_backend(rc) == "tinydb":
                coll.update(body, eids=[coll.get(Query()._id == body["_id"]).eid])
            else:
                coll.save(body)
            status = 'saved ✓'
            status_id = str(body['_id'])
        elif 'add' in form:
            try:
                body = json_util.loads(form['body'].strip())
            except Exception:
                traceback.print_exc()
                raise
            try:
                added = insert_one(coll, body)
            except Exception:
                traceback.print_exc()
                raise
            status = 'added ✓'
            if db_backend(rc) == "tinydb":
                status_id = str(added)
            else:
                status_id = str(added.inserted_id)
        elif 'delete' in form:
            body = json_util.loads(form['body'].strip())
            deled = delete_one(coll, body)
    return render_template('collection.html', rc=rc, dbname=dbname, len=len, str=str,
                           status=status, status_id=status_id, objectid=objectid,
                           collname=collname, coll=coll, json_util=json_util, min=min,
                           db_backend=db_backend(rc))
