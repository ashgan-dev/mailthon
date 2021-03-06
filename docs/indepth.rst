.. _indepth:

In Depth Guide
==============

This document describes the API in a stage-by-stage basis.
It is useful as a book-like, gentle technical introduction
to the higher and lower level APIs. Before reading this
guide it is recommended that you browse through the :ref:`quickstart`
as it will give a very high level introduction to Maithon.
If you want to look for some method or class, go to the
:ref:`api` section.

Envelopes and MIMEs
-------------------

The :class:`~mailthon.envelope.Envelope` class actually
wraps around multipart MIME objects. This means they can
be composed of multiple other MIME objects, e.g. plaintext
MIMEs, MIMEs containing HTML data, images, etc, which provides
the perfect building block for a composable class. Envelopes
are made of two parts- like a real life envelope, a "stamp",
or headers, and an enclosure, made of other mime objects::
 
    from mailthon.envelope import Envelope
    from mailthon.enclosure import PlainText

    e = Envelope(
        headers={'X-Key': 'Value'},
        enclosure=[PlainText('something')],
    )

An interesting thing to take note of is that envelopes can
be enclosed within envelopes. Concretely speaking, Envelopes
consist of the :class:`~mailthon.headers.Headers` class and
a list of :class:`~mailthon.enclosure.Enclosure` objects::

    >>> e.headers
    {'X-Key': u'Value'}
    >>> e.enclosure
    [<mailthon.enclosure.PlainText object at 0x...>]

You might have noticed that the ``Value`` string that was
set was changed to a Unicode value. Why is that so? This
is because internally the :class:`~mailthon.headers.Headers`
class decodes bytes values that we throw at it into Unicode
objects, freeing the developer from any headaches about
encoding. You can read more about these design decisions
at the :ref:`design` section.

Now that we've looked at the higher level API of the
:class:`~mailthon.envelope.Envelope` class, let's plunge
deeper into madness and look into how it generates MIME
objects with the :meth:`~mailthon.envelope.Envelope.mime`
method::

    >>> e.mime()
    <email.mime.multipart.MIMEMultipart object at 0x...>

1. Generates a :class:`~email.mime.multipart.MIMEMultipart`
   instance and attaches each of the enclosures with the
   :meth:`~email.message.Message.attach` method. Conceptually
   this is what you'd do with a real envelope- put each of
   the content into the enclosure of the envelope.
2. Puts a stamp on the envelope- sets the headers onto
   the envelope object. This is done via the
   :meth:`~mailthon.headers.Headers.prepare` method
   of the headers object, which handles setting the
   appropriate headers- e.g. it ignores the Bcc headers
   to save you from embarassment and also to make
   Mailthon compliant with :rfc:`2822`.

Disecting Enclosures
--------------------

Conceptually the :class:`~mailthon.envelope.Envelope` and
:class:`~mailthon.enclosure.Enclosure` classes are the
same- they are both made out of headers and some content.
API-wise, they are also nearly identical- they both
provide the same :meth:`~mailthon.enclosure.Enclosure.mime`
method. And you are right! Here we see that the enclosure
objects do in fact have almost the same attributes::

    >>> plaintext = PlainText('content')
    >>> plaintext.headers
    {}
    >>> plaintext.mime()
    <email.mime.text.MIMEText object at 0x...>

However, speaking from a responsibility perspecitive,
here is where they differ. Envelopes have the concept
of senders and receivers- and must keep track of them.
Enclosures however, are like a superset of envelopes-
an envelope can be an enclosure, but not the other
way round, (at least, without some tricks).

All Enclosures have a :attr:`~Enclosure.content`
attribute that represents the content of the enclosure.
This is once again something that the envelope
object doesn't have::

    >>> plaintext.content
    'content'

The role as a MIME-preparing class is the same. As
mentioned earlier, both classes have the
:meth:`~mailthon.enclosure.Enclosure.mime` method
which prepares a MIME object- needless to say
different subclasses of the :class:`~mailthon.enclosure.Enclosure`
class handle different mimetypes, e.g.
:class:`~mailthon.enclosure.PlainText` handles
``text/plain`` content. Similarly this is what
an enclosure class does when it's :meth:`~mailthon.enclosure.Enclosure.mime`
method is called:

