#! /usr/bin/python

def testrun():
	print "this is a testrun method"
	print "the end..."
	for i in range(10):
		print i
	def inner():
		a = 1+1
		return a
	print inner()


testrun()


