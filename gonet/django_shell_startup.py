import os
from os.path import getmtime
from importlib import reload
import random
import io
from collections import defaultdict, OrderedDict
import numpy as np
import pandas as pd
import json
import networkx as nx
from pkg_resources import resource_filename as pkg_file
from gonet import settings
from gonet.models import GOnetSubmission, process_signature
from gonet import ontol
from gonet.ontol import  swissprot, \
                        hpa_data, dice_data, gaf
from gonet import cyjs
from django import urls
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
import pandas as pd
pd.set_option('display.width', 240)
import sqlite3
from django.test import Client
import genontol
from gonet.graph import induced_connected_subgraph
import logging

log = logging.getLogger('gonet')

c = Client()
class BreakIt(Exception):
    pass


