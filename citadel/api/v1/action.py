# coding: utf-8

from flask import jsonify, request, Response

from citadel.libs.view import create_api_blueprint
from citadel.libs.datastructure import AbortDict
from citadel.action import (build_image, create_container, remove_container,
        upgrade_container, action_stream, ActionError)


# 把action都挂在/api/:version/下, 不再加前缀
# 也不需要他帮忙自动转JSON了
bp = create_api_blueprint('action', __name__, jsonize=False)


@bp.route('/build', methods=['POST'])
def build():
    """
    可以这么玩玩:
    $ http --stream POST localhost:5000/api/v1/build repo=git@gitlab.ricebook.net:tonic/ci-test.git sha=1d74377e99dcfb3fd892f9eaeab91e1e229179ba uid=4401
    """
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    repo = data['repo']
    sha = data['sha']
    artifact = data.get('artifact', '')
    uid = data.get('uid', '')

    q = build_image(repo, sha, uid, artifact)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/deploy', methods=['POST'])
def deploy():
    data = AbortDict(request.get_json())

    # TODO 参数需要类型校验
    repo = data['repo']
    sha = data['sha']
    podname = data['podname']
    entrypoint = data['entrypoint']
    cpu = float(data['cpu_quota'])
    count = int(data['count'])
    networks = data.get('networks', {})
    envname = data.get('env', '')
    extra_env = data.get('extra_env', []) 
    nodename = data.get('nodename', '')

    q = create_container(repo, sha, podname, nodename, entrypoint, cpu, count, networks, envname, extra_env)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/remove', methods=['POST'])
def remove():
    data = AbortDict(request.get_json())
    ids = data['ids']

    q = remove_container(ids)
    return Response(action_stream(q), mimetype='application/json')


@bp.route('/upgrade', methods=['POST'])
def upgrade():
    data = AbortDict(request.get_json())
    ids = data['ids']
    repo = data['repo']
    sha = data['sha']

    q = upgrade_container(ids, repo, sha)
    return Response(action_stream(q), mimetype='application/json')


@bp.errorhandler(ActionError)
def error_handler(e):
    return jsonify({'error': e.message}), e.code
