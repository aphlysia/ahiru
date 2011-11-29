import pickle
import os.path
import time
import hashlib
from user import User
from action import Action

class InvalidOwner(Exception): pass
class InvalidUser(Exception): pass
class InvalidIndex(Exception): pass
class InvalidBookFile(Exception): pass
class InvalidActionDictionary(Exception): pass
class NonMember(Exception): pass
class NoRight(Exception): pass
class NoParent(Exception): pass
class ActionExists(Exception): pass

class Book:
	def __init__(self):
		pass

	@classmethod
	def create(cls, owner, title, path = '', quack = True):
		assert isinstance(owner, User)
		assert isinstance(title, str) and title != ''
		assert isinstance(path, str)
		assert isinstance(quack, bool)

		self = cls()
		self.owner = owner
		self.title = title
		self.members = {owner.ID(): owner}
		self.versions = {owner.ID(): 0}
		self.actions = {}
		self.signature = owner.encrypt(title)
		self.createdAt = time.time()
		self.quack = quack
		self.latests = {}
		self.path = path
		self._save()

		return self

	@classmethod
	def copyCover(cls, owner, title, signature, createdAt, path = '', quack = True):
		assert isinstance(owner, User)
		assert isinstance(title, str) and title != ''
		assert isinstance(signature, str)
		assert isinstance(createdAt, float)
		assert isinstance(path, str)
		assert isinstance(quack, bool)

		self = cls()
		self.owner = owner
		self.title = title
		self.members = {owner.ID(): owner}
		self.versions = {owner.ID(): 0}
		self.actions = {}
		self.signature = signature
		self.createdAt = createdAt
		self.latests = {}
		self.quack = quack
		self.path = path
		self._save()

		return self
		
	@classmethod
	def open(cls, bookID = None, owner = None, title = None, path = ''):
		assert bookID is not None or owner is not None and title is not None
		assert owner is not None or isinstance(owner, User)
		assert isinstance(path, str)

		self = cls()
		if bookID is None:
			bookID = cls.ID(owner, title)
		self.path = path
		filename = os.path.join(path, str(bookID) + '.book.pkl')
		if not os.path.isfile(filename):
			raise InvalidBookFile()
		file = open(filename, 'rb')
		c = pickle.load(file)
		file.close()

		self.owner = c['owner']
		self.title = c['title']
		self.members = c['members']
		self.versions = c['versions']
		self.actions = c['actions']
		self.signature = c['signature']
		self.createdAt = c['createdAt']
		self.latests = c['latests']
		self.quack = c['quack']

		return self

	def _save(self):
		title = self.title
		path = self.path
		filename = os.path.join(path, str(self.getID()) + '.book.pkl')

		c = {
			'owner': self.owner,
			'title': self.title,
			'members': self.members,
			'versions': self.versions,
			'actions': self.actions,
			'signature': self.signature,
			'createdAt': self.createdAt,
			'latests': self.latests,
			'quack': self.quack,
		}

		file = open(filename, 'wb')
		pickle.dump(c, file)
		file.close()

	@classmethod
	def ID(cls, owner, title):
		assert isinstance(owner, User)
		assert isinstance(title, str)
		return hashlib.sha256(str((owner.ID(), title)).encode('utf8')).hexdigest()

	def getID(self):
		return self.__class__.ID(self.owner, self.title)

	def setQuack(self):
		self.quack = True
		self._save()

	def unsetQuack(self):
		self.quack = False
		self._save()

	def get(self, ID, no = None):
		if no is None:
			return self.actions[ID]     # action's ID case
		else:
			return self.actions[ID, no] # user's ID case

	def getLatests(self, ID, no = None):
		if no is None:
			return self.latests[ID]     # action's ID case
		else:
			return self.latests[ID, no] # user's ID case

	def isMember(self, user):
		if user.ID() in self.members:
			return True
		if user.approverID is not None and user.approverID in self.members:
			# a newcomer but has not yet been appended to members dictionary
			return User.isValidInvitation(self.members[user.approverID], user, self.getID())
		return False

	def putAction(self, user, actionDict):
		assert isinstance(user, User)
		if 'userID' not in actionDict or 'no' not in actionDict or 'act' not in actionDict or 'data' not in actionDict or 'comment' not in actionDict or 'time' not in actionDict or 'parent' not in actionDict or 'root' not in actionDict or 'sign' not in actionDict:
			raise InvalidActionDictionary()
		if actionDict['parent'] is not None and actionDict['parent'] not in self.actions:
			raise NoParent()
		action = Action.newFromDict(self.getID(), user, **actionDict)
		if action.ID() in self.actions:
			raise ActionExists()
		self.actions[action.ID()] = action
		if self.versions[user.ID()] < actionDict['no']:
			self.versions[user.ID()] = actionDict['no']
		if action.act == Action.Insert:
			self.latests[action.ID()] = [action]
		else:
			latests = self.latests[action.root]
			parent = self.get(action.parent)
			for i in range(len(latests)):
				if latests[i] == parent:
					latests.pop(i)
			latests.insert(0, action)
			latests.sort(key=lambda x: x.time, reverse=True)
		
		self._save()

		return action.ID()

	def put(self, user, data, comment = None):
		if not self.isMember(user):
			raise NonMember()
		self.versions[user.ID()] += 1
		no = self.versions[user.ID()]
		sign = user.encrypt(str(data))
		action = Action.new(self.getID(), user, no, Action.Insert, data, comment) 
		self.actions[action.ID()] = action
		self.latests[action.ID()] = [action]

		self._save()

		return action.ID()

	def update(self, user, data, parent, comment = None):
		"""parent is a action that will be updated"""
		assert isinstance(user, User)
		assert isinstance(data, int) or isinstance(data, float) or isinstance(data, str) or isinstance(data, tuple) or isinstance(data, list) or isinstance(data, dict) or isinstance(data, set)
		assert isinstance(parent, tuple) or isinstance(parent, Action)
		assert comment is None or isinstance(comment, str) 

		if not self.isMember(user):
			raise NonMember()
		if isinstance(parent, tuple):
			parent = self.get(parent)
		self.versions[user.ID()] += 1
		no = self.versions[user.ID()]
		sign = user.encrypt(str(data))
		action = Action.new(self.getID(), user, no, Action.Update, data, comment, parent) 
		self.actions[action.ID()] = action
		latests = self.latests[action.root]
		for i in range(len(latests)):
			if latests[i] == parent:
				latests.pop(i)
		latests.insert(0, action)
		latests.sort(key=lambda x: x.time, reverse=True)

		self._save()

		return action.ID()

	def addMember(self, approver, comer):
		assert isinstance(approver, User)
		assert isinstance(comer, User)
		if approver.ID() not in self.members:
			raise NoRight()
		approver.invite(comer, self.getID())
		self.members[comer.ID()] = comer
		self.versions[comer.ID()] = 0

	'''
	will this function be implemented in future??

	def freeze(self, user, target):
		if not self.isMember(user):
			raise NonMember()
		self.versions[user.ID()] += 1
		no = self.versions[user.ID()]
		action = Action(user.ID(), Action.typeFreeze, comment = comment, no = no, parent = target) 
		latests = self.latest[action.root.user.ID() + (action.root.no,)]
		for i in range(len(latests)):
			if latests[i] == parent:
				latests.pop(i)
			latests.append(action)

		self._save()
	'''

