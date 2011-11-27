import tornado.web
import tornado.ioloop

class main1(tornado.web.RequestHandler):
	def get(self):
		self.write('this is main1')

app1 = tornado.web.Application([
	(r"/", main1),
])

app1.listen(2010)

tornado.ioloop.IOLoop.instance().start()

class main2(tornado.web.RequestHandler):
	def get(self):
		self.write('this is main2')

app2 = tornado.web.Application([
	(r"/", main2),
])

app2.listen(2011)

tornado.ioloop.IOLoop.instance().stop()
tornado.ioloop.IOLoop.instance().start()