1. Prepare the MIME object. For :class:`~mailthon.enclosure.PlainText`
   enclosures this returns a :class:`~email.mime.text.MIMEText`
   object. For :class:`~mailthon.enclosure.Binary`
   enclosures the method returns a :class:`~email.mime.base.MIMEBase`
   object which is a lower level but more configurable
   and flexible version of the ``MIMEText`` class.
2. Apply the headers. Conceptually this is where the
   envelope analogy breaks down- you don't usually
   have stamps inside enclosures, but let's pretend
   that didn't happen. The Enclosure object is designed
   in such a way such that the subclasses will not need
   to worry about applying the user's headers. Essentially
   what the :meth:`~mailthon.enclosure.Enclosure.mime`
   method looks like is::

       def mime(self):
           mime = self.mime_object()
           self.headers.prepare(mime)
           return mime

   Which means that you usually do not have to worry
   about any headers that you've set not being applied
   to the generated MIME objects. So if you were to
   subclass the enclosure class::

       class Cat(Enclosure):
           def mime_object(self):
               return make_mime(self.cat_name)

   Which prevents you from shooting yourself in the
   foot. Or other parts of your body. Also it makes
   sure that, most of the time, you get the benefit
   of having the Mailthon infrastructure supporting
   your back- the main example being free of having
   to worry about encoding.

Few Sips of SMTP
----------------

How in the world, you ask, do you have tricks to make
the :class:`~mailthon.enclosure.Enclosure` class to
behave like an envelope? The Oracle answers, via
the runtime modification of attributes which may
cause headaches in production; but hey, let's try
them anyways::

    enclosure = PlainText('something')
    enclosure.mail_from = u'sender@mail.com'
    enclosure.receivers = [u'rcv1@mail.com', u'rcv2@mail.com']
    
    def string(self):
        return self.mime().as_string()

    enclosure.string = string

Note that the ``mail_from`` and ``receivers``
attributes having Unicode values is absolutely
necessary, and we'll see why when we talk about
then later when we explore the :class:`~mailthon.postman.Postman`
object. For now, assume that they will be properly
encoded by Mailthon. When we pass the enclosure
we've mutated to a :class:`~mailthon.postman.Postman`
instance, it'll happily send it off::

    >>> r = postman.send(enclosure)
    >>> assert r.ok

Questioning our identity
^^^^^^^^^^^^^^^^^^^^^^^^

Notice the ``mail_from`` attribute- it is not
named something like ``sender``. Why is that so?
It is named such that it is synonymous with the
SMTP ``MAIL FROM`` command. This is what is sent
by a vanila (without any middleware) Postman
instance in a typical SMTP session:

.. code-block:: text
   :emphasize-lines: 2

    HELO relay.example.org
    MAIL FROM:<sender@mail.com>
    RCPT TO:<rcv1@mail.com>
    RCPT TO:<rcv2@mail.com>
    DATA
    <mime data>
    QUIT

Note the highlighted line- the address passed to the
``MAIL FROM`` command is the 'true' sender. For example
you begin your letter with something along the lines of
"From XXX". The postman doesn't care about whatever you
wrote in there. He may, however write down your name
somewhere for bookeeping reasons. The address passed
to the ``MAIL FROM`` command is, essentially, your
'true' name. More info about this can be obtained
by reading :rfc:`2821`.

Usually you are doing the sane thing- you are sending
from the same email address that you are claiming to
send from (i.e. the one you set in the `headers`
argument to the :class:`~mailthon.envelope.Envelope`
class). But if you wish to do so, you can change the
'real' address. There are two ways to do it::

    from mailthon.headers import sender

    envelope = Envelope(
        headers=[sender('Fake <fake@mail.com>')],
        enclosure=[],
        mail_from=u'email_address@mail.com',
    )
    envelope.mail_from = u'other@mail.com'

However if you want the inferred sender (the one
that was obtained from the headers) you can still
do so via the :attr:`~mailthon.envelope.Envelope.sender`
attribute. You can read more about the behaviour
of the :attr:`~mailthon.envelope.Envelope.mail_from`
attribute.

The headless MIME
^^^^^^^^^^^^^^^^^

In an ideal world, the SMTP protocol speaks Unicode
and we can all throw poop emojis around at each other
while pretending to get our work done. But that is
sadly not the case. SMTP is a protocol which only
understands bytes, and was invented way back in
`1982 <http://tools.ietf.org/html/rfc821>`_ when
nobody cared about characters outside the English
alphabet.

As a result, the simple ASCII encoding stuck and
was used as the de-facto standard for emails and
most other protocols. However, SMTP, given that it
does only operate in bytes, does allow you to simply do::

    Subject: 哈咯 (Hello)

