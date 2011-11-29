import os.path
import threading
import types
import base64
import uuid
import pickle
from user import User
from action import *
from book import *
import tornado.ioloop
import tornado.web
import tornado.httpclient
import tornado.escape as escape
import random
import time


class InvalidParameter(Exception): pass
class BookIDExists(Exception): pass


def _authCode(user):
	assert isinstance(user, User)
	return user.encrypt(str(time.time()))


def _auth(user, password):
	assert isinstance(user, User)
	assert isinstance(password, str)

	now = time.time()
	try:
		t = float(user.decrypt(password))
		if now - t < 60:
			return True
		else:
			return False
	except Exception:
		return False


def _setWhoToAsk(user, whoToAsk, book, connectAll, maxConnection):
	if whoToAsk is None:
		whoToAsk = set()
		if connectAll:
			whoToAsk |= set(book.members.values())
		else:
			rState = random.getstate()
			random.seed(time.time())
			if len(book.members) <= maxConnection:
				whoToAsk |= set(book.members.values())
			else:
				whoToAsk |= set(random.sample(book.members.values(), maxConnection))
			random.setstate(rState)
	return whoToAsk - {user}

def _updateMembers(members, user, book, lock, address):
	lock.acquire()
	ids = [id for id in members if id not in book.members]
	freezeCount = 0
	while ids:
		id = ids.pop(0)
		newcomer = User(**members[id])
		if newcomer.approverID in book.members and User.isValidInvitation(book.members[newcomer.approverID], newcomer, book.getID()):
			book.members[id] = newcomer
			book.versions[id] = 0
			freezeCount = 0
		else:
			freezeCount += 1
			ids.append(id)
			if freezeCount >= len(ids):
				break
	lock.release()
		
	lock.acquire()
	myMembers = dict(book.members)
	lock.release()
	for user in myMembers:
		if user not in members:
			http_client = tornado.httpclient.HTTPClient()
			_body = 'userName=' + escape.url_escape(user.name)
			_body += '&userPubKey=' + escape.url_escape(user.pubKey)
			_body += '&host=' + escape.url_escape(user.host)
			_body += '&port=' + escape.url_escape(str(user.port))
			_body += '&invitation=' + escape.url_escape(user.invitation if user.invitation is not None else ' ')
			_body += '&approverID=' + escape.url_escape(user.approverID if user.approverID is not None else ' ')
			_body += '&bookID=' + escape.url_escape(book.getID())
			_body += '&password=' + escape.url_escape(_authCode(user))
			response = http_client.fetch(address + '/newmembers', method = 'POST', body = _body)
			break

def _updateActions(versions, user, book, lock, address):
	updateMember = []
	for userID in versions:
		if userID in book.versions and book.versions[userID] < versions[userID]:
			updateMember.append(userID)
		elif userID in book.versions and book.versions[userID] > versions[userID]:
			http_client = tornado.httpclient.HTTPClient()
			_body = 'userName=' + escape.url_escape(user.name)
			_body += '&userPubKey=' + escape.url_escape(user.pubKey)
			_body += '&host=' + escape.url_escape(user.host)
			_body += '&port=' + escape.url_escape(str(user.port))
			_body += '&invitation=' + escape.url_escape(user.invitation if user.invitation is not None else ' ')
			_body += '&approverID=' + escape.url_escape(user.approverID if user.approverID is not None else ' ')
			_body += '&bookID=' + escape.url_escape(book.getID())
			_body += '&password=' + escape.url_escape(_authCode(user))
			response = http_client.fetch(address + '/newactions', method = 'POST', body = _body)
			break
	freezeCount = 0
	while updateMember:
		userID = updateMember.pop(0)
		for no in range(book.versions[userID] + 1, versions[userID] + 1):
			if (userID, no) not in book.actions:
				http_client = tornado.httpclient.HTTPClient()
				_body = 'userName=' + escape.url_escape(user.name)
				_body += '&userPubKey=' + escape.url_escape(user.pubKey)
				_body += '&host=' + escape.url_escape(user.host)
				_body += '&port=' + escape.url_escape(str(user.port))
				_body += '&invitation=' + escape.url_escape(user.invitation if user.invitation is not None else ' ')
				_body += '&approverID=' + escape.url_escape(user.approverID if user.approverID is not None else ' ')
				_body += '&bookID=' + escape.url_escape(book.getID())
				_body += '&password=' + escape.url_escape(_authCode(user))
				_body += '&no=' + escape.url_escape(str(no))
				_body += '&authorID=' + escape.url_escape(userID)
				response = http_client.fetch(address + '/action', method = 'POST', body = _body)
				try:
					action = escape.json_decode(response.body)
				except ValueError:
					print('ValueError')
					continue
				if action['parent'] is not None:
					action['parent'] = tuple(action['parent'])
				if action['root'] is not None:
					action['root'] = tuple(action['root'])
				try:
					book.putAction(book.members[userID], action)
					freezeCount = 0
				except NoParent as e:
					freezeCount += 1
					if freezeCount >= len(updateMember):
						return
					if action.parent[0] in versions \
					   and action.parent[0] <= versions[action.parent[0]] \
					   and action.parent[1] <= versions[action.parent[0]]:
						updateMember.append(userID)
					break
				except InvalidSign as e:
					print('exception:InvalidSign')
					break
				except InvalidActionDictionary as e:
					print('exception:invalidActionDictionary')
					return

