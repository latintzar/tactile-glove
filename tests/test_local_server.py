"""Exercise actual HTTP routes and file containment with a loopback server."""
import importlib.util
import threading
from pathlib import Path
from http.client import HTTPConnection
from urllib.parse import urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('glove_serve', ROOT/'tools/serve.py')
serve = importlib.util.module_from_spec(spec); spec.loader.exec_module(serve)

@pytest.fixture(scope='module')
def origin():
    server = serve.ThreadingHTTPServer(('127.0.0.1', 0), serve.DesignHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown(); worker.join(); server.server_close()

@pytest.mark.parametrize('path,needle', [
    ('/', b'Cuff components'),
    ('/device/', b'Waiting for hardware data'),
    ('/hardware/glove-v4/enclosure/scene.json', b'positions'),
    ('/hardware/glove-v4/enclosure/print-manifest.json', b'first_article_fabrication_ready'),
    ('/static/glove-viewer/three.module.js', b'WebGLRenderer'),
    ('/build-v4-reference/guide/assembly.html', b'<!doctype html>'),
])
def test_actual_public_routes(origin,path,needle):
    with urlopen(origin+path) as r:
        assert r.status == 200
        assert needle in r.read()
        assert r.headers['X-Content-Type-Options'] == 'nosniff'

@pytest.mark.parametrize('path', ['/.env', '/.git/config', '/tools/serve.py', '/hardware/', '/%2e%2e/etc/passwd', '/hardware/%2e%2e/%2e%2e/etc/passwd', '/hardware%5c..%5c.env'])
def test_private_and_traversal_routes_rejected(origin,path):
    with pytest.raises(HTTPError) as e: urlopen(origin+path)
    assert e.value.code == 404


@pytest.mark.parametrize('path', ['/', '/hardware/glove-v4/enclosure/viewer.js', '/hardware/glove-v4/enclosure/scene.json'])
def test_head_has_no_body(origin,path):
    parsed = urlsplit(origin)
    c = HTTPConnection(parsed.hostname, parsed.port)
    c.request('HEAD', path)
    r = c.getresponse()
    assert r.status == (302 if path == '/' else 200)
    assert r.read() == b''
    c.close()

def test_outside_symlink_rejected(origin,tmp_path):
    outside = tmp_path/'private.txt'; outside.write_text('private sentinel')
    alias = ROOT/'assets/test-outside-alias.txt'
    assert not alias.exists()
    try:
        alias.symlink_to(outside)
        with pytest.raises(HTTPError) as e: urlopen(origin+'/assets/test-outside-alias.txt')
        assert e.value.code == 404
    finally:
        alias.unlink()
