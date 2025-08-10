from flask import Blueprint
api = Blueprint("api", __name__)
from .endpoints import *  # registers routes
