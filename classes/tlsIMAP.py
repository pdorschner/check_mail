import imaplib
import ssl

Commands = {
  'STARTTLS': ('NONAUTH')
}

imaplib.Commands.update(Commands)

class IMAP4_STARTTLS(imaplib.IMAP4, object):
  def __init__(self, host, port):
    super(IMAP4_STARTTLS, self).__init__(host, port)
    self.__starttls__()
    self.__capability__()

  def __starttls__(self, keyfile = None, certfile = None):
    typ, data = self._simple_command('STARTTLS')
    if typ != 'OK':
      raise self.error('no STARTTLS')
    self.sock = ssl.wrap_socket(self.sock,
      keyfile,
      certfile,
      ssl_version=ssl.PROTOCOL_TLSv1)
    self.file.close()
    self.file = self.sock.makefile('rb')

  def __capability__(self):
    typ, dat = super(IMAP4_STARTTLS, self).capability()
    if dat == [None]:
      raise self.error('no CAPABILITY response from server')
    self.capabilities = tuple(dat[-1].upper().split())