import hashlib
import re

class NoSecKey(Exception): pass

class User:
	def __init__(self, name, pubKey, secKey = None, host = None, port = None, invitation = None, approverID = None):
		assert isinstance(name, str)
		assert isinstance(pubKey, str)
		assert secKey is None or isinstance(secKey, str)
		assert host is None or isinstance(host, str)
		assert port is None or isinstance(port, int)

		self.name = name
		self.pubKey = pubKey
		self.secKey = secKey
		self.host = host
		self.port = port
		self.invitation = invitation
		self.approverID = approverID
	
	def toDict(self):
		return {
			'name': self.name,
			'pubKey': self.pubKey,
			'host': self.host,
			'port': self.port,
			'invitation': self.invitation,
			'approverID': self.approverID,
			}

	def encrypt(self, string):
		#todo: implement actual encryption
		if self.secKey is None:
			raise NoSecKey()
		return '[' + self.pubKey + ']' + string + '[' + self.pubKey + ']'

	def decrypt(self, string):
		#todo: implement actual decryption
		return re.sub('^\[' + self.pubKey + '\](.+)\[' + self.pubKey + '\]', '\g<1>', string)

	def ID(self):
		return hashlib.sha256(str((self.name, self.pubKey)).encode('utf8')).hexdigest()

	def invite(self, comer, bookID):
		assert isinstance(comer, self.__class__)

		comer.invitation = self.encrypt(hashlib.sha256(str((comer.ID(), bookID)).encode('utf8')).hexdigest())
		comer.approverID = self.ID()

	@classmethod
	def isValidInvitation(cls, approver, comer, bookID):
		assert isinstance(approver, cls)
		assert isinstance(comer, cls)

		if not isinstance(comer.invitation, str):
			return False
		return approver.decrypt(comer.invitation) == hashlib.sha256(str((comer.ID(), bookID)).encode('utf8')).hexdigest()

