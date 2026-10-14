"""Optional pytest plugin: deny remote sockets during isolated Home review."""
import socket

_original_connect = socket.socket.connect


def pytest_configure(config):
    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            host = address[0]
            if host not in {'127.0.0.1', '::1', 'localhost'}:
                raise AssertionError('External network prohibited during Home review')
        return _original_connect(sock, address)
    socket.socket.connect = connect


def pytest_unconfigure(config):
    socket.socket.connect = _original_connect
