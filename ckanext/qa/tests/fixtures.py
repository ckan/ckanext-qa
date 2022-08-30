import pytest
import os
import threading
from ckanext.archiver.tests.mock_flask_server import create_app


@pytest.fixture(scope='session', autouse=True)
def client():
    app = create_app()
    port = 9091
    thread = threading.Thread(target=lambda: app.run(debug=True, port=port, use_reloader=False))
    thread.daemon = True
    thread.start()

    yield "http://127.0.0.1:" + str(port)

@pytest.fixture(scope='class')
def files():
    fixture_data_dir = os.path.join(os.path.dirname(__file__), 'data')
    files = []
    for filename in os.listdir(fixture_data_dir):
        format_extension = '.'.join(filename.split('.')[1:]).replace('_', ' ')
        filepath = os.path.join(fixture_data_dir, filename)
        files.append((format_extension, filepath))

    yield files