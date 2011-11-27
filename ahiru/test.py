import time
import unittest
from user import *
from action import *
from book import *
from manager import *

class ActionT(unittest.TestCase):
	def test_new(self):
		data = 'hello'
		user = User('taro', 'hello', 'sec')
		root = Action.new(bookID = 'book1', user = user, no = 1, act = Action.Insert, data = data)
		self.assert_(isinstance(root, Action))
	
	def test_newChild(self):
		data = 'hello'
		user = User('taro', 'hello', 'sec')
		root = Action.new(bookID = 'book1', user = user, no = 1, act = Action.Insert, data = data)
		child = Action.new(bookID = 'book1', user = user, no = 2, act = Action.Update, data = data, parent = root)
		self.assertEqual(child.root, root.ID())
		self.assertEqual(child.parent, root.ID())

	def test_newGrandChild(self):
		data = 'hello'
		user = User('taro', 'hello', 'sec')
		root = Action.new(bookID = 'book1', user = user, no = 1, act = Action.Insert, data = data)
		child = Action.new(bookID = 'book1', user = user, no = 2, act = Action.Update, data = data, parent = root)
		u = User('xyz', 'helloo', 'seco')
		grandchild = Action.new(bookID = 'book1', user = u, no = 1, act = Action.Update, data = data, parent = child)
		self.assertEqual(grandchild.root, root.ID())
		self.assertEqual(grandchild.parent, child.ID())

	def test_newFromDict(self):
		data = 'hello'
		user = User('taro', 'hello', 'sec')
		action = Action.new(bookID = 'book1', user = user, no = 1, act = Action.Insert, data = data)
		action2 = Action.newFromDict('book1', user, **action.toDict())
		self.assert_(isinstance(action2, Action))

	def test_newFromDict_invalidSign(self):
		data = 'hello'
		user = User('taro', 'hello', 'sec')
		action = Action.new(bookID = 'book1', user = user, no = 1, act = Action.Insert, data = data)
		d = action.toDict()
		d['sign'] = ''
		self.assertRaises(InvalidSign, Action.newFromDict, 'book1', user, d['userID'], d['no'], d['act'], d['data'], d['comment'], d['time'], d['parent'], d['root'], d['sign'])


class UserT(unittest.TestCase):
	def test_User(self):
		user = User('taro', 'helloPublic')
		self.assert_(isinstance(user, User))

	def test_encrypt_and_decrypt(self):
		user = User('taro', 'helloPublic', 'securityKey')
		text = 'hello world!'
		self.assertEqual(user.decrypt(user.encrypt(text)), text)

	def test_ID(self):
		user = User('taro', 'helloPublic', 'securityKey')
		self.assertEqual(user.ID(), hashlib.sha256(str(('taro', 'helloPublic')).encode('utf8')).hexdigest())
		
	def test_invite(self):
		user = User('taro', 'helloPublic', 'securityKey')
		user2 = User('jiro', 'abc')
		user.invite(user2, 'bookID')
		self.assertEqual(User.isValidInvitation(user, user2, 'bookID'), True)
	
	def test_isValidInvitation(self):
		user = User('taro', 'helloPublic', 'securityKey')
		user2 = User('jiro', 'abc')
		user.invite(user2, 'bookID')
		self.assertEqual(User.isValidInvitation(user, user2, 'bookID'), True)
		self.assertEqual(User.isValidInvitation(user, user2, 'bookIDD'), False)
		user3 = User('hanako', '12344134')
		self.assertEqual(User.isValidInvitation(user3, user2, 'bookID'), False)

	def test_User_errorCases(self):
		self.assertRaises(TypeError, User, 'taro')
		self.assertRaises(AssertionError, User, 'taro', 1)
		self.assertRaises(AssertionError, User, 1, 'helloPublic')
		user = User('taro', 'helloPublic')
		self.assertRaises(NoSecKey, user.encrypt, 'hello')


