from tkinter.font import names

from fastapi import FastAPI, Body
from db.models import *
from pydantic import Field

app = FastAPI()

class Employees:
	name: str
	emailId: str
	employeeId: str = None
	githubHandle: str = None

	def __init__(self, name, email, empid, githubHandle):
		self.name = name
		self.emailId = email
		self.employeeId = empid
		self.githubHandle = githubHandle

Employee_list: list = []


@app.get("/")
async def main():
	return {"message": "hello"}

@app.get("/employees")
async def list_employees():
	return Employee_list

@app.post("/add-employee")
async def create_employee(emp: Employee):
	new_emp = Employee(**emp.model_dump())
	Employee_list.append(new_emp)

