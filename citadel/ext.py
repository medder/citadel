# coding: utf-8
import mapi
from etcd import Client
from flask_caching import Cache
from flask_mako import MakoTemplates
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from gitlab import Gitlab
from redis import Redis

from citadel.config import ZONE_CONFIG, HUB_ADDRESS, REDIS_URL, GITLAB_URL, GITLAB_PRIVATE_TOKEN
from citadel.libs.utils import memoize


@memoize
def get_etcd(zone):
    cluster = ZONE_CONFIG[zone]['ETCD_CLUSTER']
    return Client(cluster, allow_reconnect=True)


db = SQLAlchemy()
mako = MakoTemplates()
rds = Redis.from_url(REDIS_URL)
cache = Cache(config={'CACHE_TYPE': 'redis'})
gitlab = Gitlab(GITLAB_URL, private_token=GITLAB_PRIVATE_TOKEN)
sess = Session()
hub = mapi.MapiClient(HUB_ADDRESS, use_tls=True)
