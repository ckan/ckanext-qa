import pytest
from ckanext.qa.tests.mock_flask_server import create_app

import threading


@pytest.fixture(scope='session', autouse=True)
def client():
    app = create_app()
    port = 9091
    thread = threading.Thread(target=lambda: app.run(debug=True, port=port, use_reloader=False))
    thread.daemon = True
    thread.start()

    yield "http://127.0.0.1:" + str(port)