But some clients will not be able to read it if they
are expected something encoded in ASCII, and suddenly
get some UTF-8 value, and is likely to end up with
`Mojibake <http://en.wikipedia.org/wiki/Mojibake>`_.

Instead, we must specify the encoding, and then
rewrite all of the code points of the string so that
it is ASCII-encoded. So your beautiful characters
end up looking like::

    >>> from email.header import Header
    >>> Header(u'哈咯 (Hello)', 'utf-8').encode()
    '=?utf-8?b?5ZOI5ZKvIChIZWxsbyk=?='

Not very nice, nor human readable. So rather
than having you manually encode everything,
Mailthon insists on having everything in
Unicode. This makes everything a lot easier-
extracting and encoding addresses, equality
comparisions, etc. So the job of the :class:`~mailthon.headers.Headers`
class (specifically, the :class:`~mailthon.helpers.UnicodeDict`
class) is to handle all this for you::

    >>> from email.message import Message
    >>> from mailthon.headers import Headers
    >>> headers = Headers({
    ...    'Subject': u'∂y is not exact',
    ... })
    >>> mime = Message()
    >>> headers.prepare(mime)
    >>> mime.as_string()
    'Subject: =?utf-8?q?=E2=88=82y_is_not_exact?=\n\n'

For the record, it's actually the :class:`~email.message.Message`
class that does all the heavy lifting- for space
saving and efficiency reasons, Mailthon simply
supplies it with the Unicode string and it
determines whether to encode with ASCII or
UTF-8.

IDNA and Friends
^^^^^^^^^^^^^^^^

Turns out that there is now a format for
encoding domain names with non-ASCII
characters in them, specified in :rfc:`3490`
and usually referred to as
`IDN or IDNA <http://en.wikipedia.org/wiki/Internationalized_domain_name>`_.
For a real life example: `é.com <http://xn--9ca.com>`_.
This gives us a pleasant surprise if we try
to encode everything with UTF-8, the silver
bullet to our Unicode encoding woes::

    >>> u'é'.encode('utf8')
    '\xc3\xa9'
    >>> u'é'.encode('idna')
    'xn--9ca'

A short detour on the format of email addresses-
they are made up of two parts, separated by the
first occurence of the '@' symbol.

1. `Local-Part <http://en.wikipedia.org/wiki/Email_address#Local_part>`_
   which can be UTF-8 encoded as per :rfc:`6531`.
   The local part is not really important to the
   sending server who you are sending it to, rather
   it is more concerned with which server you are
   sending it to.
2. `Domain-Part <http://en.wikipedia.org/wiki/Email_address#Domain_part>`_
   which should be IDNA-encoded. Although servers
   which are compliant with both :rfc:`6531` and
   :rfc:`6532` can accept Unicode-encoded domain
   names, the pessimistic guess would be that most
   aren't, so for the time being we are encoding
   in IDNA.

Putting it all together we have something like
the following function::

    def encode_address(addr):
        localpart, domain = addr.split('@', 1)
        return b'@'.join([
            localpart.encode('utf8'),
            domain.encode('idna'),
        ])

But Mailthon already has a more robust implementation
available in the form of the :func:`~mailthon.helpers.encode_address`
function, and is automatically used by the :class:`~mailthon.postman.Postman`
class when sending envelopes. Via the :meth:`~smtplib.SMTP.sendmail`
method. Essentially, the following::

    def send(smtp, envelope):
        smtp.sendmail(
            encode_address(envelope.sender),
            [encode_address(k) for k in envelope.receivers],
            envelope.string(),
        )

Which explains why the addresses specified in the
:attr:`~mailthon.envelope.Envelope.mail_from` and
:attr:`~mailthon.envelope.Envelope.receivers` attributes
must be Unicode values instead of byte strings
since mixing them up will cause issues in Python 3.

The Postman Object
------------------

The :class:`~mailthon.postman.Postman` class is
responsible for delivering the email via some
transport, and is meant as a transport-agnostic
layer to make sending emails via different protocols
as painless as possible. Let's start by creating
a postman instance::

    >>> from mailthon.postman import Postman
    >>> postman = Postman(host='smtp.server.com', port=587)

The Mutation Phase
^^^^^^^^^^^^^^^^^^

