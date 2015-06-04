from pytest import fixture
from mock import Mock, call
from mailthon.middleware import TLS, Auth
from .utils import tls_started


@fixture
def smtp():
    return Mock()


class TestTlsSupported:
    @fixture
    def conn(self, smtp):
        smtp.has_extn.return_value = True
        return smtp

    def test_no_force(self, conn):
        tls = TLS()
        tls(conn)

        assert conn.mock_calls[0] == call.has_extn('STARTTLS')
        assert tls_started(conn)

    def test_force(self, conn):
        tls = TLS(force=True)
        tls(conn)

        assert tls_started(conn)


class TestTLSUnsupported:
    @fixture
    def conn(self, smtp):
        smtp.has_extn.return_value = False
        return smtp

    def test_no_force(self, conn):
        tls = TLS()
        tls(conn)

        assert not tls_started(conn)


class TestAuth:
    def test_logs_in_user(self, smtp):
        auth = Auth(username='user', password='pass')
        auth(smtp)

        assert call.login('user', 'pass') in smtp.mock_calls
