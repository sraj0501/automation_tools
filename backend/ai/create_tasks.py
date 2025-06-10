import ollama
import json
import pandas as pd
from typing import List, Dict, Any
import re

class TaskGenerator:
    def __init__(self, model_name: str = "llama3.1"):
        """
        Initialize the TaskGenerator with an Ollama model
        
        Args:
            model_name: The name of the Ollama model to use (default: llama3.1)
        """
        self.model_name = model_name
        self.client = ollama.Client()
        
    def generate_tasks(self, 
                      requirements: str, 
                      constraints: str, 
                      existing_tasks: List[Dict] = None,
                      assignee: str = "Shashank Raj shashank.raj@latentbridge.com",
                      parent_work_item_id: str = "9759",
                      starting_work_item_id: int = 9760) -> List[Dict]:
        """
        Generate project tasks based on requirements and constraints
        
        Args:
            requirements: The project requirements and component breakdown
            constraints: Project constraints and specifications
            existing_tasks: List of existing tasks (optional)
            assignee: Who to assign the tasks to
            parent_work_item_id: Parent work item ID for all tasks
            starting_work_item_id: Starting ID for new work items
            
        Returns:
            List of dictionaries containing task information
        """
        
        # Prepare the prompt for the LLM
        prompt = self._create_prompt(requirements, constraints, existing_tasks)
        
        # Generate response using Ollama
        response = self.client.chat(model=self.model_name, messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ])
        
        # Parse the response to extract tasks
        tasks = self._parse_response(response['message']['content'], 
                                   assignee, 
                                   parent_work_item_id, 
                                   starting_work_item_id)
        
        return tasks
    
    def _create_prompt(self, requirements: str, constraints: str, existing_tasks: List[Dict] = None) -> str:
        """Create a detailed prompt for task generation"""
        
        existing_tasks_text = ""
        if existing_tasks:
            existing_tasks_text = "\n\nExisting tasks already created:\n"
            for i, task in enumerate(existing_tasks, 1):
                existing_tasks_text += f"{i}. {task.get('title', 'Untitled Task')}\n"
        
        prompt = f"""
You are a project manager breaking down software development requirements into specific, actionable tasks.

PROJECT REQUIREMENTS:
{requirements}

PROJECT CONSTRAINTS:
{constraints}

{existing_tasks_text}

Based on the requirements and constraints above, generate a comprehensive list of remaining tasks needed to complete the project. 

For each task, provide:
1. A clear, specific title that describes what needs to be done
2. A brief description of the task (1-2 sentences)
3. The category/component it belongs to (e.g., "User Input Parsing", "Query Validation", etc.)

Format your response as a structured list where each task is clearly numbered and contains:
- Title: [Clear, actionable task title]
- Description: [Brief description of what the task involves]
- Category: [Which component/phase this belongs to]

Focus on:
- Breaking down complex processes into manageable tasks
- Ensuring logical sequence and dependencies
- Including error handling, testing, and monitoring tasks
- Covering all aspects mentioned in the requirements
- Not duplicating existing tasks

Generate tasks that are specific, measurable, and implementable.
"""
        
        return prompt
    
    def _parse_response(self, response_text: str, assignee: str, parent_work_item_id: str, starting_id: int) -> List[Dict]:
        """Parse the LLM response and create structured task dictionaries"""
        
        tasks = []
        current_id = starting_id
        
        # Split response into lines and process
        lines = response_text.split('\n')
        current_task = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for task titles (usually numbered or with bullet points)
            if re.match(r'^\d+\.', line) or line.startswith('- ') or line.startswith('* '):
                # If we have a previous task, save it
                if current_task.get('title'):
                    tasks.append(self._create_task_dict(current_task, assignee, parent_work_item_id, current_id))
                    current_id += 1
                
                # Start new task
                current_task = {'title': re.sub(r'^\d+\.\s*|\-\s*|\*\s*', '', line)}
                
            # Look for title/description patterns
            elif line.lower().startswith('title:'):
                current_task['title'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('description:'):
                current_task['description'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('category:'):
                current_task['category'] = line.split(':', 1)[1].strip()
            elif current_task.get('title') and not current_task.get('description'):
                # If we have a title but no description, this might be the description
                if len(line) > 20:  # Reasonable description length
                    current_task['description'] = line
        
        # Don't forget the last task
        if current_task.get('title'):
            tasks.append(self._create_task_dict(current_task, assignee, parent_work_item_id, current_id))
        
        return tasks
    
    def _create_task_dict(self, task_data: Dict, assignee: str, parent_work_item_id: str, work_item_id: int) -> Dict:
        """Create a structured task dictionary matching the required format"""
        
        return {
            'Work Item Type': 'Task',
            'Title': task_data.get('title', 'Unnamed Task'),
            'Assigned To': assignee,
            'State': 'To Do',
            'Tags': 'Automation',
            'Work Item ID': str(work_item_id),
            'DevOps URL': '',
            'Iteration Path': '',
            'Parent Work Item ID': parent_work_item_id,
            'Description': task_data.get('description', ''),
            'Category': task_data.get('category', '')
        }
    
    def export_to_csv(self, tasks: List[Dict], filename: str = "generated_tasks.csv"):
        """Export tasks to CSV file"""
        df = pd.DataFrame(tasks)
        df.to_csv(filename, index=False)
        print(f"Tasks exported to {filename}")
    
    def export_to_markdown(self, tasks: List[Dict], filename: str = "generated_tasks.md"):
        """Export tasks to markdown table format"""
        df = pd.DataFrame(tasks)
        # Select only the main columns for the table
        table_columns = ['Work Item Type', 'Title', 'Assigned To', 'State', 'Tags', 'Work Item ID', 'DevOps URL', 'Iteration Path', 'Parent Work Item ID']
        table_df = df[table_columns]
        
        markdown_content = table_df.to_markdown(index=False)
        
        with open(filename, 'w') as f:
            f.write(markdown_content)
        print(f"Tasks exported to {filename}")
    
    def print_tasks(self, tasks: List[Dict]):
        """Print tasks in a readable format"""
        for i, task in enumerate(tasks, 1):
            print(f"\n{i}. {task['Title']}")
            print(f"   ID: {task['Work Item ID']}")
            if task.get('Description'):
                print(f"   Description: {task['Description']}")
            if task.get('Category'):
                print(f"   Category: {task['Category']}")

# Example usage
def main():
    # Initialize the task generator
    generator = TaskGenerator(model_name="llama3.1")  # Change model as needed
    
    # Define your requirements
    requirements = """
    User Input Parsing:
    * The user enters a query about the given table. 
    * The metadata for the table, along with the column definition is already stored in the Postgres DB. When called for action, the metadata is a JSON response.
    * The users' query along with the metadata and column definition is passed to the LLM to generate a SQL query. 
    Query validation:
    *  Once the SQL is generated, the same, along with the original user query and metadata context is passed to the LLM. 
    * The LLM then decided whether the query is correct based on the provided input.
    * If correct, the SQL along with the user query is stored temporarily. 
    * If not, the top 3 steps are repeated 3 times to generate the correct query. 
    * If correct query is not generated after 3 times, the **process exits**.
    * If the SQL and the user query are in sync, then the user query, table metadata and SQL are stored temporarily is a csv. 
    Query Execution:
    * The SQL is executed against the said database ( 3 tries with a timeout of 30 seconds each). 
    * If an output is generated in the given window, the same is stored along with the original query and the SQL generated. 
    * If not, the **process exits.** 
    Final Output Parsing:
    * In this step, the original user query, along with the generated SQL and the output is passed to an LLM to generate a chatbot response.
    * The LLM then generates a response which is based on predefined prompts.
    * Once the response is generated, it is parsed in a JSON format and sent as final output.
    """
    
    constraints = """
    * There is no front end component and only one API.
    * All tasks should be backend-focused.
    * Include error handling for process exit scenarios.
    * Implement proper timeout and retry mechanisms.
    * Include logging and monitoring capabilities.
    """
    
    existing_tasks = [
        {"title": "Augment Extract Metadata Process for Postgres"},
        {"title": "Table Metadata Validation"},
        {"title": "Create Backend API for Extract Process"},
        {"title": "Front End for the Extract Process"},
        {"title": "API to validate Table Metadata"},
        {"title": "Accept User Query and format for LLM"},
        {"title": "Automate end-to-end flow from user input to chatbot response"}
    ]
    
    # Generate tasks
    print("Generating tasks using Ollama...")
    tasks = generator.generate_tasks(
        requirements=requirements,
        constraints=constraints,
        existing_tasks=existing_tasks,
        assignee="Shashank Raj shashank.raj@latentbridge.com",
        parent_work_item_id="9759",
        starting_work_item_id=9760
    )
    
    # Display results
    print(f"\nGenerated {len(tasks)} tasks:")
    generator.print_tasks(tasks)
    
    # Export to files
    generator.export_to_csv(tasks)
    generator.export_to_markdown(tasks)
    
    return tasks

if __name__ == "__main__":
    main()