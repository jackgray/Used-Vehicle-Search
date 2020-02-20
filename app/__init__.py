from flask import Flask
# Load app
app = Flask(__name__, instance_relative_config=True)
from app import views

# Load the config file
app.config.from_object('config')