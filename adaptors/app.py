"""
file: app.py
The "human" adaptor, the web app.
"""
from flask import Flask
app = Flask(__name__)


@app.route("/")
def hello():
    """
    Hello, World!
    """
    return "<h1>Hello, World!</h1><p>Yes, it's true, it's true.</p>" \
         + "<p>This is my first web app</p>"


if __name__ == "__main__":
    app.run()
