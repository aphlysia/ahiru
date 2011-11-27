import time as _time
from user import User
import pickle
import hashlib

class NeedParent(Exception): pass
class InvalidSign(Exception): pass

class Action:
	Insert = 1
	Update = 2

	def __init__(self):
		self.userID = None
		self.no = None
		self.act = None
		self.data = None
		self.comment = None
		self.time = None
		self.parent = None
		self.root = None
		self.sign = None

	@classmethod
	def new(cls, bookID, user, no, act, data, comment = None, parent = None, time = None):
		assert isinstance(user, User)
		assert isinstance(no, int)
		assert act in (cls.Insert, cls.Update)
		assert comment is None or isinstance(comment, str)
		assert parent is None or isinstance(parent, cls)
		assert time is None or isinstance(_time, float)

		self = cls()
		self.userID = user.ID()
		self.no = no
		self.act = act
		self.data = data
		self.comment = comment
		if time is None:
			self.time = _time.time()
		if act == self.Insert:
			self.parent = None
			self.root = self.ID()
		elif act == self.Update:
			self.parent = parent.ID()
			self.root = parent.root
		self.sign = user.encrypt(hashlib.sha256(str((bookID, self.userID, self.no, self.act, self.data, self.comment, self.time, self.parent, self.root)).encode('utf8')).hexdigest())
		return self

	@classmethod
	def newFromDict(cls, bookID, user, userID, no, act, data, comment, time, parent, root, sign):
		assert isinstance(user, User)
		if user.decrypt(sign) == hashlib.sha256(str((bookID, userID, no, act, data, comment, time, parent, root)).encode('utf8')).hexdigest():
			s = cls()
			s.userID = user.ID()
			s.no = no
			s.act = act
			s.data = data
			s.comment = comment
			s.time = time
			s.parent = parent
			s.root = root
			s.sign = s
			return s
		raise InvalidSign()
	
	@classmethod
	def actionID(c, userID, no):
		if isinstance(userID, tuple):
			return userID + (no,)
		return userID, no
		
	def ID(self):
		return self.__class__.actionID(self.userID, self.no)

	def toDict(self):
		return {
			'userID': self.userID,
			'act': self.act,
			'data': self.data,
			'sign': self.sign,
			'comment': self.comment,
			'no': self.no,
			'time': self.time,
			'parent': self.parent,
			'root': self.root,
		}
	