class BookT(unittest.TestCase):
	def test_Book(self):
		book = Book()
	
	def test_create(self):
		book = Book()
		taro = User('taro', 'abcde', '123456')
		hanako = User('hanako', '123@#')
		book.create(taro, 'testBook', '.')
		self.assert_(True)
		
	def test_open(self):
		book = Book()
		taro = User('taro', 'abcde', '123456')
		book.create(taro, 'testBook', '.')

		book2 = Book()
		book2.open(title = 'testBook', owner = taro, path = '.')
		
		book = Book()
		self.assertRaises(InvalidBookFile, book.open, 'testBook_kjhsadfiuywerbklfdsakljhsdfiuyadsfkjh', '~')
	
	def test_get(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		book.create(taro, 'testBook', '.')
		ldata = [1, 2, 3]
		comment = "hello i'm taro"
		ID = book.put(taro, ldata, comment)
		
		action = book.get(ID)
		self.assertTrue(isinstance(action, Action))

		self.assertEqual(book.get(taro.ID(), 1), 
		                 book.get((taro.ID(), 1)))
	
	def test_getLatests(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		book.create(taro, 'testBook', '.')
		ldata = [1, 2, 3]
		comment = "hello i'm taro"
		ID = book.put(taro, ldata, comment)
		
		action1 = book.get(ID)
		self.assertEqual(book.getLatests(ID), [action1])
		self.assertEqual(book.getLatests(ID), book.getLatests(ID[0], ID[1]))
	
	def test_put(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		hanako = User('hanako', '123@#')
		book.create(taro, 'testBook', '.')

		ldata = [1, 2, 3]
		comment = "hello i'm taro"
		ID = book.put(taro, ldata, comment)
		self.assertEqual(ID, (taro.ID(), 1))
		action = book.get(ID)
		self.assertEqual(action.userID, taro.ID())
		self.assertEqual(action.no, 1)
		self.assertEqual(action.act, Action.Insert)
		self.assertEqual(action.data, ldata)
		self.assertEqual(action.comment, comment)
		self.assertEqual(action.parent, None)
		self.assertEqual(action.root, action.ID())
		self.assertEqual(book.getLatests(ID), [action])

		self.assertRaises(NonMember, book.put, hanako, ldata)
	
	def test_update(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		book.create(taro, 'testBook', '.')
		ldata = [1, 2, 3]
		comment = "hello i'm taro"
		ID = book.put(taro, ldata, comment)
		action1 = book.get(ID)

		ddata = {1:'one', 'two':2}
		ID2 = book.update(taro, ddata, action1, comment)
		self.assertEqual(ID2, (taro.ID() ,2))
		action2 = book.get(ID2)
		self.assertEqual(action2.userID, taro.ID())
		self.assertEqual(action2.act, Action.Update)
		self.assertEqual(action2.data, ddata)
		self.assertEqual(action2.comment, comment)
		self.assertEqual(action2.parent, action1.ID())
		self.assertEqual(action2.root, action1.ID())
		
		sdata = 'hogehoge'
		ID3 = book.update(taro, sdata, ID, comment)
		self.assertEqual(ID3, (taro.ID(), 3))
		action3 = book.get(taro.ID(), 3)
		self.assertEqual(action3.userID, taro.ID())
		self.assertEqual(action3.act, Action.Update)
		self.assertEqual(action3.data, sdata)
		self.assertEqual(action3.comment, comment)
		self.assertEqual(action3.parent, action1.ID())
		self.assertEqual(action3.root, action1.ID())

		self.assertEqual(book.getLatests(taro.ID(), 1), [action3, action2])

		ID4 = book.update(taro, sdata, ID2, comment)
		self.assertEqual(ID4, (taro.ID(), 4))
		action4 = book.get(taro.ID(), 4)
		self.assertEqual(action4.userID, taro.ID())
		self.assertEqual(action4.act, Action.Update)
		self.assertEqual(action4.data, sdata)
		self.assertEqual(action4.comment, comment)
		self.assertEqual(action4.parent, action2.ID())
		self.assertEqual(action4.root, action1.ID())

		self.assertEqual(book.getLatests(taro.ID(), 1), [action4, action3])
		self.assertRaises(KeyError, book.getLatests, taro.ID(), 2)

	def test_addMember(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		book.create(taro, 'testBook', '.')

		hanako = User('hanako', '123@#')
		jiro = User('jiro', 'oiuwre')
		self.assertRaises(NoRight, book.addMember, hanako, jiro)
		book.addMember(taro, jiro)
		self.assertTrue(jiro.ID() in book.members)

	def test_isMember(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		book.create(taro, 'testBook', '.')
		hanako = User('hanako', '123@#')
		jiro = User('jiro', 'oiuwre')
		book.addMember(taro, jiro)
		self.assertEqual(book.isMember(taro), True)
		self.assertEqual(book.isMember(jiro), True)
		self.assertEqual(book.isMember(hanako), False)

	def test_putAction(self):
		taro = User('taro', 'abcde', '123456')
		book = Book()
		book.create(taro, 'testBook', '.')
		action = Action.new(bookID = book.ID(), user = taro, no = 1, act = Action.Insert, data = 'hoge')
		
		ID = book.putAction(taro, action.toDict())
		self.assertEqual(ID, (taro.ID(), 1))
		a = book.get(ID)
		self.assertEqual(action.userID, a.userID)
		self.assertEqual(action.act, a.act)
		self.assertEqual(action.data, a.data)
		self.assertEqual(action.comment, a.comment)
		self.assertEqual(action.parent, a.parent)
		self.assertEqual(action.root, a.root)
		self.assertEqual(book.getLatests(ID), [a])
		
		action2 = Action.new(bookID = book.ID(), user = taro, no = 2, act = Action.Update, data = 'fuga', parent = a)
		ID2 = book.putAction(taro, action2.toDict())
		a2 = book.get(ID2)
		self.assertEqual(book.getLatests(ID), [a2])


class AhiruT(unittest.TestCase):
	def test_Ahiru_1(self):
		ahiru = Ahiru(name = 'taro', pubKey = 'abc', secKey = '123')
		self.assert_(True)
		self.assertEqual(ahiru.user.name, 'taro')
		self.assertEqual(ahiru.user.pubKey, 'abc')
		self.assertEqual(ahiru.user.secKey, '123')

	def test_Ahiru_2(self):
		taro = User('taro', 'abc', '123')
		def f(): pass
		def g(): pass
		ahiru = Ahiru(user = taro, newMemberFunc = f, newActionFunc = g, path='hoge/fuge/')
		self.assert_(True)
		self.assertEqual(ahiru.user.name, 'taro')
		self.assertEqual(ahiru.user.pubKey, 'abc')
		self.assertEqual(ahiru.user.secKey, '123')
		self.assertEqual(ahiru.newMemberFunc, f)
		self.assertEqual(ahiru.newActionFunc, g)
		self.assertEqual(ahiru.path, 'hoge/fuge/')

	def test_setNewMemberFunc(self):
		ahiru = Ahiru(name = 'taro', pubKey = 'abc', secKey = '123')
		def f(): pass
		ahiru.setNewMemberFunc(f)
		self.assertEqual(ahiru.newMemberFunc, f)
		
	def test_setNewActionFunc(self):
		ahiru = Ahiru(name = 'taro', pubKey = 'abc', secKey = '123')
		def f(): pass
		ahiru.setNewActionFunc(f)
		self.assertEqual(ahiru.newActionFunc, f)
		
	def test_create(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2009)
		def f(): pass
		def g(): pass
		ahiru = Ahiru(user = taro, newMemberFunc = f, newActionFunc = g)
		testBookID = ahiru.create('test book')
		self.assert_(True)
	
	def test_open(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2009)
		def f(): pass
		def g(): pass
		ahiru = Ahiru(user = taro, newMemberFunc = f, newActionFunc = g)
		testBookID = ahiru.create('test book')

		ahiru = Ahiru(name = 'taro', pubKey = 'abc', secKey = '123')
		b = ahiru.open(testBookID)
		self.assert_(True)
	
	def test_quack(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2009)
		def f(): pass
		def g(): pass
		ahiru = Ahiru(user = taro, newMemberFunc = f, newActionFunc = g)
		testBookID = ahiru.create('test book')

		ahiru.quack()
		self.assertEqual(ahiru.quacking, True)
		time.sleep(1)
		ahiru.stop()
		self.assertEqual(ahiru.quacking, False)

	def test_addMember(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2009)
		def f(): pass
		def g(): pass
		ahiru = Ahiru(user = taro, newMemberFunc = f, newActionFunc = g)
		testBookID = ahiru.create('test book')

		hanako = User('hanako', 'oiuawer')
		ahiru.addMember(testBookID, taro)
		self.assert_(True)

class QuackT(unittest.TestCase):
	def test_2members_0action(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2010)
		ahiru = Ahiru(user = taro)
		bookID = ahiru.create('test book')
		ahiru.quack()
		hanako = User('hanako', 'hhh', 'ggg', '127.0.0.1', 2011)
		ahiru.addMember(bookID, hanako)
		ahiruH = Ahiru(user = hanako)
		time.sleep(1)
		ahiruH.join(bookID, '127.0.0.1', 2010)
		time.sleep(1)
		ahiruH.quack()
		time.sleep(1)
		ahiru.stop()
		ahiruH.stop()
		
		bookT = ahiru.books[bookID]
		bookH = ahiruH.books[bookID]
		self.assertEqual(bookH.title, bookT.title)
		self.assertEqual(bookH.signature, bookT.signature)
		self.assertEqual(bookH.createdAt, bookT.createdAt)
		self.assertEqual(bookH.owner.name, taro.name)
		self.assertEqual(bookH.owner.pubKey, taro.pubKey)
		self.assertEqual(bookH.owner.approverID, taro.approverID)
		self.assertEqual(bookH.owner.host, taro.host)
		self.assertEqual(bookH.owner.port, taro.port)
		self.assertEqual(bookH.owner.invitation, taro.invitation)
		self.assertEqual(len(ahiru.books[bookID].members), 2)
		self.assertEqual(len(bookH.members), 2)
		self.assertTrue(taro.ID() in bookH.members)
		self.assertTrue(hanako.ID() in bookH.members)
		self.assertEqual(len(bookH.versions), 2)
		self.assertTrue(taro.ID() in bookH.versions)
		self.assertTrue(hanako.ID() in bookH.versions)
		self.assertEqual(bookH.versions[taro.ID()], 0)
		self.assertEqual(bookH.versions[hanako.ID()], 0)

	def test_2members_1action(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2012)
		ahiru = Ahiru(user = taro)
		bookID = ahiru.create('test book')
		ahiru.quack()
		time.sleep(1)
		actionID = ahiru.put(bookID, 'hello world!')
		hanako = User('hanako', 'hhh', 'ggg', '127.0.0.1', 2013)
		ahiru.addMember(bookID, hanako )
		ahiruH = Ahiru(user = hanako)
		ahiruH.join(bookID, '127.0.0.1', 2012)
		time.sleep(1)
		ahiruH.quack()
		time.sleep(1)
		ahiru.stop()
		ahiruH.stop()
		
		bookT = ahiru.books[bookID]
		bookH = ahiruH.books[bookID]
		self.assertEqual(len(bookH.members), 2)
		self.assertTrue(taro.ID() in bookH.members)
		self.assertTrue(hanako.ID() in bookH.members)
		self.assertEqual(len(bookH.versions), 2)
		self.assertTrue(taro.ID() in bookH.versions)
		self.assertTrue(hanako.ID() in bookH.versions)
		self.assertEqual(bookH.versions[taro.ID()], 1)
		self.assertEqual(bookH.versions[hanako.ID()], 0)
		actionT = ahiru.get(bookID, actionID)
		actionH = ahiruH.get(bookID, actionID)
		self.assertEqual(actionT.userID, actionH.userID)
		self.assertEqual(actionT.act, actionH.act)
		self.assertEqual(actionT.data, actionH.data)
		self.assertEqual(actionT.comment, actionH.comment)
		self.assertEqual(actionT.parent, actionH.parent)
		self.assertEqual(actionT.root, actionH.root)
		self.assertEqual(bookH.getLatests(actionID), [actionH])

	def test_2members_2action(self):
		taro = User('taro', 'abc', '123', '127.0.0.1', 2014)
		ahiru = Ahiru(user = taro)
		bookID = ahiru.create('test book')
		ahiru.quack()
		time.sleep(1)
		actionID = ahiru.put(bookID, 'hello world!')
		hanako = User('hanako', 'hhh', 'ggg', '127.0.0.1', 2015)
		ahiru.addMember(bookID, hanako )
		ahiruH = Ahiru(user = hanako)
		ahiruH.join(bookID, '127.0.0.1', 2014)
		time.sleep(1)
		ahiruH.quack()
		time.sleep(1)
		action2 = ahiruH.update(bookID, 'bye', actionID)
		time.sleep(1)
		ahiru.stop()
		ahiruH.stop()
		
		bookT = ahiru.books[bookID]
		bookH = ahiruH.books[bookID]
		self.assertTrue(hanako.ID() in bookT.versions)
		self.assertEqual(bookT.versions[taro.ID()], 1)
		self.assertEqual(bookT.versions[hanako.ID()], 1)
		self.assertEqual(bookH.versions[taro.ID()], 1)
		self.assertEqual(bookH.versions[hanako.ID()], 1)
		actionT = ahiru.get(bookID, action2)
		actionH = ahiruH.get(bookID, action2)
		self.assertEqual(actionT.userID, actionH.userID)
		self.assertEqual(actionT.act, actionH.act)
		self.assertEqual(actionT.data, actionH.data)
		self.assertEqual(actionT.comment, actionH.comment)
		self.assertEqual(actionT.parent, actionH.parent)
		self.assertEqual(actionT.root, actionH.root)
		self.assertEqual(bookT.getLatests(actionID), [actionT])

if __name__ == "__main__":
	suites = []
	suites.append(unittest.TestLoader().loadTestsFromTestCase(UserT))
	suites.append(unittest.TestLoader().loadTestsFromTestCase(ActionT))
	suites.append(unittest.TestLoader().loadTestsFromTestCase(BookT))
	suites.append(unittest.TestLoader().loadTestsFromTestCase(AhiruT))
	suites.append(unittest.TestLoader().loadTestsFromTestCase(QuackT))
	unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))

