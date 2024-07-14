import os

def copy_template(project_name, case_number, year):
    
    # Set the base directory for the documents
    base_dir = '/Users/yugao/UOP/ORS-processing/doc/'

    # Create a specific directory for the project
    project_dir = os.path.join(base_dir, project_name, case_number)
    
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)
    
    # Read the template
    with open(os.path.join(base_dir, 'template.tex'), 'r') as file:
        template = file.read()

    # Replace placeholders in the template
    template = template.replace("{{projectname}}", project_name)
    template = template.replace("{{year}}", year)
    template = template.replace("{{caseNumber}}", case_number)
    # template = template.replace("{{DeploymentSpike}}", deployment_spike)
    # template = template.replace("{{DeploymentRecordedSpike}}", recorded_deployment_spike)
    # template = template.replace("{{RecoverySpike}}", recovery_spike)
    # template = template.replace("{{RecoveryRecordedSpike}}", recorded_recovery_spike)

    # Write the modified template to a new file in the project directory
    with open(os.path.join(project_dir, f'{project_name}{case_number}_data_report_{year}.tex'), 'w') as file:
        file.write(template)

    # Navigate to the project directory and compile the LaTeX file into a PDF
    # os.chdir(project_dir)
    # os.system(f'pdflatex {project_name}_data_report_{year}.tex')


def create_report(project_name, case_number, year, 
                deployment_spike, recorded_deployment_spike, 
                recovery_spike, recorded_recovery_spike):
    
    # Set the base directory for the documents
    base_dir = '/Users/yugao/UOP/ORS-processing/doc/'

    # Create a specific directory for the project
    project_dir = os.path.join(base_dir, project_name, case_number)
    
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)
    
    # Read the template
    with open(os.path.join(base_dir, 'template.tex'), 'r') as file:
        template = file.read()

    # Replace placeholders in the template
    template = template.replace("{{projectname}}", project_name)
    template = template.replace("{{year}}", year)
    template = template.replace("{{caseNumber}}", case_number)
    template = template.replace("{{DeploymentSpike}}", deployment_spike)
    template = template.replace("{{DeploymentRecordedSpike}}", recorded_deployment_spike)
    template = template.replace("{{RecoverySpike}}", recovery_spike)
    template = template.replace("{{RecoveryRecordedSpike}}", recorded_recovery_spike)

    # Write the modified template to a new file in the project directory
    with open(os.path.join(project_dir, f'{project_name}_data_report_{year}.tex'), 'w') as file:
        file.write(template)

    # Navigate to the project directory and compile the LaTeX file into a PDF
    os.chdir(project_dir)
    os.system(f'pdflatex {project_name}{case_number}_data_report_{year}.tex')

# Example of creating a report for Stratus 16 for the year 2017 with specific spike times

# deployment_spike_times_recorded = '5/06/2017 19:05'
# deployment_spike_times_data = '5/06/2017 19:00'
# recovery_spike_times_recorded = '4/12/2018 14:45'
# recovery_spike_times_data = '4/12/2018 15:50'
# project_name = "stratus"
# case_number = '16'
# year = '2017'

# create_report(project_name, "16", "2017", deployment_spike_times_data, deployment_spike_times_recorded,
#             recovery_spike_times_data, recovery_spike_times_recorded)