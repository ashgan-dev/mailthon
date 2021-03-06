# coding=utf8
import pytest
from mailthon.helpers import (guess, format_addresses,
                              encode_address, UnicodeDict)
from .utils import unicode as uni


def test_guess_recognised():
    mimetype, _ = guess('file.html')
    assert mimetype == 'text/html'


def test_guess_fallback():
    mimetype, _ = guess('ha', fallback='text/plain')
    assert mimetype == 'text/plain'


def test_format_addresses():
    chunks = format_addresses([
        ('From', 'sender@mail.com'),
        'Fender <fender@mail.com>',
    ])
    assert chunks == 'From <sender@mail.com>, Fender <fender@mail.com>'


def test_encode_address():
    assert encode_address(uni('mail@mail.com')) == b'mail@mail.com'
    assert encode_address(uni('mail@måil.com')) == b'mail@xn--mil-ula.com'
    assert encode_address(uni('måil@måil.com')) == b'm\xc3\xa5il@xn--mil-ula.com'


class TestUnicodeDict:
    @pytest.fixture
    def mapping(self):
        return UnicodeDict({'Item': uni('måil')})

    @pytest.mark.parametrize('param', [
        uni('måil'),
        uni('måil').encode('utf8'),
    ])
    def test_setitem(self, param):
        u = UnicodeDict()
        u['Item'] = param
        assert u['Item'] == uni('måil')

    def test_update(self, mapping):
        mapping.update({
            'Item-1': uni('unicode-itém'),
            'Item-2': uni('bytes-item').encode('utf8'),
        })
        assert mapping['Item-1'] == uni('unicode-itém')
        assert mapping['Item-2'] == uni('bytes-item')