class _JoinClient(threading.Thread):
	def __init__(self, user, books, lock, bookID, host, port, path = ''):
		super(self.__class__, self).__init__()
		self.user = user
		self.books = books
		self.lock = lock
		self.bookID = bookID
		self.host = host
		self.port = port
		self.path = path
	
	def run(self):
		books = self.books
		lock = self.lock
			
		http_client = tornado.httpclient.HTTPClient()
		_body = 'userName=' + escape.url_escape(self.user.name)
		_body += '&userPubKey=' + escape.url_escape(self.user.pubKey)
		_body += '&host=' + escape.url_escape(self.user.host)
		_body += '&port=' + escape.url_escape(str(self.user.port))
		_body += '&bookID=' + escape.url_escape(self.bookID)
		_body += '&invitation=' + escape.url_escape(' ')
		_body += '&approverID=' + escape.url_escape(' ')
		_body += '&password=' + escape.url_escape(_authCode(self.user))
		address = 'http://' + str(self.host) + ':' + str(self.port)
		try:
			response = http_client.fetch(address + '/join', method = 'POST', body = _body)
			b = escape.json_decode(response.body)
			owner = User(**b['owner'])
			lock.acquire()
			book = Book.copyCover(owner, b['title'], b['signature'], b['createdAt'], self.path)
			books[book.getID()] = book
			lock.release()
			
			response = http_client.fetch(address + '/members', method = 'POST', body = _body)
			members = escape.json_decode(response.body)
			_updateMembers(members, self.user, book, lock, address)
		except tornado.httpclient.HTTPError as e:
			#todo: log
			print("Error:" + str(e))
		except ValueError:
			print('ValueError')
	
class _QuackClient(threading.Thread):
	def __init__(self, user, book, lock, whoToAsk = None, connectAll = False, maxConnection = 3, askAction = True, askMember = True):
		assert isinstance(user, User)
		assert whoToAsk is None or isinstance(whoToAsk, set)
		assert isinstance(connectAll, bool)
		assert isinstance(maxConnection, int) and maxConnection > 0
		assert isinstance(askAction, bool)
		assert isinstance(askMember, bool)

		super(self.__class__, self).__init__()
		self.user = user
		self.book = book
		self.lock = lock
		self.whoToAsk = whoToAsk
		self.connectAll = connectAll
		self.maxConnection = maxConnection
		self.askAction = askAction
		self.askMember = askMember
	
	def run(self):
		book = self.book
		lock = self.lock
		whoToAsk = _setWhoToAsk(self.user, self.whoToAsk, self.book, self.connectAll, self.maxConnection)
		
		http_client = tornado.httpclient.HTTPClient()
		_body = 'userName=' + escape.url_escape(self.user.name)
		_body += '&userPubKey=' + escape.url_escape(self.user.pubKey)
		_body += '&host=' + escape.url_escape(self.user.host)
		_body += '&port=' + escape.url_escape(str(self.user.port))
		_body += '&invitation=' + escape.url_escape(self.user.invitation if self.user.invitation is not None else ' ')
		_body += '&approverID=' + escape.url_escape(self.user.approverID if self.user.approverID is not None else ' ')
		_body += '&bookID=' + escape.url_escape(self.book.getID())
		_body += '&password=' + escape.url_escape(_authCode(self.user))
		for user in whoToAsk:
			try:
				address = 'http://' + str(user.host) + ':' + str(user.port)
				if self.askMember:
					response = http_client.fetch(address + '/members', method = 'POST', body = _body)
					members = escape.json_decode(response.body)
					_updateMembers(members, self.user, book, lock, address)
				if self.askAction:
					response = http_client.fetch(address + '/versions', method = 'POST', body = _body)
					versions = escape.json_decode(response.body)
					_updateActions(versions, self.user, book, lock, address)
			except tornado.httpclient.HTTPError as e:
				#todo: log
				print("Error:" + str(e))
				pass
			except ValueError:
				print('ValueError')
			

