import os
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.providers.sftp.operators.sftp import SFTPOperator

dag_folder = os.path.dirname(__file__)

with DAG(
    dag_id="minutely_dag",
    description="Train, register and upload new models",
    doc_md="""
    # Train and push model to Bucket
    """,
    tags=["train", "register", "upload"],
    schedule_interval=None,
    default_args={
        "owner": "mchelali",
        # "start_date": days_ago(0, minute=1),
    },
    catchup=False,
    # render_template_as_native_obj=True,
) as my_dag:
    
    # copy_script = SFTPOperator(
    #     task_id="copy_script",
    #     ssh_conn_id="rd_host",
    #     local_filepath=os.path.join(dag_folder, "run_training.sh"),  
    #     remote_filepath="/r_and_d/run_training.sh",  
    #     operation="put", 
    # )

    command = r"cd /r_and_d/ && poetry run python -m scripts.register_best_model "
    # the command should ends with space (https://stackoverflow.com/questions/58023987/jinja2-exceptions-templatenotfound-error-with-airflow-bash-operator)
    execute_script = SSHOperator(
        ssh_conn_id="rd_host",
        task_id='rd_ssh_operator',
        command=command,
        do_xcom_push=False,)

    # copy_script >> execute_script