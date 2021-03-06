import pytest
from mock import Mock, call
import mailthon.headers
from mailthon.headers import Headers, cc, to, bcc, sender, message_id, date
from .mimetest import blank


class TestNotResentHeaders:
    @pytest.fixture
    def headers(self):
        return Headers([
            ('From', 'from@mail.com'),
            sender('sender@mail.com'),
            to('to@mail.com'),
            cc('cc1@mail.com', 'cc2@mail.com'),
            bcc('bcc1@mail.com', 'bcc2@mail.com'),
        ])

    def test_getitem(self, headers):
        assert headers['From'] == 'sender@mail.com'
        assert headers['To'] == 'to@mail.com'

    def test_sender(self, headers):
        assert headers.sender == 'sender@mail.com'

    def test_receivers(self, headers):
        assert set(headers.receivers) == set([
            'to@mail.com',
            'cc1@mail.com',
            'cc2@mail.com',
            'bcc1@mail.com',
            'bcc2@mail.com',
            ])

    def test_resent(self, headers):
        assert not headers.resent

    def test_prepare(self, headers):
        mime = blank()
        headers.prepare(mime)

        assert not mime['Bcc']
        assert mime['Cc'] == 'cc1@mail.com, cc2@mail.com'
        assert mime['To'] == 'to@mail.com'
        assert mime['From'] == 'sender@mail.com'


class TestResentHeaders(TestNotResentHeaders):
    @pytest.fixture
    def headers(self):
        head = TestNotResentHeaders.headers(self)
        head.update({
            'Resent-Date': 'Today',
            'Resent-From': 'rfrom@mail.com',
            'Resent-To': 'rto@mail.com',
            'Resent-Cc': 'rcc@mail.com',
            'Resent-Bcc': 'rbcc1@mail.com, rbcc2@mail.com'
        })
        return head

    def test_sender(self, headers):
        assert headers.sender == 'rfrom@mail.com'

    def test_prefers_resent_sender(self, headers):
        headers['Resent-Sender'] = 'rsender@mail.com'
        assert headers.sender == 'rsender@mail.com'

    def test_resent_sender_without_senders(self, headers):
        del headers['Resent-From']
        assert headers.sender is None

    def test_receivers(self, headers):
        assert set(headers.receivers) == set([
            'rto@mail.com',
            'rcc@mail.com',
            'rbcc1@mail.com',
            'rbcc2@mail.com',
        ])

    def test_resent(self, headers):
        assert headers.resent

    def test_resent_date_removed(self, headers):
        headers.pop('Resent-Date')
        assert not headers.resent

    def test_prepare(self, headers):
        mime = blank()
        headers.prepare(mime)

        assert not mime['Resent-Bcc']
        assert not mime['Bcc']


@pytest.mark.parametrize('function', [to, cc, bcc])
def test_tuple_headers(function):
    _, value = function(
        ('From', 'sender@mail.com'),
        'Me <me@mail.com>',
    )
    expected = 'From <sender@mail.com>, Me <me@mail.com>'
    assert value == expected


@pytest.mark.parametrize('argtype', [str, tuple])
def test_sender_tuple(argtype):
    param = ('name', 'mail@mail.com')
    if argtype is str:
        param = '{0} <{1}>'.format(*param)
    _, value = sender(param)
    assert value == 'name <mail@mail.com>'


def test_message_id():
    def msgid(thing=None):
        return thing

    mailthon.headers.make_msgid = Mock(side_effect=msgid)
    assert tuple(message_id()) == ('Message-ID', None)
    assert tuple(message_id('string')) == ('Message-ID', 'string')
    assert tuple(message_id(idstring=1)) == ('Message-ID', 1)


def test_date():
    formatdate = mailthon.headers.formatdate = Mock(return_value=1)
    assert tuple(date()) == ('Date', 1)
    assert formatdate.mock_calls == [call(localtime=True)]

    assert tuple(date('time')) == ('Date', 'time')
