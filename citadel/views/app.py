# -*- coding: utf-8 -*-
from flask import g, request, abort, flash, jsonify, url_for, redirect
from flask_mako import render_template

from citadel.config import IGNORE_PODS, ELB_APP_NAME
from citadel.ext import cache
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release
from citadel.models.base import ModelDeleteError
from citadel.models.container import Container
from citadel.models.gitlab import make_commit_url
from citadel.models.oplog import OPLog, OPType
from citadel.rpc import get_core
from citadel.views.helper import bp_get_app, bp_get_release


bp = create_page_blueprint('app', __name__, url_prefix='/app')


@bp.route('/')
def index():
    apps = [a for a in App.get_all(limit=None) if a.name != ELB_APP_NAME]
    return render_template('/app/list.mako', apps=apps)


@bp.route('/<name>', methods=['GET', 'DELETE'])
def app(name):
    app = bp_get_app(name)
    if request.method == 'DELETE':
        try:
            app.delete()
            return jsonify({'message': 'OK'}), 200
        except ModelDeleteError:
            return jsonify({'message': '容器删干净之后才能删除应用'}), 400

    releases = Release.get_by_app(app.name, limit=8)
    containers = Container.get_by(appname=app.name, zone=g.zone)
    return render_template('/app/app.mako', app=app, releases=releases, containers=containers)


@bp.route('/<name>/version/<sha>', methods=['GET', 'DELETE'])
def release(name, sha):
    app = bp_get_app(name)
    release = Release.get_by_app_and_sha(name, sha)
    if not all([app, release]):
        abort(404, 'App or release not found')

    if request.method == 'DELETE':
        if release.get_container_list():
            release.delete()
            return jsonify({'message': 'OK'})
        else:
            flash('这个版本还有容器在跑')

    # we won't be using pod redis and elb here
    pods = [p for p in get_core(g.zone).list_pods() if p.name not in IGNORE_PODS]
    combos_list = sorted((combo_name, combo) for combo_name, combo in release.combos.items() if combo.zone == g.zone)
    return render_template('/app/release.mako', app=app, release=release,
                           pods=pods, combos_list=combos_list)


@bp.route('/<name>/env', methods=['GET', 'POST'])
def app_env(name):
    app = bp_get_app(name)

    if request.method == 'GET':
        return render_template('/app/env.mako', app=app)

    keys = [key for key in request.form.keys() if key.startswith('key_')]
    env_keys = [request.form[key] for key in keys]
    env_set = {key: request.form.get('value_%s' % key, '') for key in env_keys}

    envname = request.form['env']
    app.add_env_set(envname, env_set)
    op_content = {'envname': envname}
    OPLog.create(OPType.CREATE_ENV, app.name, content=op_content)
    return redirect(url_for('app.app_env', name=name))


@bp.route('/<name>/version/<sha>/gitlab')
@cache.cached(timeout=50)
def gitlab_url(name, sha):
    release = bp_get_release(name, sha)
    commit = release.gitlab_commit
    commit_info = commit.as_dict()
    full_sha = commit_info['id']
    return redirect(make_commit_url(commit_info['project_id'], full_sha))
