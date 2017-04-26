#!/usr/bin/env python3

# Backend services.

from flask import Flask
import sys

app = Flask(__name__)

if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except:
        print("USAGE: backend.py <port number>")
        exit(1)

    app.run(port=port)
