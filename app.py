import os
import uuid
from flask import Flask, render_template, request
import hcl
from fuzzywuzzy import process

app = Flask(__name__)

# Define paths
MODULES_DIR = 'terraform_modules'
GENERATED_DIR = 'generated_files'


def load_modules():
    """
    This function scans the modules directory and loads each module's information
    by reading the `variables.tf` file to extract required and optional attributes.
    """
    modules = {}

    for module_name in os.listdir(MODULES_DIR):
        module_path = os.path.join(MODULES_DIR, module_name)
        if os.path.isdir(module_path):
            variables_file = os.path.join(module_path, 'variables.tf')
            if os.path.exists(variables_file):
                with open(variables_file, 'r') as f:
                    try:
                        # Parse the variables.tf using HCL (HashiCorp Configuration Language)
                        parsed_variables = hcl.parse(f.read())
                        required = []
                        optional = []
                        
                        # Classify the variables into required and optional
                        for var, var_data in parsed_variables['variable'].items():
                            var_info = {
                                'name': var,
                                'description': var_data.get('description', 'No description'),
                                'type': var_data.get('type', 'string'),
                                'default': var_data.get('default', None)
                            }
                            if var_info['default'] is None:
                                required.append(var_info)
                            else:
                                optional.append(var_info)

                        modules[module_name] = {
                            "required": required,
                            "optional": optional
                        }
                    except Exception as e:
                        print(f"Error parsing {variables_file}: {e}")

    print(f"Modules loaded: {modules}")  # Debugging - Print all loaded modules
    return modules


def fuzzy_match_input(user_input, available_resources):
    """
    This function uses fuzzy matching to find the best matching resource
    based on the user input and available resources.
    """
    # Normalize both the input and the available resources
    user_input_normalized = user_input.strip().lower()
    available_resources_normalized = [r.strip().lower() for r in available_resources]

    print(f"User Input (Normalized): {user_input_normalized}")  # Debugging
    print(f"Available Resources (Normalized): {available_resources_normalized}")  # Debugging

    # Direct exact match check
    if user_input_normalized in available_resources_normalized:
        return user_input_normalized

    # If no exact match, use fuzzy matching
    result = process.extractOne(user_input_normalized, available_resources_normalized)
    if result:  # Check if result is not None
        matched_resource, score = result
        print(f"Matching '{user_input_normalized}' to '{matched_resource}' with score {score}")  # Debugging
        if score >= 60:  # Adjust score threshold if needed
            return matched_resource
    return None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form.get('resource_request')
        modules = load_modules()

        # Split the input by commas to handle multiple resources
        resources_selected = [r.strip().lower() for r in user_input.split(',')]
        
        print("User input resources:", resources_selected)  # Debugging
        available_resources = list(modules.keys())
        print("Available resources:", available_resources)  # Debugging

        # First, check for exact matches
        exact_matches = [r for r in resources_selected if r in available_resources]
        if exact_matches:
            valid_resources = exact_matches
        else:
            valid_resources = []

        # Use fuzzy matching for remaining unmatched resources
        for resource in resources_selected:
            if resource not in valid_resources:
                matched_resource = fuzzy_match_input(resource, available_resources)
                if matched_resource:
                    valid_resources.append(matched_resource)

        print("Valid resources after matching:", valid_resources)  # Debugging

        if not valid_resources:
            return render_template('index.html', error="No valid resources found. Please try again.")

        # Dynamically generate the form based on valid resources
        return render_template('form.html', resources=valid_resources, modules=modules)

    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    user_inputs = request.form.to_dict()
    selected_resources = user_inputs.pop('selected_resources').split(',')

    # Strip whitespace and validate the selected resources
    selected_resources = [r.strip() for r in selected_resources if r.strip()]
    modules = load_modules()

    # Check if the selected resources are in the available modules
    selected_resources = [r for r in selected_resources if r in modules]

    if not selected_resources:
        return render_template('result.html', error="No valid resources selected.")

    # Create a new project folder
    project_id = str(uuid.uuid4())
    project_path = os.path.join(GENERATED_DIR, project_id)
    os.makedirs(project_path, exist_ok=True)

    main_tf_content = ""
    variables_tf_content = ""

    # Generate Terraform code for each selected resource
    for resource in selected_resources:
        resource_inputs = {key: user_inputs[key] for key in user_inputs if key.startswith(resource)}

        # Check for 'use_existing' input
        use_existing = user_inputs.get(f'{resource}_use_existing') == 'on'

        if use_existing:
            main_tf_content += generate_module_block(resource, resource_inputs, modules[resource])
            variables_tf_content += generate_variables_block(modules[resource]["required"], modules[resource]["optional"])
        else:
            main_tf_content += generate_resource_block(resource, resource_inputs)
            variables_tf_content += generate_variables_block(modules[resource]["required"], modules[resource]["optional"])

    # Save the generated Terraform files
    main_tf_file = os.path.join(project_path, 'main.tf')
    variables_tf_file = os.path.join(project_path, 'variables.tf')

    with open(main_tf_file, 'w') as f:
        f.write(main_tf_content)

    with open(variables_tf_file, 'w') as f:
        f.write(variables_tf_content)

    # Display the generated code on the result page
    return render_template('result.html', project_id=project_id, terraform_code=main_tf_content)


def generate_module_block(module, inputs, module_info):
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


def generate_variables_block(required, optional):
    block = ''
    for var in required + optional:
        block += f'variable "{var["name"]}" {{\n'
        block += f'  description = "{var["description"]}"\n'
        block += f'  type        = {var["type"]}\n'
        if var in optional:
            block += '  default     = ""\n'
        block += '}\n\n'
    return block


if __name__ == "__main__":
    app.run(debug=True)
