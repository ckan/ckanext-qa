import os
from flask import Flask, request, make_response


def create_app():
    app = Flask(__name__)

    @app.route('/', defaults={"path": ""})
    @app.route('/<path:path>')
    def echo(path):
        status = int(request.args.get('status', 200))

        content = request.args.get('content', '')

        response = make_response(content, status)

        headers = [
            item
            for item in list(request.args.items())
            if item[0] not in ('content', 'status')
        ]

        if 'length' in request.args:
            cl = request.args.get('length')
            headers += [('Content-Length', cl)]
        elif content and 'no-content-length' not in request.args:
            headers += [('Content-Length', bytes(len(content)))]

        for k, v in headers:
            response.headers[k] = v

        return response

    return app


def get_file_content(data_filename):
    filepath = os.path.join(os.path.dirname(__file__), 'data', data_filename)
    assert os.path.exists(filepath), filepath
    with open(filepath, 'rb') as f:
        return f.read()
