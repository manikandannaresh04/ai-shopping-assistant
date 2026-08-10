import os

class Config:
    SECRET_KEY = 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///shopping.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False