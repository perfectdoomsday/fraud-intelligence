"""Airflow example: offline retraining is evaluated, not auto-promoted."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="fraud_model_retraining",
    description="Generate features, train challengers and emit evaluation artifacts for human review.",
    start_date=datetime(2025, 1, 1),
    schedule="@weekly",
    catchup=False,
    default_args={"owner": "ml-platform", "retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["fraud", "mlops", "governance"],
) as dag:
    validate_input = BashOperator(
        task_id="validate_training_input",
        bash_command="test -f /opt/airflow/data/synthetic_transactions.csv || (echo 'Mount a validated CSV dataset at /opt/airflow/data/synthetic_transactions.csv' && exit 2)",
    )
    train_challenger = BashOperator(
        task_id="train_challenger",
        bash_command="python /opt/airflow/project/ml/training/train.py --input /opt/airflow/data/synthetic_transactions.csv --output /opt/airflow/artifacts/challenger.joblib",
    )
    human_approval = BashOperator(
        task_id="await_external_human_approval",
        bash_command="echo 'Candidate artifacts are ready. Register, compare with champion, and require an authorized approval before promotion.'",
    )
    validate_input >> train_challenger >> human_approval
