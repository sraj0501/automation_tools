import os
from dotenv import load_dotenv


class AzureDevOpsMgr:
	"""
	A simple class to manage the Azure DevOps issues, stories and manage updates.
	"""
	def __int__(self):
		self.org = None
		self.project = None
		self.user = None

	def get_stories(self):
		raise NotImplementedError

	def get_work_items(self):
		raise NotImplementedError

	def get_tasks(self):
		raise NotImplementedError
