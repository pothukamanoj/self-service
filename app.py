import os
import uuid
import json
from flask import Flask, render_template, request

app = Flask(__name__)

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MODULES_DIR = os.path.join(BASE_DIR, 'modules')
GENERATED_DIR = os.path.join(BASE_DIR, 'generated_projects')

# Function to load all modules from the 'modules/' directory
def load_modules():
    modules = {}
    for module_name in os.listdir(MODULES_DIR):
        module_path = os.path.join(MODULES_DIR, module_name)
        if os.path.isdir(module_path):
            variables_tf_file = os.path.join(module_path, 'variables.tf')
            if os.path.exists(variables_tf_file):
                variables = extract_variables_from_tf(variables_tf_file)
                modules[module_name] = {
                    'fields': variables['fields'],
                    'resource': f'azurerm_{module_name}',  # For generating resource names
                    'required': variables['required'],
                    'optional': variables['optional']
                }
    return modules

# Function to extract required and optional variables from 'variables.tf'
def extract_variables_from_tf(variables_tf_path):
    required = []
    optional = []
    with open(variables_tf_path, 'r') as file:
        lines = file.readlines()
    
    for line in lines:
        if "variable" in line:
            # Capture the variable name
            var_name = line.split('"')[1]
            # Now find the following lines for description and type
            description = ''
            var_type = 'string'  # Default type
            for next_line in lines[lines.index(line)+1:]:
                if 'description' in next_line:
                    description = next_line.split('"')[1]
                if 'type' in next_line:
                    var_type = next_line.split('=')[1].strip().replace('"', '')
                if 'default' in next_line:
                    # If there is a default, it's optional
                    optional.append({'name': var_name, 'description': description, 'type': var_type})
                    break
                if '}' in next_line:
                    # If there is no default, it's required
                    required.append({'name': var_name, 'description': description, 'type': var_type})
                    break

    return {
        'fields': [var['name'] for var in required + optional],
        'required': required,
        'optional': optional
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    modules = load_modules()
    if request.method == 'POST':
        selected_modules = request.form.getlist('modules')
        use_existing = request.form.get('use_existing') == 'on'
        return render_template('form.html', modules=selected_modules, available_modules=modules, use_existing=use_existing)
    return render_template('index.html', modules=modules)

@app.route('/generate', methods=['POST'])
def generate():
    user_inputs = request.form.to_dict()
    selected_modules = user_inputs.pop('selected_modules').split(',')
    
    # Check if 'use_existing' is in the form, if not, set it to False
    use_existing = user_inputs.get('use_existing') == 'on'

    # Create new project folder
    project_id = str(uuid.uuid4())
    project_path = os.path.join(GENERATED_DIR, project_id)
    os.makedirs(project_path, exist_ok=True)

    main_tf_content = ""
    variables_tf_content = ""

    # Generate main.tf content
    modules = load_modules()

    for module in selected_modules:
        inputs = {field: user_inputs.get(f"{module}_{field}") for field in modules[module]["fields"]}
        
        if use_existing:
            main_tf_content += generate_module_block(module, inputs)
            variables_tf_content += generate_variables_block(module, modules[module]["required"], modules[module]["optional"])
        else:
            main_tf_content += generate_resource_block(module, inputs)
            variables_tf_content += generate_variables_block(module, modules[module]["required"], modules[module]["optional"])

    # Save main.tf and variables.tf
    main_tf_file = os.path.join(project_path, 'main.tf')
    variables_tf_file = os.path.join(project_path, 'variables.tf')
    
    with open(main_tf_file, 'w') as f:
        f.write(main_tf_content)
    
    with open(variables_tf_file, 'w') as f:
        f.write(variables_tf_content)

    # Display the generated code on the result page
    return render_template('result.html', project_id=project_id, terraform_code=main_tf_content)

def generate_module_block(module, inputs):
    block = f'module "{module}" {{\n'
    block += f'  source = "../modules/{module}"\n'
    for key, value in inputs.items():
        if value:
            block += f'  {key} = "{value}"\n'
    block += '}\n\n'
    return block

def generate_resource_block(module, inputs):
    resource_type = f'azurerm_{module}'
    block = f'resource "{resource_type}" "{module}" {{\n'
    for key, value in inputs.items():
        if value:
            block += f'  {key} = "{value}"\n'
    block += '}\n\n'
    return block

def generate_variables_block(module, required, optional):
    block = ''
    for var in required + optional:
        block += f'variable "{module}_{var["name"]}" {{\n'
        block += f'  description = "{var["description"]}"\n'
        block += f'  type        = {var["type"]}\n'
        if var in optional:
            block += '  default     = ""\n'
        block += '}\n\n'
    return block

if __name__ == '__main__':
    os.makedirs(GENERATED_DIR, exist_ok=True)
    app.run(debug=True)
