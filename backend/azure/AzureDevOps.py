from pydantic import BaseModel
import os
from dotenv import load_dotenv


class AzureDevOpsMgr(BaseModel):
	"""
	A simple class to manage the Azure DevOps issues, stories and manage updates.
	"""

	def get_stories(self):
		raise NotImplementedError

	def get_work_items(self):
		raise NotImplementedError

	def get_tasks(self):
		raise NotImplementedError