The :attr:`~Postman.transport` attribute. This is
the actual "transport" used to send our emails over
to a real server. To implement a transport it turns
out that we need, at the very least, to have the
``ehlo``, ``noop``, ``quit``, and ``sendmail``
methods::

    class MyTransport(object):
        def __init__(self, host, port):
            self.host = host
            self.port = port
            self.connection_started = False

        def check_conn(self):
            if not self.connection_started:
                raise IOError

        def noop(self):
            self.check_conn()
            return 200

        def ehlo(self):
            self.connection_started = True

        def sendmail(self, sender, receipients, string):
            self.check_conn()
            return {}

        def quit(self):
            self.connection_started = False

Next all we need to do is replace the ``tranport``
attribute with the class object that we've just
created. Although this is not recommended as I
recommend subclassing to change the transport
being used we will do it anyways::

    postman.transport = MyTransport

The :attr:`~Postman.response_cls` attribute will
contain a custom response class. We will create
our own response class as well::

    class Response(object):
        def __init__(self, rejected, status):
            self.rejected = rejected
            self.status_code = status
     
        @property
        def ok(self):
            return self.status_code == 200 and \
                   not self.rejected

If you haven't noticed, the ``__init__`` method
of our custom response class matches perfectly
with the return values of the ``sendmail`` and
``noop`` methods from the ``MyTransport`` class,
respectively. They are called by the :class:`~mailthon.postman.Postman`
class like so::

   def deliver(self, conn, envelope):
       rejected = conn.sendmail(...)
       return self.response_cls(rejected, conn.noop())

Now we just have to change the response class on
the postman object we've created. Once again I
recommend subclassing to change these attributes
but for this experiment we'll change them in runtime::

    >>> postman.response_cls = Response

Putting it all together
^^^^^^^^^^^^^^^^^^^^^^^

Next we'll send an envelope "across the wire" using
our mutated postman object with our custom transport
and response classes::

    >>> r = postman.send(envelope)
    >>> assert r.ok

But that doesn't give us very much knowlegde of what
happens underneath the hood. The :meth:`~mailthon.postman.Postman.send`
method is simply a veneer over the lower level
:meth:`~mailthon.postman.Postman.connection` and
:meth:`~mailthon.postman.Postman.deliver` methods.
Let's recreate the send method::

    >>> with postman.connection() as conn:
    ...    print(conn.connection_started)
    ...    r = postman.deliver(conn, envelope)
    ...    print(r)
    ...
    True
    <__main__.Response object at 0x...>

Basically what the :meth:`~mailthon.postman.Postman.connection`
context manager does is that it manages the (usually SMTP)
session for you. It is roughly implemented as::

    @contextmanager
    def connection(self):
        conn = self.transport(self.host, self.port)
        try:
            conn.ehlo()
            yield conn
        finally:
            conn.quit()

Which closes the connection regardless of whether the
sending operation is a success. This is important to
prevent excessive memory and file-descriptor usage
from the open sockets. You can verify that the connection
as closed::

    >>> conn.connection_started
    False

Which is changed to False due the the context manager
calling the ``quit`` method once the block of code within
the ``with`` statement has finished executing. If you
would like to find out how all of this is implemented
you can take a look at the `source <https://github.com/eugene-eeo/mailthon/blob/master/mailthon/postman.py>`_
code.

Middlewares and Middlemen
-------------------------

One of the more powerful features of Mailthon is the
ability to add middleware- which are basically functions
that allow for certain features, e.g. :class:`~mailthon.middleware.TLS`,
:class:`~mailthon.middleware.Auth` which provide for
TLS and authentication, respectively. Let's make
our own middleware to see how all of this is done::

    def my_middleware(must_have=()):
        def func(conn):
            for item in must_have:
                assert hasattr(conn, item)
        return func

Then we need to put our middleware in what's known
as a middleware stack. It is basically a list of
callables which will be invoked with the transport
object. Using our Postman class::

    postman.use(my_middleware(['quit']))

Which will add the closure into the middleware stack
and assert that the transport object has the ``quit``
attribute/method. More powerful middleware can
certainly be programmed via classes, the recommended
way if you want to make extensible middlewares is to
subclass from the :class:`~mailthon.middleware.Middleware`
class::

    from mailthon.middleware import Middleware

    class MyMiddleware(Middle):
        def __call__(self, conn):
            pass

The registered middlewares will be called by the
:meth:`~mailthon.postman.Postman.connection` method
to set up the connection. If any exception is raised,
the connection is automatically closed.