class _QuackServer(threading.Thread):
	def __init__(self, iam, books, lock):
		super(_QuackServer, self).__init__()
		self.iam = iam
		self.books = books
		self.lock = lock
	
	def run(self):
		iam = self.iam
		books = self.books
		lock = self.lock

		class Main(tornado.web.RequestHandler):
			def get(self):
				self.write(''
				'<html><head><title>ahiru server</title></head><body>'
				'<form action="/" method="post">'
				'userName: <input type="text" name="userName"><br />'
				'userPubKey: <input type="text" name="userPubKey"><br />'
				'invitation: <input type="text" name="invitation"> (optional)<br />'
				'approverID: <input type="text" name="approverID"> (optional)<br />'
				'<input type="submit" />'
				'</form></body></html>')

			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"))
				self.write(''
				'<html><head><title>ahiru server</title></head><body>'
				'name: <span id="name">' + iam.name + '</span><br />'
				'pubKey: <span id="pubKey">' + iam.pubKey + '</span><br />'
				'i\'m opening following books:<br />')
				for ID in books.keys():
					self.write(books[ID].title + '<br />')
				self.write('</body></html>')

		class Join(tornado.web.RequestHandler):
			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"), host = self.get_argument('host'), port = int(self.get_argument('port')))
				bookID = self.get_argument("bookID")
				lock.acquire()
				if bookID not in books:
					lock.release()
					self.finish()
					return
				b = books[bookID]
				if b.isMember(user) and _auth(b.members[user.ID()], self.get_argument("password")):
					self.write({'owner':b.owner.toDict(), 'title':b.title, 'signature':b.signature, 'createdAt':b.createdAt})
					b.addMember(iam, user)
				lock.release()

		class Members(tornado.web.RequestHandler):
			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"), host = self.get_argument('host'), port = int(self.get_argument('port')), invitation = self.get_argument('invitation'), approverID = self.get_argument('approverID'))
				bookID = self.get_argument("bookID")
				lock.acquire()
				if bookID not in books:
					lock.release()
					self.finish()
					return
				b = books[bookID]
				if b.isMember(user) and _auth(b.members[user.ID()], self.get_argument("password")):
					m = b.members
					self.write({ID: m[ID].toDict() for ID in m})
				lock.release()

		class NewMembers(tornado.web.RequestHandler):
			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"), host = self.get_argument('host'), port = int(self.get_argument('port')), invitation = self.get_argument('invitation'), approverID = self.get_argument('approverID'))
				bookID = self.get_argument("bookID")
				lock.acquire()
				if bookID not in books:
					lock.release()
					self.finish()
					return
				b = books[bookID]
				if b.isMember(user) and _auth(b.members[user.ID()], self.get_argument('password')):
					lock.release()
					client = _QuackClient(iam, b, lock, whoToAsk = {user}, askAction = False, askMember = True)
					client.start()
				else:
					lock.release()

		class Versions(tornado.web.RequestHandler):
			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"), host = self.get_argument('host'), port = int(self.get_argument('port')), invitation = self.get_argument('invitation'), approverID = self.get_argument('approverID'))
				lock.acquire()
				b = books[self.get_argument("bookID")]
				if b.isMember(user) and _auth(b.members[user.ID()], self.get_argument('password')):
					v = b.versions
					self.write({str(ID):v[ID] for ID in v})
				lock.release()

		class NewActions(tornado.web.RequestHandler):
			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"), host = self.get_argument('host'), port = int(self.get_argument('port')), invitation = self.get_argument('invitation'), approverID = self.get_argument('approverID'))
				bookID = self.get_argument("bookID")
				lock.acquire()
				if bookID not in books:
					lock.release()
					self.finish()
					return
				b = books[bookID]
				if b.isMember(user) and _auth(b.members[user.ID()], self.get_argument('password')):
					lock.release()
					client = _QuackClient(iam, b, lock, whoToAsk = {user}, askAction = True, askMember = False)
					client.start()
				else:
					lock.release()

		class _Action(tornado.web.RequestHandler):
			def post(self):
				user = User(self.get_argument("userName"), self.get_argument("userPubKey"), host = self.get_argument('host'), port = int(self.get_argument('port')), invitation = self.get_argument('invitation'), approverID = self.get_argument('approverID'))
				bookID = self.get_argument("bookID")
				lock.acquire()
				if bookID not in books:
					lock.release()
					self.finish()
					return
				b = books[bookID]
				if b.isMember(user) and _auth(b.members[user.ID()], self.get_argument('password')):
					lock.release()
					authorID = self.get_argument("authorID")
					no = int(self.get_argument("no"))
					lock.acquire()
					if (authorID, no) not in b.actions:
						lock.release()
						self.finish()
						return
					action = b.actions[Action.actionID(authorID, no)]
					self.write(b.actions[Action.actionID(authorID, no)].toDict())
					lock.release()
				else:
					lock.release()

		class StopServer(tornado.web.RequestHandler):
			#todo: auth
			def get(self):
				self.write('')
				self.ioloop.stop()

		application = tornado.web.Application([
			(r"/", Main),
			(r"/members", Members),
			(r"/versions", Versions),
			(r"/action", _Action),
			(r"/newmembers", NewMembers),
			(r"/newactions", NewActions),
			(r"/stopserver", StopServer),
			(r"/join", Join),
		])

		self.ioloop = tornado.ioloop.IOLoop()
		application.listen(iam.port, io_loop = self.ioloop)
		self.ioloop.start()


class Ahiru:
	def __init__(self, user = None, name = None, pubKey = None, secKey = None, host = '127.0.0.1', port = 2009, path = None, newMemberFunc = None, newActionFunc = None):
		assert user is not None or name is not None and pubKey is not None and secKey is not None and host is not None and port is not None
		assert user is None or isinstance(user, User) 
		assert user is not None\
		       or isinstance(name, str) and isinstance(pubKey, str) and isinstance(secKey, str) and isinstance(host, str) and isinstance(port, int)
		assert newMemberFunc is None or isinstance(newMemberFunc, types.FunctionType)
		assert newActionFunc is None or isinstance(newActionFunc, types.FunctionType)

		self.newMemberFunc = newMemberFunc
		self.newActionFunc = newActionFunc
		if path is None:
			self.path = os.path.join('.', '')
		else:
			self.path = path
		self.books = {}
		if user is not None:
			self.user = user
		else:
			self.user = User(name, pubKey, secKey, host = host, port = port)
		self.quacking = False
		self.lock = threading.Lock()
		self.addresses = {}
	
	def setNewMemberFunc(self, f):
		assert f is None or isinstance(f, types.FunctionType)
		self.newMemberFunc = f
	
	def setNewActionFunc(self, f):
		assert f is None or isinstance(f, types.FunctionType)
		self.newActionFunc = f

	def create(self, title):
		if Book.ID(self.user, title) in self.books:
			raise BookIDExists()
		b = Book.create(self.user, title, self.path)
		self.books[b.getID()] = b
		return b.getID()

	def open(self, ID):
		b = Book.open(ID, self.path)
		self.books[ID] = b

	def quack(self):
		# start chorus with other Ahirus
		if self.quacking:
			return
		self.server = _QuackServer(self.user, self.books, self.lock)
		self.server.start()
		for book in self.books.values():
			client = _QuackClient(self.user, book, self.lock)
			client.start()
		self.quacking = True

	def stop(self):
		# stop quack
		self.server.ioloop.stop()
		self.quacking = False

	def get(self, bookID, ID):
		return self.books[bookID].get(ID)
	
	def getLatests(self, bookID, ID):
		return self.books[bookID].getLatests(ID)
	
	def put(self, bookID, data, comment = None):
		self.lock.acquire()
		action = self.books[bookID].put(self.user, data, comment)
		self.lock.release()
		if self.quacking:
			client = _QuackClient(self.user, self.books[bookID], self.lock, connectAll = True)
			client.start()
		return action
	
	def update(self, bookID, data, parent, comment = None):
		assert isinstance(parent, tuple) or isinstance(parent, Action)
		self.lock.acquire()
		action = self.books[bookID].update(self.user, data, parent, comment)
		self.lock.release()
		if self.quacking:
			client = _QuackClient(self.user, self.books[bookID], self.lock, connectAll = True)
			client.start()
		return action

	def addMember(self, bookID, comer):
		assert isinstance(comer, User)
		self.books[bookID].addMember(self.user, comer)

	def join(self, bookID, host, port, path = ''):
		client = _JoinClient(self.user, self.books, self.lock, bookID, host, port, path)
		client.start()

